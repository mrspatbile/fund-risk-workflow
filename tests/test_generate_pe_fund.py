"""
tests/test_generate_pe_fund.py
==============================
Unit tests for generate_pe_fund.py
Run with: python3 -m pytest tests/test_generate_pe_fund.py -v
"""
import pytest
from src.generate_pe_fund import (
    generate_cash_flows, generate_nav_history,
    generate_valuation_reports, COMPANIES
)


class TestGenerateCashFlows:

    def test_returns_list(self):
        assert isinstance(generate_cash_flows(), list)

    def test_capital_calls_negative(self):
        flows = generate_cash_flows()
        calls = [f for f in flows if f['flow_type'] == 'capital_call']
        assert all(f['amount_eur'] < 0 for f in calls)

    def test_distributions_positive(self):
        flows = generate_cash_flows()
        dists = [f for f in flows if f['flow_type'] in ('distribution', 'exit_proceeds')]
        assert all(f['amount_eur'] > 0 for f in dists)

    def test_all_flows_have_date(self):
        flows = generate_cash_flows()
        assert all('date' in f for f in flows)

    def test_flows_sorted_by_date(self):
        flows = generate_cash_flows()
        dates = [f['date'] for f in flows]
        assert dates == sorted(dates)


class TestGenerateNavHistory:

    def test_returns_list(self):
        val_reports = generate_valuation_reports()
        assert isinstance(generate_nav_history(val_reports), list)

    def test_company_nav_positive(self):
        val_reports = generate_valuation_reports()
        nav = generate_nav_history(val_reports)
        company_nav = [n for n in nav if n['company_id'] is not None]
        assert all(n['nav_eur'] >= 0 for n in company_nav)

    def test_fund_level_nav_present(self):
        val_reports = generate_valuation_reports()
        nav = generate_nav_history(val_reports)
        fund_nav = [n for n in nav if n['company_id'] is None]
        assert len(fund_nav) > 0

    def test_all_companies_have_nav(self):
        val_reports = generate_valuation_reports()
        nav = generate_nav_history(val_reports)
        company_ids = {n['company_id'] for n in nav if n['company_id']}
        expected = {c['company_id'] for c in COMPANIES}
        assert company_ids == expected

    def test_nav_consistent_with_appraisal(self):
        val_reports = generate_valuation_reports()
        nav = generate_nav_history(val_reports)
        nav_map = {(n['company_id'], n['date']): n['nav_eur']
                   for n in nav if n['company_id']}
        for vr in val_reports:
            key = (vr['company_id'], vr['date'])
            assert abs(nav_map[key] - vr['appraised_nav_eur']) < 0.01


class TestGenerateValuationReports:

    def test_returns_list(self):
        assert isinstance(generate_valuation_reports(), list)

    def test_all_companies_have_reports(self):
        reports = generate_valuation_reports()
        company_ids = {r['company_id'] for r in reports}
        expected = {c['company_id'] for c in COMPANIES}
        assert company_ids == expected

    def test_retail_group_distressed(self):
        reports = generate_valuation_reports()
        retail = [r for r in reports
                  if r['company_id'] == 'PE_004'
                  and r['date'] >= '2023-01-01']
        assert any('COVENANT' in r['key_risks'] for r in retail)

    def test_fintech_has_arr(self):
        reports = generate_valuation_reports()
        fintech = [r for r in reports if r['company_id'] == 'PE_006']
        assert all(r['arr_eur'] is not None for r in fintech)

    def test_fintech_has_liquidity_covenant(self):
        reports = generate_valuation_reports()
        fintech = [r for r in reports if r['company_id'] == 'PE_006']
        assert all(r['covenant_type'] == 'liquidity' for r in fintech)

    def test_buyout_has_leverage_covenant(self):
        reports = generate_valuation_reports()
        techco = [r for r in reports if r['company_id'] == 'PE_001']
        assert all(r['covenant_type'] == 'leverage' for r in techco)

    def test_exited_company_stops_at_exit(self):
        reports = generate_valuation_reports()
        logistics = [r for r in reports if r['company_id'] == 'PE_003']
        assert all(r['date'] <= '2023-06-30' for r in logistics)


class TestEvMultiplePath:

    def test_ev_multiple_path_used_not_entry_multiple(self):
        """PE_001 Q4 2021 should reflect path multiple 11.0x, not entry multiple 10.0x."""
        reports = generate_valuation_reports()
        pe001_q4_2021 = [
            r for r in reports
            if r['company_id'] == 'PE_001' and r['date'] == '2021-12-31'
            and r['ebitda_ltm_eur'] > 0
        ]
        assert len(pe001_q4_2021) == 1, "Expected exactly one Q4 2021 row for PE_001"
        implied = pe001_q4_2021[0]['ev_eur'] / pe001_q4_2021[0]['ebitda_ltm_eur']
        assert implied > 10.5, f"Q4 2021 EV/EBITDA {implied:.2f}x below path multiple 11.0x"
        assert implied <= 11.0 + 1e-6, f"Q4 2021 EV/EBITDA {implied:.2f}x above path ceiling 11.0x"

    def test_multiple_compression_pe004(self):
        """RetailGroup should show declining multiples over time per path."""
        reports = generate_valuation_reports()
        pe004 = sorted(
            [r for r in reports if r['company_id'] == 'PE_004' and r['ev_ebitda'] is not None],
            key=lambda x: x['date']
        )
        early = [r['ev_ebitda'] for r in pe004 if r['date'] < '2021-01-01']
        late  = [r['ev_ebitda'] for r in pe004 if r['date'] >= '2023-01-01']
        assert sum(early) / len(early) > sum(late) / len(late), \
            "PE_004 multiples should compress over time"


