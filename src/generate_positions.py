"""
generate_positions.py
=====================
Generates realistic fund position Excel files for all four funds,
mimicking the daily export format of a fund administrator system
(SimCorp, Geneva, Advent).

Each file contains 250 trading days of daily position snapshots.
Filtering to a single date reproduces the daily fund admin export.

Usage
-----
    python3 generate_positions.py

Output
------
    data/fund_positions_AIFM_HedgeFund.xlsx
    data/fund_positions_AIFM_PrivateDebt.xlsx
    data/fund_positions_AIFM_RealEstate.xlsx
    data/fund_positions_UCITS_Balanced.xlsx
"""

import json
import numpy as np
import pandas as pd
from datetime import date
import os
from pathlib import Path

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

ROOT_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = str(ROOT_DIR / 'data')
_REF_DIR   = ROOT_DIR / 'reference_data'

TRADING_DAYS  = 2000
END_DATE      = pd.Timestamp('2026-05-13')
DATES         = pd.bdate_range(end=END_DATE, periods=TRADING_DAYS)
np.random.seed(42)

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(_REF_DIR / 'esg_scores.json') as _f:
    _ESG = json.load(_f)


# ----------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------

def simulate_prices(
    start_price: float,
    n: int,
    vol: float = 0.01,
    seed: int = 0
) -> np.ndarray:
    """Simulate price path ending at start_price."""
    np.random.seed(seed)
    log_returns = np.random.normal(-vol**2 / 2, vol, n)
    log_prices  = np.log(start_price) - np.cumsum(log_returns[::-1])
    prices      = np.exp(log_prices)[::-1]
    prices      = prices * start_price / prices[-1]
    return prices


def _get_base_price(bloomberg_ticker: str, fallback: float) -> float:
    """
    For instruments in MockBloomberg.YF_MAP return the last real
    closing price from yfinance cache. Falls back to hardcoded price
    if not mapped or cache unavailable.
    """
    from src.mock_bloomberg import MockBloomberg
    yf_ticker = MockBloomberg.YF_MAP.get(bloomberg_ticker)
    if not yf_ticker:
        return fallback
    cache_dir  = MockBloomberg.YF_CACHE_DIR
    safe_name  = yf_ticker.replace('^', '').replace('=', '_')
    cache_path = cache_dir / f'{safe_name}.csv'
    if not cache_path.exists():
        return fallback
    try:
        raw = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        raw.index = pd.to_datetime(raw.index).tz_localize(None)
        raw = raw[raw.index <= pd.Timestamp('2026-05-13')]
        return float(raw['Close'].dropna().iloc[-1])
    except Exception:
        return fallback


