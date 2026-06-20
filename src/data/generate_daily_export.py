"""
generate_daily_export.py
========================
Generates single-day position Excel files mimicking the daily
export sent by the fund administrator. Extracts a specific date
from the full position history and saves as a standalone file.

Usage
-----
    python3 src/generate_daily_export.py
"""

import pandas as pd
from pathlib import Path

ROOT_DIR   = Path(__file__).parent.parent.parent  # src/data/ -> project root
DATA_DIR   = ROOT_DIR / 'data'
EXPORT_DIR = ROOT_DIR / 'data' / 'daily_exports'
EXPORT_DIR.mkdir(exist_ok=True)

FUNDS = {
    'AIFM_HedgeFund'  : 'fund_positions_AIFM_HedgeFund.xlsx',
    'AIFM_PrivateDebt': 'fund_positions_AIFM_PrivateDebt.xlsx',
    'AIFM_RealEstate' : 'fund_positions_AIFM_RealEstate.xlsx',
    'UCITS_Balanced'  : 'fund_positions_UCITS_Balanced.xlsx',
}

DATES = ['2026-03-30', '2026-03-31']  # Last two business days of available data


if __name__ == '__main__':
    for fund_id, filename in FUNDS.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f'Warning: {filepath} not found, skipping.')
            continue

        df = pd.read_excel(filepath)
        df['position_date'] = df['position_date'].astype(str)

        for date in DATES:
            daily = df[df['position_date'] == date].copy()
            if daily.empty:
                print(f'Warning: no data for {fund_id} on {date}')
                continue

            # Export boundary: rename position_date to generic 'date' for external format
            # (mimics fund administrator daily export files)
            daily = daily.rename(columns={'position_date': 'date'})

            out_file = EXPORT_DIR / f'{fund_id}_{date}.xlsx'
            daily.to_excel(out_file, index=False)
            print(f'Exported: {out_file.name} '
                  f'({len(daily)} positions)')