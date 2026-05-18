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