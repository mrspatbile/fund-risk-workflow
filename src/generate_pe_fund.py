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

from src.database import get_engine, PEFund, PEPortfolioCompany, PEFundInvestment, PECashFlow, PENavHistory
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


def generate_nav_history() -> list:
    """Generate quarterly NAV history showing J-curve pattern."""
    nav_rows = []

    # company-level NAV evolution
    company_nav = {
        'PE_001': {'start': '2018-06-30', 'cost': 28_000_000,
                   'moic_path': [0.85, 0.90, 0.95, 1.05, 1.15, 1.30,
                                 1.50, 1.70, 1.90, 2.10, 2.30, 2.50]},
        'PE_002': {'start': '2019-03-31', 'cost': 22_000_000,
                   'moic_path': [0.88, 0.92, 0.98, 1.08, 1.20, 1.35,
                                 1.55, 1.75, 1.95, 2.15]},
        'PE_003': {'start': '2018-12-31', 'cost': 18_000_000,
                   'moic_path': [0.90, 0.95, 1.05, 1.20, 1.45, 1.80,
                                 2.10, 2.33],
                   'exit': '2023-06-30'},
        'PE_004': {'start': '2019-09-30', 'cost': 15_000_000,
                   'moic_path': [0.82, 0.85, 0.88, 0.92, 0.98, 1.05,
                                 1.12, 1.20, 1.30]},
        'PE_005': {'start': '2020-06-30', 'cost': 20_000_000,
                   'moic_path': [0.90, 0.95, 1.05, 1.20, 1.40, 1.65,
                                 1.85, 2.05]},
        'PE_006': {'start': '2021-03-31', 'cost': 25_000_000,
                   'moic_path': [0.85, 0.88, 0.92, 0.98, 1.08, 1.20,
                                 1.35]},
        'PE_007': {'start': '2019-06-30', 'cost': 16_000_000,
                   'moic_path': [0.88, 0.92, 1.00, 1.15, 1.35, 1.60,
                                 1.85, 2.10, 2.19],
                   'exit': '2024-03-31'},
        'PE_008': {'start': '2022-06-30', 'cost': 24_000_000,
                   'moic_path': [0.88, 0.92, 0.96, 1.02, 1.10, 1.20]},
    }

    for company_id, data in company_nav.items():
        start = pd.Timestamp(data['start'])
        cost  = data['cost']
        moic_path = data['moic_path']
        exit_date = pd.Timestamp(data['exit']) if 'exit' in data else None

        quarters = pd.date_range(start=start, periods=len(moic_path), freq='QE')

        for i, (quarter, moic) in enumerate(zip(quarters, moic_path)):
            if exit_date and quarter > exit_date:
                break
            nav = cost * moic
            nav_rows.append(dict(
                fund_id        = FUND_ID,
                company_id     = company_id,
                date           = quarter.strftime('%Y-%m-%d'),
                nav_eur        = round(nav, 2),
                gross_multiple = round(moic, 3),
                unrealised_gain= round(nav - cost, 2),
                cost_basis_eur = cost,
            ))

    # fund-level quarterly NAV (sum of companies)
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
def generate_pe_fund(engine=None) -> None:
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:

        # clear existing PE data
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

        # NAV history
        for nav in generate_nav_history():
            session.add(PENavHistory(**nav))

        session.commit()

    print(f'PE fund {FUND_ID} generated successfully.')
    print(f'  Companies     : {len(COMPANIES)}')
    print(f'  Cash flows    : {len(generate_cash_flows())}')
    print(f'  NAV quarters  : {len([n for n in generate_nav_history() if n["company_id"] is not None])}')


if __name__ == '__main__':
    generate_pe_fund()