class TestLiquidationFloor:

    def test_nav_never_below_liquidation_floor(self):
        """No company NAV should ever drop below its liquidation value."""
        from src.generate_pe_fund import LIQUIDATION_VALUE
        reports = generate_valuation_reports()
        for r in reports:
            floor = LIQUIDATION_VALUE[r['company_id']]
            assert r['appraised_nav_eur'] >= floor, (
                f"{r['company_id']} on {r['date']}: NAV {r['appraised_nav_eur']:,.0f} "
                f"below liquidation floor {floor:,.0f}"
            )

    def test_distressed_retail_above_floor(self):
        """PE_004 in late years should sit at or just above liquidation value, not zero."""
        from src.generate_pe_fund import LIQUIDATION_VALUE
        reports = generate_valuation_reports()
        pe004_late = [
            r for r in reports
            if r['company_id'] == 'PE_004' and r['date'] >= '2024-01-01'
        ]
        floor = LIQUIDATION_VALUE['PE_004']
        for r in pe004_late:
            assert r['appraised_nav_eur'] >= floor, \
                f"PE_004 NAV {r['appraised_nav_eur']:,.0f} dropped below floor {floor:,.0f}"

class TestGenerateCashFlowsWaterfall:

    def test_capital_calls_derived_not_hardcoded(self):
        """Capital calls must match compute_entry_equity_check() for each company."""
        from src.generate_pe_fund import compute_entry_equity_check
        flows = generate_cash_flows()
        initial_calls = [
            f for f in flows
            if f['flow_type'] == 'capital_call'
            and 'Initial investment' in f['description']
        ]
        for f in initial_calls:
            expected = compute_entry_equity_check(f['company_id'])
            assert abs(abs(f['amount_eur']) - expected) < 1.0, (
                f"{f['company_id']} capital call {abs(f['amount_eur'])/1e6:.1f}M "
                f"does not match equity check {expected/1e6:.1f}M"
            )

    def test_management_fees_derived_from_committed(self):
        """Management fees must equal 1.75% of committed p.a., semi-annual."""
        from src.generate_pe_fund import COMMITTED, MGMT_FEE_RATE
        flows = generate_cash_flows()
        fees = [f for f in flows if f['flow_type'] == 'management_fee']
        expected_semi = round(COMMITTED * MGMT_FEE_RATE / 2, 0)
        assert len(fees) > 0
        for f in fees:
            assert abs(abs(f['amount_eur']) - expected_semi) < 1.0, (
                f"Management fee {abs(f['amount_eur'])/1e6:.2f}M "
                f"does not match expected {expected_semi/1e6:.2f}M"
            )

    def test_exit_proceeds_lp_share_below_gross(self):
        """LP distribution must be less than gross exit proceeds after carry."""
        flows = generate_cash_flows()
        exits = [f for f in flows if f['flow_type'] == 'exit_proceeds']
        companies_with_exits = [c for c in COMPANIES if c.get('exit_price_eur')]
        for ex in companies_with_exits:
            lp_flow = next(
                (f for f in exits if f['company_id'] == ex['company_id']), None
            )
            assert lp_flow is not None, f"No LP distribution for {ex['company_id']}"
            assert lp_flow['amount_eur'] <= ex['exit_price_eur'], (
                f"{ex['company_id']} LP share {lp_flow['amount_eur']/1e6:.1f}M "
                f"exceeds gross exit {ex['exit_price_eur']/1e6:.1f}M"
            )

    def test_carried_interest_is_twenty_percent_of_profits(self):
        """GP carry must be approximately 20% of profits above hurdle."""
        from src.generate_pe_fund import CARRY_RATE
        flows = generate_cash_flows()
        carry_flows = [f for f in flows if f['flow_type'] == 'carried_interest']
        exit_flows  = [f for f in flows if f['flow_type'] == 'exit_proceeds']
        call_flows  = [f for f in flows if f['flow_type'] == 'capital_call']

        for ex in COMPANIES:
            if not ex.get('exit_price_eur'):
                continue
            carry = next((f for f in carry_flows if f['company_id'] == ex['company_id']), None)
            lp    = next((f for f in exit_flows  if f['company_id'] == ex['company_id']), None)
            if carry is None:
                continue  # no carry if exit below hurdle
            gross       = ex['exit_price_eur']
            total_out   = carry['amount_eur'] + lp['amount_eur']
            assert abs(total_out - gross) < 1.0, (
                f"{ex['company_id']} LP + GP {total_out/1e6:.1f}M != gross {gross/1e6:.1f}M"
            )
            assert carry['amount_eur'] / gross <= CARRY_RATE + 0.01, (
                f"{ex['company_id']} carry {carry['amount_eur']/1e6:.1f}M "
                f"exceeds {CARRY_RATE*100:.0f}% of gross"
            )

    def test_total_committed_covers_deployment(self):
        """Total capital calls must not exceed committed capital."""
        from src.generate_pe_fund import COMMITTED
        flows = generate_cash_flows()
        total_called = sum(
            abs(f['amount_eur']) for f in flows
            if f['flow_type'] == 'capital_call'
        )
        assert total_called <= COMMITTED, (
            f"Total calls {total_called/1e6:.1f}M exceed committed {COMMITTED/1e6:.1f}M"
        )

    def test_distributions_positive(self):
        """All distribution and exit flow amounts must be positive."""
        flows = generate_cash_flows()
        dist_types = ['distribution', 'exit_proceeds', 'carried_interest']
        for f in flows:
            if f['flow_type'] in dist_types:
                assert f['amount_eur'] > 0, (
                    f"{f['flow_type']} on {f['date']} has non-positive amount {f['amount_eur']}"
                )