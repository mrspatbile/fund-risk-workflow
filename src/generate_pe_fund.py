"""
generate_pe_fund.py
===================
Generates synthetic PE fund data for AIFM_PE_Buyout.
Simulates a 10-year EUR 200m buyout fund with 8 portfolio companies
across different sectors and geographies, vintage 2018.

Populates:
    pe_funds
    pe_portfolio_companies
    pe_fund_investments
    pe_cash_flows
    pe_nav_history
    pe_valuation_report
    pe_company_metrics

Usage
-----
    python3 src/generate_pe_fund.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.database import (
    get_engine, PEFund, PEPortfolioCompany, PEFundInvestment,
    PECashFlow, PENavHistory, PEValuationReport, PECompanyMetrics
)

from sqlalchemy.orm import Session

np.random.seed(42)

# ----------------------------------------------------------------
# Fund configuration
# ----------------------------------------------------------------
FUND_ID   = 'AIFM_PE_Buyout'
FUND_NAME = 'AIFM PE Buyout Fund I'
VINTAGE   = 2018
FUND_LIFE = 10
INV_PERIOD_END = '2023-12-31'
TARGET_SIZE    = 200_000_000
COMMITTED      = 180_000_000  # 90% called over investment period

# ----------------------------------------------------------------
# Portfolio companies
# ----------------------------------------------------------------
COMPANIES = [
    dict(company_id='PE_001', company_name='TechCo Solutions',
         sector='Technology', country='DE',
         investment_stage='Buyout', status='Active',
         investment_date='2018-06-15', entry_multiple=11.5,
         cost_basis_eur=28_000_000, ownership_pct=65.0),

    dict(company_id='PE_002', company_name='MedDevice AG',
         sector='Healthcare', country='CH',
         investment_stage='Buyout', status='Active',
         investment_date='2019-03-20', entry_multiple=13.2,
         cost_basis_eur=22_000_000, ownership_pct=55.0),

    dict(company_id='PE_003', company_name='Logistics Plus',
         sector='Industrials', country='NL',
         investment_stage='Buyout', status='Exited',
         investment_date='2018-11-01', entry_multiple=9.8,
         cost_basis_eur=18_000_000, ownership_pct=70.0,
         exit_date='2023-06-30', exit_price_eur=42_000_000,
         exit_multiple=2.33),

    dict(company_id='PE_004', company_name='RetailGroup France',
         sector='Consumer', country='FR',
         investment_stage='Buyout', status='Active',
         investment_date='2019-09-15', entry_multiple=8.5,
         cost_basis_eur=15_000_000, ownership_pct=80.0),

    dict(company_id='PE_005', company_name='EnergyTrans GmbH',
         sector='Energy Transition', country='DE',
         investment_stage='Growth', status='Active',
         investment_date='2020-04-01', entry_multiple=12.0,
         cost_basis_eur=20_000_000, ownership_pct=45.0),

    dict(company_id='PE_006', company_name='FinTech Nordic',
         sector='Financial Services', country='SE',
         investment_stage='Growth', status='Active',
         investment_date='2021-01-15', entry_multiple=15.5,
         cost_basis_eur=25_000_000, ownership_pct=40.0),

    dict(company_id='PE_007', company_name='FoodCo Benelux',
         sector='Consumer', country='BE',
         investment_stage='Buyout', status='Exited',
         investment_date='2019-06-01', entry_multiple=9.2,
         cost_basis_eur=16_000_000, ownership_pct=75.0,
         exit_date='2024-03-31', exit_price_eur=35_000_000,
         exit_multiple=2.19),

    dict(company_id='PE_008', company_name='SoftwareHub UK',
         sector='Technology', country='GB',
         investment_stage='Buyout', status='Active',
         investment_date='2022-03-01', entry_multiple=14.8,
         cost_basis_eur=24_000_000, ownership_pct=60.0),
]

# ----------------------------------------------------------------
# Cash flow generation
# ----------------------------------------------------------------
def generate_cash_flows() -> list:
    """Generate realistic capital calls and distributions."""
    flows = []

    # Capital calls: irregular over investment period 2018-2023
    calls = [
        # (date, company_id, amount, description)
        ('2018-06-15', 'PE_001', -28_000_000, 'Initial investment TechCo'),
        ('2018-11-01', 'PE_003', -18_000_000, 'Initial investment Logistics Plus'),
        ('2018-12-15', None,     -2_000_000,  'Management fee 2018'),
        ('2019-03-20', 'PE_002', -22_000_000, 'Initial investment MedDevice'),
        ('2019-06-01', 'PE_007', -16_000_000, 'Initial investment FoodCo'),
        ('2019-09-15', 'PE_004', -15_000_000, 'Initial investment RetailGroup'),
        ('2019-12-15', None,     -3_600_000,  'Management fee 2019'),
        ('2020-04-01', 'PE_005', -20_000_000, 'Initial investment EnergyTrans'),
        ('2020-12-15', None,     -3_600_000,  'Management fee 2020'),
        ('2021-01-15', 'PE_006', -25_000_000, 'Initial investment FinTech Nordic'),
        ('2021-12-15', None,     -3_600_000,  'Management fee 2021'),
        ('2022-03-01', 'PE_008', -24_000_000, 'Initial investment SoftwareHub'),
        ('2022-12-15', None,     -3_600_000,  'Management fee 2022'),
        ('2023-06-15', 'PE_001',  -3_000_000, 'Follow-on TechCo'),
        ('2023-12-15', None,     -3_600_000,  'Management fee 2023'),
    ]

    # Distributions and exits
    distributions = [
        ('2021-06-30', 'PE_003',  8_000_000, 'Interim distribution Logistics Plus'),
        ('2022-06-30', 'PE_003',  6_000_000, 'Interim distribution Logistics Plus'),
        ('2023-06-30', 'PE_003', 42_000_000, 'Exit proceeds Logistics Plus'),
        ('2023-12-15', 'PE_003',  5_000_000, 'Carried interest distribution'),
        ('2024-03-31', 'PE_007', 35_000_000, 'Exit proceeds FoodCo'),
        ('2024-06-30', 'PE_002',  4_000_000, 'Interim distribution MedDevice'),
        ('2024-12-15', None,      2_000_000,  'Dividend recapitalisation'),
        ('2025-06-30', 'PE_001',  6_000_000, 'Interim distribution TechCo'),
        ('2025-12-15', 'PE_005',  5_000_000, 'Interim distribution EnergyTrans'),
    ]

    for date, company_id, amount, desc in calls:
        flows.append(dict(
            fund_id    = FUND_ID,
            company_id = company_id,
            date       = date,
            flow_type  = 'management_fee' if company_id is None else 'capital_call',
            amount_eur = amount,
            description= desc,
        ))

    for date, company_id, amount, desc in distributions:
        flows.append(dict(
            fund_id    = FUND_ID,
            company_id = company_id,
            date       = date,
            flow_type  = 'exit_proceeds' if 'Exit' in desc else 'distribution',
            amount_eur = amount,
            description= desc,
        ))

    return sorted(flows, key=lambda x: x['date'])


# ----------------------------------------------------------------
# NAV history generation (quarterly)
# ----------------------------------------------------------------
# MOIC (Multiple on Invested Capital) = current NAV / cost basis
# moic_path traces the J-curve: starts below 1.0x in early years
# (management fees, slow value creation) and rises above 2.0x
# as portfolio companies grow and are exited.
# MOIC < 1.0x: investment below cost (typical years 1-2)
# MOIC = 1.0x: at cost (breakeven)
# MOIC > 1.0x: value creation above cost


def generate_nav_history(valuation_reports: list) -> list:
    """
    Derive quarterly NAV history from independent appraisal reports.
    NAV = appraised_nav_eur from pe_valuation_report (source of truth).
    Fund-level NAV = sum of active company NAVs per quarter.
    """
    nav_rows = []

    # company-level: one row per valuation report
    for vr in valuation_reports:
        nav_rows.append(dict(
            fund_id        = vr['fund_id'],
            company_id     = vr['company_id'],
            date           = vr['date'],
            nav_eur        = vr['appraised_nav_eur'],
            gross_multiple = round(vr['appraised_nav_eur'] / 
                            next(c['cost_basis_eur'] for c in COMPANIES 
                                 if c['company_id'] == vr['company_id']), 3),
            unrealised_gain= round(vr['appraised_nav_eur'] - 
                            next(c['cost_basis_eur'] for c in COMPANIES 
                                 if c['company_id'] == vr['company_id']), 2),
            cost_basis_eur = next(c['cost_basis_eur'] for c in COMPANIES 
                                  if c['company_id'] == vr['company_id']),
        ))

    # fund-level: sum of company NAVs per quarter
    df = pd.DataFrame(nav_rows)
    fund_nav = df.groupby('date')['nav_eur'].sum().reset_index()
    for _, row in fund_nav.iterrows():
        nav_rows.append(dict(
            fund_id        = FUND_ID,
            company_id     = None,
            date           = row['date'],
            nav_eur        = round(row['nav_eur'], 2),
            gross_multiple = None,
            unrealised_gain= None,
            cost_basis_eur = None,
        ))

    return nav_rows


# ----------------------------------------------------------------
# Main: populate PE tables
# ----------------------------------------------------------------


# ----------------------------------------------------------------
# Valuation report generation (quarterly independent appraisal)
# ----------------------------------------------------------------
# Data simulates quarterly reports received from independent valuation
# firm (e.g. KPMG, Duff & Phelps). In production this arrives as a
# structured report. The ManCo stores and consumes it, does not compute it.

COMPANY_PROFILES = {
    'PE_001': {
        # TechCo: solid performer, 8% revenue CAGR, slight multiple expansion then compression
        'appraiser': 'KPMG Luxembourg', 'valuation_basis': 'Market approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 6.5, 'coverage_covenant': 2.0,
        'discount_rate': 0.12,
        'revenue_start': 45_000_000, 'revenue_cagr': 0.08,
        'ebitda_margin_start': 0.22, 'ebitda_margin_end': 0.26,
        'net_debt_start': 35_000_000, 'debt_repayment_pa': 3_000_000,
        'interest_rate': 0.055,
        # EV/EBITDA: entry 11.5x, peak 13x in 2021, compressed to 10x by 2023, recovery to 11x
        'ev_multiple_path': {2018: 11.5, 2019: 12.0, 2020: 11.5, 2021: 13.0,
                             2022: 11.5, 2023: 10.0, 2024: 10.5, 2025: 11.0, 2026: 11.0},
        'key_risks': 'Technology disruption, key person dependency, customer concentration',
    },
    'PE_002': {
        # MedDevice: defensive sector, steady growth, resilient multiples
        'appraiser': 'Duff & Phelps', 'valuation_basis': 'Income approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 5.5, 'coverage_covenant': 2.5,
        'discount_rate': 0.11,
        'revenue_start': 38_000_000, 'revenue_cagr': 0.07,
        'ebitda_margin_start': 0.25, 'ebitda_margin_end': 0.28,
        'net_debt_start': 28_000_000, 'debt_repayment_pa': 2_500_000,
        'interest_rate': 0.050,
        'ev_multiple_path': {2019: 13.2, 2020: 13.0, 2021: 14.5,
                             2022: 13.0, 2023: 12.0, 2024: 12.5, 2025: 13.0, 2026: 13.0},
        'key_risks': 'Regulatory approval risk, reimbursement pressure, clinical trial outcomes',
    },
    'PE_003': {
        # Logistics Plus: exited 2023, good performer
        'appraiser': 'Lincoln International', 'valuation_basis': 'Market approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 6.0, 'coverage_covenant': 2.0,
        'discount_rate': 0.13,
        'revenue_start': 55_000_000, 'revenue_cagr': 0.08,
        'ebitda_margin_start': 0.18, 'ebitda_margin_end': 0.21,
        'net_debt_start': 22_000_000, 'debt_repayment_pa': 2_000_000,
        'interest_rate': 0.058,
        'ev_multiple_path': {2018: 9.8, 2019: 10.5, 2020: 9.5, 2021: 12.0,
                             2022: 10.5, 2023: 11.0},
        'key_risks': 'E-commerce disruption, fuel cost exposure, driver shortage',
        'exit_date': '2023-06-30',
    },
    'PE_004': {
        # RetailGroup France: DISTRESSED - structural decline, covenant breach
        'appraiser': 'KPMG Luxembourg', 'valuation_basis': 'Market approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 5.5, 'coverage_covenant': 2.0,
        'discount_rate': 0.14,
        'revenue_start': 42_000_000, 'revenue_cagr': 0.01,
        'ebitda_margin_start': 0.14, 'ebitda_margin_end': -0.04,
        'net_debt_start': 18_000_000, 'debt_repayment_pa': 300_000,
        'interest_rate': 0.068,
        'ev_multiple_path': {2019: 8.5, 2020: 7.0, 2021: 8.0,
                             2022: 6.0, 2023: 4.5, 2024: 3.0, 2025: 2.5, 2026: 2.0},
        'key_risks': 'Structural decline of physical retail, rising vacancy rates, '
                     'e-commerce competition, covenant breach risk from 2024',
    },
    'PE_005': {
        # EnergyTrans: growth story, capex heavy early, improving margins
        'appraiser': 'Duff & Phelps', 'valuation_basis': 'Income approach',
        'covenant_type': 'revenue',
        'leverage_covenant': 7.0, 'coverage_covenant': 1.8,
        'discount_rate': 0.13,
        'revenue_start': 28_000_000, 'revenue_cagr': 0.15,
        'ebitda_margin_start': 0.16, 'ebitda_margin_end': 0.22,
        'net_debt_start': 24_000_000, 'debt_repayment_pa': 1_500_000,
        'interest_rate': 0.060,
        'ev_multiple_path': {2020: 12.0, 2021: 15.0, 2022: 13.0,
                             2023: 11.0, 2024: 12.0, 2025: 12.5, 2026: 13.0},
        'revenue_covenant_eur': 25_000_000,
        'key_risks': 'Energy transition policy risk, technology obsolescence, capex intensity',
    },
    'PE_006': {
        # FinTech Nordic: pre-profit growth, high multiple on revenue, path to profitability
        'appraiser': 'Lincoln International', 'valuation_basis': 'Market approach',
        'covenant_type': 'liquidity',
        'leverage_covenant': None, 'coverage_covenant': None,
        'discount_rate': 0.18,
        'revenue_start': 12_000_000, 'revenue_cagr': 0.30,
        'ebitda_margin_start': -0.20, 'ebitda_margin_end': 0.15,
        'net_debt_start': 8_000_000, 'debt_repayment_pa': 0,
        'interest_rate': 0.075,
        'ev_multiple_path': {2021: 15.5, 2022: 10.0, 2023: 8.0,
                             2024: 9.0, 2025: 10.0, 2026: 11.0},
        'revenue_covenant_eur': 10_000_000,
        'cash_covenant_eur': 3_000_000,
        'key_risks': 'Regulatory fintech risk, customer acquisition cost, '
                     'path to profitability, competition from incumbents',
    },
    'PE_007': {
        # FoodCo Benelux: exited 2024, good performer
        'appraiser': 'KPMG Luxembourg', 'valuation_basis': 'Market approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 5.5, 'coverage_covenant': 2.2,
        'discount_rate': 0.12,
        'revenue_start': 48_000_000, 'revenue_cagr': 0.07,
        'ebitda_margin_start': 0.16, 'ebitda_margin_end': 0.19,
        'net_debt_start': 20_000_000, 'debt_repayment_pa': 2_000_000,
        'interest_rate': 0.055,
        'ev_multiple_path': {2019: 9.2, 2020: 8.5, 2021: 10.5,
                             2022: 9.0, 2023: 8.5, 2024: 9.0},
        'key_risks': 'Consumer spending slowdown, private label competition, raw material costs',
        'exit_date': '2024-03-31',
    },
    'PE_008': {
        # SoftwareHub: recent investment, strong growth trajectory
        'appraiser': 'Duff & Phelps', 'valuation_basis': 'Market approach',
        'covenant_type': 'leverage',
        'leverage_covenant': 6.0, 'coverage_covenant': 2.0,
        'discount_rate': 0.13,
        'revenue_start': 32_000_000, 'revenue_cagr': 0.12,
        'ebitda_margin_start': 0.20, 'ebitda_margin_end': 0.26,
        'net_debt_start': 30_000_000, 'debt_repayment_pa': 2_000_000,
        'interest_rate': 0.062,
        'ev_multiple_path': {2022: 14.8, 2023: 11.0, 2024: 11.5,
                             2025: 12.0, 2026: 12.5},
        'key_risks': 'Talent retention, cyber security, integration risk post-acquisition',
    },
}


def generate_valuation_reports() -> list:
    """Generate quarterly independent appraisal reports for all companies."""
    reports = []

    for company_id, inv in [(c['company_id'], c) for c in COMPANIES]:
        profile      = COMPANY_PROFILES[company_id]
        start_date   = pd.Timestamp(inv['investment_date'])
        exit_date    = pd.Timestamp(profile['exit_date']) if 'exit_date' in profile else None
        cost_basis   = inv['cost_basis_eur']
        nav_data     = {
            n['company_id']: n
            for n in [dict(
                company_id     = nr.company_id,
                date           = nr.date,
                nav_eur        = nr.nav_eur,
                gross_multiple = nr.gross_multiple,
            ) for nr in []]
        }

        # generate quarterly dates from first full quarter after investment
        first_quarter = start_date + pd.offsets.QuarterEnd(1)
        quarters      = pd.date_range(
            start=first_quarter,
            end=pd.Timestamp('2026-03-31'),
            freq='QE'
        )

        n_quarters         = len(quarters)
        revenue_start      = profile['revenue_start']
        revenue_cagr       = profile['revenue_cagr']
        ebitda_margin_start= profile['ebitda_margin_start']
        ebitda_margin_end  = profile['ebitda_margin_end']
        net_debt           = profile['net_debt_start']
        debt_repayment_pa  = profile['debt_repayment_pa']
        interest_rate      = profile['interest_rate']

        for i, quarter in enumerate(quarters):
            if exit_date and quarter > exit_date:
                break

            # interpolate metrics over fund life
            t = i / max(n_quarters - 1, 1)

            revenue_ltm  = revenue_start * (1 + revenue_cagr) ** (i / 4)
            ebitda_margin= ebitda_margin_start + t * (ebitda_margin_end - ebitda_margin_start)
            ebitda_ltm   = revenue_ltm * ebitda_margin
            net_debt_q   = max(0, net_debt - debt_repayment_pa * (i / 4))
            interest_exp = net_debt_q * interest_rate

            # EV and NAV
            if ebitda_ltm > 0:
                # use entry multiple as base, slight compression/expansion
                ev_ebitda = inv['entry_multiple'] * (1 + t * 0.1)
                ev_eur    = ebitda_ltm * ev_ebitda
            else:
                ev_ebitda = None
                ev_eur    = revenue_ltm * 1.5  # revenue multiple for pre-profit

            appraised_nav = max(0, ev_eur - net_debt_q)

            # covenant ratios
            leverage_ratio  = net_debt_q / ebitda_ltm if ebitda_ltm > 0 else None
            coverage_ratio  = ebitda_ltm / interest_exp if interest_exp > 0 else None
            arr_eur         = revenue_ltm * 0.6 if company_id == 'PE_006' else None

            # key risks evolve for distressed company
            key_risks = profile['key_risks']
            if company_id == 'PE_004' and quarter >= pd.Timestamp('2022-01-01'):
                if leverage_ratio and leverage_ratio > profile['leverage_covenant'] * 0.8:
                    key_risks = key_risks + ' — COVENANT HEADROOM < 20%: monitoring intensified'
            if company_id == 'PE_004' and quarter >= pd.Timestamp('2024-01-01'):
                key_risks = key_risks + ' — COVENANT BREACH: waiver requested'

            reports.append(dict(
                fund_id             = FUND_ID,
                company_id          = company_id,
                date                = quarter.strftime('%Y-%m-%d'),
                appraised_nav_eur   = round(appraised_nav, 2),
                ebitda_ltm_eur      = round(ebitda_ltm, 2),
                revenue_ltm_eur     = round(revenue_ltm, 2),
                ebitda_margin       = round(ebitda_margin, 4),
                net_debt_eur        = round(net_debt_q, 2),
                ev_eur              = round(ev_eur, 2),
                ev_ebitda           = round(ev_ebitda, 2) if ev_ebitda else None,
                interest_expense_eur= round(interest_exp, 2),
                discount_rate       = profile['discount_rate'],
                valuation_basis     = profile['valuation_basis'],
                appraiser           = profile['appraiser'],
                key_risks           = key_risks,
                covenant_type       = profile['covenant_type'],
                leverage_covenant   = profile.get('leverage_covenant'),
                leverage_ratio      = round(leverage_ratio, 3) if leverage_ratio else None,
                coverage_covenant   = profile.get('coverage_covenant'),
                coverage_ratio      = round(coverage_ratio, 3) if coverage_ratio else None,
                revenue_covenant_eur= profile.get('revenue_covenant_eur'),
                cash_covenant_eur   = profile.get('cash_covenant_eur'),
                arr_eur             = round(arr_eur, 2) if arr_eur else None,
            ))

    return reports


def generate_pe_fund(engine=None) -> None:
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:

        # clear existing PE data
        session.query(PEValuationReport).filter_by(fund_id=FUND_ID).delete()
        session.query(PENavHistory).filter_by(fund_id=FUND_ID).delete()
        session.query(PECashFlow).filter_by(fund_id=FUND_ID).delete()
        session.query(PEFundInvestment).filter_by(fund_id=FUND_ID).delete()
        session.query(PEFund).filter_by(fund_id=FUND_ID).delete()
        for c in COMPANIES:
            session.query(PEPortfolioCompany).filter_by(
                company_id=c['company_id']).delete()
        session.commit()

        # PE fund metadata
        session.add(PEFund(
            fund_id               = FUND_ID,
            fund_name             = FUND_NAME,
            vintage_year          = VINTAGE,
            target_size_eur       = TARGET_SIZE,
            investment_period_end = INV_PERIOD_END,
            fund_life_years       = FUND_LIFE,
            currency              = 'EUR',
            domicile              = 'Luxembourg',
            strategy              = 'Buyout',
        ))

        # portfolio companies and fund investments
        for c in COMPANIES:
            session.add(PEPortfolioCompany(
                company_id       = c['company_id'],
                company_name     = c['company_name'],
                sector           = c['sector'],
                country          = c['country'],
                investment_stage = c['investment_stage'],
                status           = c['status'],
            ))
            session.add(PEFundInvestment(
                fund_id         = FUND_ID,
                company_id      = c['company_id'],
                investment_date = c['investment_date'],
                entry_multiple  = c['entry_multiple'],
                cost_basis_eur  = c['cost_basis_eur'],
                ownership_pct   = c['ownership_pct'],
                exit_date       = c.get('exit_date'),
                exit_price_eur  = c.get('exit_price_eur'),
                exit_multiple   = c.get('exit_multiple'),
            ))

        # cash flows
        for cf in generate_cash_flows():
            session.add(PECashFlow(**cf))

        # valuation reports first - source of truth for NAV
        val_reports = generate_valuation_reports()
        for vr in val_reports:
            session.add(PEValuationReport(**vr))

        # NAV history derived from appraisal reports
        for nav in generate_nav_history(val_reports):
            session.add(PENavHistory(**nav))

        session.commit()


    val_reports = generate_valuation_reports()
    print(f'PE fund {FUND_ID} generated successfully.')
    print(f'  Companies         : {len(COMPANIES)}')
    print(f'  Cash flows        : {len(generate_cash_flows())}')
    print(f'  Valuation reports : {len(val_reports)}')
    print(f'  NAV quarters      : {len([n for n in generate_nav_history(val_reports) if n["company_id"] is not None])}')


if __name__ == '__main__':
    generate_pe_fund()