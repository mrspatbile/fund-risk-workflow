"""
tests/test_generate_daily_export.py
====================================
Unit tests for generate_daily_export.py
Run with: python3 -m pytest tests/test_generate_daily_export.py -v
"""

import pytest
import pandas as pd
from pathlib import Path

ROOT_DIR   = Path(__file__).parent.parent
EXPORT_DIR = ROOT_DIR / 'data' / 'daily_exports'
DATA_DIR   = ROOT_DIR / 'data'

FUNDS = [
    'AIFM_HedgeFund',
    'AIFM_PrivateDebt',
    'AIFM_RealEstate',
    'UCITS_Balanced',
]
DATES = ['2026-05-13', '2026-05-12']

STANDARD_COLS = [
    'fund_id', 'fund_name', 'date', 'isin', 'bloomberg_ticker',
    'instrument_name', 'asset_class', 'sub_asset_class',
    'currency', 'quantity', 'price', 'market_value_local',
    'market_value_eur', 'weight_pct', 'country', 'rating',
    'maturity', 'sector', 'adv_eur'
]


class TestDailyExportFiles:

    def test_export_directory_exists(self):
        assert EXPORT_DIR.exists()

    def test_all_files_created(self):
        for fund in FUNDS:
            for date in DATES:
                path = EXPORT_DIR / f'{fund}_{date}.xlsx'
                assert path.exists(), f'missing: {path.name}'

    def test_files_readable_with_pandas(self):
        for fund in FUNDS:
            for date in DATES:
                path = EXPORT_DIR / f'{fund}_{date}.xlsx'
                if path.exists():
                    df = pd.read_excel(path)
                    assert len(df) > 0

    def test_all_standard_columns_present(self):
        for fund in FUNDS:
            path = EXPORT_DIR / f'{fund}_2026-05-13.xlsx'
            if path.exists():
                df = pd.read_excel(path)
                for col in STANDARD_COLS:
                    assert col in df.columns, \
                        f'{fund}: missing column {col}'

    def test_single_date_per_file(self):
        for fund in FUNDS:
            for date in DATES:
                path = EXPORT_DIR / f'{fund}_{date}.xlsx'
                if path.exists():
                    df = pd.read_excel(path)
                    assert df['date'].astype(str).nunique() == 1
                    assert df['date'].astype(str).iloc[0] == date

    def test_single_fund_per_file(self):
        for fund in FUNDS:
            path = EXPORT_DIR / f'{fund}_2026-05-13.xlsx'
            if path.exists():
                df = pd.read_excel(path)
                assert df['fund_id'].nunique() == 1
                assert df['fund_id'].iloc[0] == fund

    def test_weights_sum_to_100(self):
        for fund in FUNDS:
            path = EXPORT_DIR / f'{fund}_2026-05-13.xlsx'
            if path.exists():
                df    = pd.read_excel(path)
                total = df['weight_pct'].sum()
                assert abs(total - 100.0) < 1.0, \
                    f'{fund}: weights sum to {total:.2f}'

    def test_real_estate_has_extra_columns(self):
        path = EXPORT_DIR / 'AIFM_RealEstate_2026-05-13.xlsx'
        if path.exists():
            df = pd.read_excel(path)
            for col in ['ltv_pct', 'rental_yield_pct',
                        'vacancy_rate_pct', 'is_direct_property']:
                assert col in df.columns

    def test_hedge_fund_has_short_positions(self):
        path = EXPORT_DIR / 'AIFM_HedgeFund_2026-05-13.xlsx'
        if path.exists():
            df = pd.read_excel(path)
            assert (df['market_value_eur'] < 0).any()

    def test_ucits_all_long_only(self):
        path = EXPORT_DIR / 'UCITS_Balanced_2026-05-13.xlsx'
        if path.exists():
            df = pd.read_excel(path)
            assert (df['market_value_eur'] >= 0).all()

    def test_daily_export_matches_full_history(self):
        """Filtering full history to single date = daily export."""
        for fund in FUNDS:
            full_path   = DATA_DIR / f'fund_positions_{fund}.xlsx'
            export_path = EXPORT_DIR / f'{fund}_2026-05-13.xlsx'
            if full_path.exists() and export_path.exists():
                full   = pd.read_excel(full_path)
                full   = full[
                    full['position_date'].astype(str) == '2026-05-13'
                ].reset_index(drop=True)
                # Drop position_date and rename to match export format
                full = full.drop(columns=['position_date'])
                export = pd.read_excel(
                    export_path).reset_index(drop=True)
                assert len(full) == len(export), \
                    f'{fund}: row count mismatch'