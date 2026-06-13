"""
setup_db.py
===========
Idempotent database setup script. Safe to run at any time.

Logic
-----
1. db does not exist          → create schema, load positions, enrich
2. positions empty            → load positions, enrich
3. positions_enriched missing → enrich only
4. everything exists          → print status, exit

Usage
-----
    python3 src/setup_db.py           # idempotent
    python3 src/setup_db.py --force   # full rebuild from scratch
"""

import sys
import os
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import sqlalchemy as sa
from src.data.database import create_db, load_fund_metadata, load_positions, get_engine
from src.data.enrichment import enrich_positions
from src.data.mock_bloomberg import MockBloomberg as Bloomberg
from sqlalchemy import text

FUNDS    = ['AIFM_HedgeFund', 'AIFM_PrivateDebt',
            'AIFM_RealEstate', 'UCITS_Balanced']
DATE     = '2026-05-13'
DATA_DIR = str(ROOT_DIR / 'data')
DB_PATH  = str(ROOT_DIR / 'data' / 'risk_management.db')


def table_exists(engine: sa.Engine, table: str) -> bool:
    return sa.inspect(engine).has_table(table)


def positions_loaded(engine: sa.Engine) -> bool:
    if not table_exists(engine, 'positions'):
        return False
    with engine.connect() as conn:
        n = conn.execute(sa.text('SELECT COUNT(*) FROM positions')).scalar()
    return n > 0


def enriched_exists(engine: sa.Engine) -> bool:
    return table_exists(engine, 'positions_enriched')


def run(force: bool = False) -> None:

    if force and os.path.exists(DB_PATH):
        print('--force: removing existing database...')
        os.remove(DB_PATH)

    # step 0: regenerate position Excel files with real prices
    if force:
        print('Regenerating position Excel files with real prices...')
        from src.data.generate_positions import (
            generate_hedge_fund, generate_private_debt,
            generate_real_estate, generate_ucits_balanced,
        )
        import pandas as pd
        fund_generators = {
            'AIFM_HedgeFund'  : generate_hedge_fund,
            'AIFM_PrivateDebt': generate_private_debt,
            'AIFM_RealEstate' : generate_real_estate,
            'UCITS_Balanced'  : generate_ucits_balanced,
        }
        for fund_name, generator in fund_generators.items():
            print(f'  {fund_name}...')
            df = generator()
            path = str(ROOT_DIR / 'data' / f'fund_positions_{fund_name}.xlsx')
            df.to_excel(path, index=False)
        print('Excel files regenerated.')

    # step 1: create schema if db missing
    if not os.path.exists(DB_PATH):
        print('Creating database schema...')
        create_db()
    else:
        print('Database exists.')

    engine = get_engine()

    # step 1b: load fund metadata (idempotent)
    load_fund_metadata(engine)

    # step 2: load positions if empty
    if not positions_loaded(engine):
        print('Loading positions from Excel files...')
        load_positions(engine, DATA_DIR)
    else:
        with engine.connect() as conn:
            n = conn.execute(
                sa.text('SELECT COUNT(*) FROM positions')).scalar()
        print(f'Positions already loaded ({n:,} rows). Skipping.')

    # step 3: enrich if positions_enriched missing
    if not enriched_exists(engine):
        print('Enriching positions...')
        bbg = Bloomberg()
        for fund_id in FUNDS:
            print(f'  {fund_id}...')
            enrich_positions(engine, fund_id, DATE, bbg)
        print('Enrichment complete.')
    else:
        print('positions_enriched exists. Skipping enrichment.')


    # step 4: conditionally generate PE fund if present in funds table
    with engine.connect() as conn:
        pe_fund_exists = conn.execute(
            text('SELECT COUNT(*) FROM funds WHERE fund_id = :fid'),
            {'fid': 'AIFM_PE_Buyout'}
        ).scalar()

    if pe_fund_exists > 0:
        with engine.connect() as conn:
            n_pe = conn.execute(text('SELECT COUNT(*) FROM pe_funds')).scalar()
        if n_pe == 0:
            print('Generating PE fund data...')
            from src.data.generate_pe_fund import generate_pe_fund
            generate_pe_fund(engine)
        else:
            print('PE fund data exists. Skipping.')
    else:
        print('AIFM_PE_Buyout not found in funds table. Skipping PE generation.')

    # step 5: conditionally generate infrastructure fund if present in funds table
    with engine.connect() as conn:
        infra_fund_exists = conn.execute(
            text('SELECT COUNT(*) FROM funds WHERE fund_id = :fid'),
            {'fid': 'AIFM_Infra_Core'}
        ).scalar()

    if infra_fund_exists > 0:
        with engine.connect() as conn:
            n_infra = conn.execute(text('SELECT COUNT(*) FROM infra_funds')).scalar()
        if n_infra == 0:
            print('Generating infrastructure fund data...')
            from src.data.generate_infra_fund import generate_infra_fund
            generate_infra_fund(engine)
        else:
            print('Infrastructure fund data exists. Skipping.')
    else:
        print('AIFM_Infra_Core not found in funds table. Skipping Infra generation.')

    print('\nDatabase ready.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Setup risk database.')
    parser.add_argument('--force', action='store_true',
                        help='Rebuild database from scratch.')
    args = parser.parse_args()
    run(force=args.force)