def make_positions_df(rows: list, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Expand a list of position definitions across all dates.
    Each row is a dict defining a single position (instrument).
    For instruments in YF_MAP, real price history is used.
    All other instruments use simulated random walk prices.
    """
    all_rows = []

    for i, row in enumerate(rows):
        bbg_ticker = row.get('bloomberg_ticker')
        base_price = (
            _get_base_price(bbg_ticker, row['price'] or 100.0)
            if bbg_ticker else (row['price'] or 100.0)
        )

        # MRS-47: use real price history for YF_MAP instruments
        if bbg_ticker:
            from src.mock_bloomberg import MockBloomberg
            yf_ticker = MockBloomberg.YF_MAP.get(bbg_ticker)
        else:
            yf_ticker = None

        if yf_ticker:
            from src.mock_bloomberg import MockBloomberg
            prices = MockBloomberg()._fetch_yf_prices(yf_ticker, dates, base_price)
        else:
            vol    = row.get('price_vol', 0.01)
            prices = simulate_prices(base_price, len(dates), vol=vol, seed=i)

        quantities  = row['quantity']
        asset_class = row.get('asset_class', 'Equity')

        for j, dt in enumerate(dates):
            price = prices[j]

            # bonds, loans, CLOs: price is per 100 face value
            if asset_class in ('Bond', 'Loan', 'CLO'):
                mv_local = quantities * price / 100
            # options: price is per share, contract size = 100
            elif asset_class == 'Derivative':
                mv_local = quantities * price * 100
            else:
                mv_local = price * quantities

            mv_eur = mv_local * row.get('fx_rate', 1.0)

            position = {
                'fund_id'           : row['fund_id'],
                'fund_name'         : row['fund_name'],
                'date'              : dt.date(),
                'isin'              : row['isin'],
                'bloomberg_ticker'  : row.get('bloomberg_ticker'),
                'instrument_name'   : row['instrument_name'],
                'asset_class'       : row['asset_class'],
                'sub_asset_class'   : row.get('sub_asset_class', ''),
                'currency'          : row['currency'],
                'quantity'          : quantities,
                'price'             : round(price, 4),
                'market_value_local': round(mv_local, 2),
                'market_value_eur'  : round(mv_eur, 2),
                'weight_pct'        : 0.0,
                'country'           : row.get('country', ''),
                'rating'            : row.get('rating', ''),
                'maturity'          : row.get('maturity', ''),
                'sector'            : row.get('sector', ''),
                'adv_eur'           : row.get('adv_eur', 0),
                'esg_score'         : row.get('esg_score'),
                'env_score'         : row.get('env_score'),
                'soc_score'         : row.get('soc_score'),
                'gov_score'         : row.get('gov_score'),
                'controversy_flag'  : row.get('controversy_flag'),
                'carbon_intensity'  : row.get('carbon_intensity'),
                'is_hedge'          : row.get('is_hedge', False),
            }

            # real estate extra columns
            for col in ['ltv_pct', 'rental_yield_pct',
                        'vacancy_rate_pct', 'property_type',
                        'valuation_date', 'is_direct_property']:
                if col in row:
                    position[col] = row[col]

            all_rows.append(position)

    df = pd.DataFrame(all_rows)

    # compute weight_pct per fund per date
    nav_by_date = (
        df.groupby(['fund_id', 'date'])['market_value_eur']
        .sum()
        .abs()
        .reset_index()
        .rename(columns={'market_value_eur': 'nav'})
    )

    df = df.merge(nav_by_date, on=['fund_id', 'date'], how='left')
    df['weight_pct'] = (df['market_value_eur'] / df['nav'] * 100).round(4)
    df = df.drop(columns=['nav'])

    return df


def _load_specs(fund_id: str) -> list:
    """Load position specs from reference_data and inject ESG fields."""
    path  = _REF_DIR / 'position_specs' / f'{fund_id}.json'
    specs = json.loads(path.read_text())
    for pos in specs:
        esg = _ESG.get(pos['isin'], {})
        for field in ('esg_score', 'env_score', 'soc_score', 'gov_score',
                      'controversy_flag', 'carbon_intensity'):
            if field not in pos:
                pos[field] = esg.get(field)
    return specs


# ----------------------------------------------------------------
# Fund generators
# ----------------------------------------------------------------

def generate_hedge_fund() -> pd.DataFrame:
    return make_positions_df(_load_specs('AIFM_HedgeFund'), DATES)


def generate_private_debt() -> pd.DataFrame:
    return make_positions_df(_load_specs('AIFM_PrivateDebt'), DATES)


def generate_real_estate() -> pd.DataFrame:
    return make_positions_df(_load_specs('AIFM_RealEstate'), DATES)


def generate_ucits_balanced() -> pd.DataFrame:
    return make_positions_df(_load_specs('UCITS_Balanced'), DATES)


# ----------------------------------------------------------------
# Main: generate all four files
# ----------------------------------------------------------------

if __name__ == '__main__':

    funds = {
        'AIFM_HedgeFund'  : generate_hedge_fund,
        'AIFM_PrivateDebt': generate_private_debt,
        'AIFM_RealEstate' : generate_real_estate,
        'UCITS_Balanced'  : generate_ucits_balanced,
    }

    for fund_name, generator in funds.items():
        print(f'Generating {fund_name}...')
        df       = generator()
        filename = f'{OUTPUT_DIR}/fund_positions_{fund_name}.xlsx'
        df.to_excel(filename, index=False)

        latest = df[df['date'] == df['date'].max()]
        nav    = latest['market_value_eur'].sum()
        print(f'  positions : {len(latest)}')
        print(f'  NAV (EUR) : {nav:,.0f}')
        print(f'  date range: {df["date"].min()} to {df["date"].max()}')
        print(f'  saved to  : {filename}')
        print()

    print('All four fund position files generated successfully.')
