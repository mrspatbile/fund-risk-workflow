"""
tests/test_setup_db.py
======================
Unit tests for setup_db.py
Run with: python3 -m pytest tests/test_setup_db.py -v
"""
import os
import pytest
import sqlalchemy as sa
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

import sys
sys.path.insert(0, str(ROOT_DIR))

from src.setup_db import run, table_exists, positions_loaded, enriched_exists
from src.database import get_engine


@pytest.mark.skip(reason="integration test - run manually with: pytest tests/test_setup_db.py -v")
class TestSetupDb:

    def test_tables_created(self):
        run(force=True)
        engine = get_engine()
        assert table_exists(engine, 'positions')
        assert table_exists(engine, 'positions_enriched')
        assert table_exists(engine, 'funds')

    def test_positions_loaded(self):
        run(force=True)
        engine = get_engine()
        assert positions_loaded(engine)

    def test_enriched_exists(self):
        run(force=True)
        engine = get_engine()
        assert enriched_exists(engine)

    def test_idempotent(self):
        run(force=True)
        engine = get_engine()
        with engine.connect() as conn:
            n1 = conn.execute(
                sa.text('SELECT COUNT(*) FROM positions')).scalar()
        run()
        with engine.connect() as conn:
            n2 = conn.execute(
                sa.text('SELECT COUNT(*) FROM positions')).scalar()
        assert n1 == n2

    def test_row_count(self):
        run(force=True)
        engine = get_engine()
        with engine.connect() as conn:
            n = conn.execute(
                sa.text('SELECT COUNT(*) FROM positions')).scalar()
        assert n == 88000

    def test_four_funds_present(self):
        run(force=True)
        engine = get_engine()
        with engine.connect() as conn:
            funds = conn.execute(
                sa.text('SELECT DISTINCT fund_id FROM positions')
            ).fetchall()
        fund_ids = [f[0] for f in funds]
        for fund in ['AIFM_HedgeFund', 'AIFM_PrivateDebt',
                     'AIFM_RealEstate', 'UCITS_Balanced']:
            assert fund in fund_ids