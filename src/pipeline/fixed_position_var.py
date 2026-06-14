"""
fixed_position_var.py
=====================
Fixed-position VaR: separated into P&L computation (step 1) and VaR calculation (step 2).

Step 1: compute_fixed_position_pnl_series() — reconstruct 250 days of P&L
Step 2: compute_var_from_pnl() — extract VaR at any confidence level or horizon
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.computation.var import var_historical, var_scale, es_historical, es_scale


def compute_fixed_position_pnl_series(
    engine: Engine,
    fund_id: str,
    valuation_date: str,
    lookback: int = 250,
) -> tuple[np.ndarray, float]:
    """
    Step 1: Compute 250-day P&L series for fixed current portfolio.

    Takes TODAY's positions and reconstructs historical P&L
    assuming that exact portfolio existed for the last 250 trading days.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    fund_id : str
    valuation_date : str
        YYYY-MM-DD (today's date)
    lookback : int, default 250
        Number of business days for P&L reconstruction

    Returns
    -------
    tuple
        (pnl_returns: np.ndarray of 250 daily returns (decimal),
         nav_eur: float, current NAV in EUR)
    """

    # Load today's positions
    with engine.connect() as conn:
        positions_sql = text("""
            SELECT fund_id, position_date, isin, bloomberg_ticker,
                   quantity, price, market_value_eur, asset_class
            FROM positions
            WHERE fund_id = :fund_id AND position_date = :date
        """)
        positions = pd.read_sql(
            positions_sql,
            conn,
            params={'fund_id': fund_id, 'date': valuation_date}
        )

    if positions.empty:
        raise ValueError(f"No positions found for {fund_id} on {valuation_date}")

    nav_today = positions['market_value_eur'].sum()

    # Group by ticker and store asset class for bond scaling
    qty_by_ticker = {}
    asset_class_by_ticker = {}
    for _, row in positions.iterrows():
        ticker_key = row['bloomberg_ticker'] if pd.notna(row['bloomberg_ticker']) else f"ISIN:{row['isin']}"
        qty_by_ticker[ticker_key] = row['quantity']
        asset_class_by_ticker[ticker_key] = row['asset_class']

    # Reconstruct 250-day P&L series
    pnl_returns = []
    lookback_range = pd.date_range(end=valuation_date, periods=lookback + 1, freq='B')
    lookback_dates = sorted([dt.strftime('%Y-%m-%d') for dt in lookback_range])

    for i in range(len(lookback_dates) - 1):
        prev_date = lookback_dates[i]
        curr_date = lookback_dates[i + 1]

        try:
            with engine.connect() as conn:
                prices_sql = text("""
                    SELECT bloomberg_ticker, isin, price
                    FROM positions
                    WHERE fund_id = :fund_id AND position_date = :date
                """)
                prev_pos = pd.read_sql(prices_sql, conn,
                                      params={'fund_id': fund_id, 'date': prev_date})
                curr_pos = pd.read_sql(prices_sql, conn,
                                      params={'fund_id': fund_id, 'date': curr_date})

            daily_pnl = 0.0
            for ticker_key, qty in qty_by_ticker.items():
                if pd.isna(qty) or qty == 0:
                    continue

                if ticker_key.startswith('ISIN:'):
                    isin = ticker_key.split(':')[1]
                    prev_row = prev_pos[prev_pos['isin'] == isin]
                    curr_row = curr_pos[curr_pos['isin'] == isin]
                else:
                    prev_row = prev_pos[prev_pos['bloomberg_ticker'] == ticker_key]
                    curr_row = curr_pos[curr_pos['bloomberg_ticker'] == ticker_key]

                if prev_row.empty or curr_row.empty:
                    continue

                prev_price = float(prev_row.iloc[0]['price'])
                curr_price = float(curr_row.iloc[0]['price'])

                if pd.isna(prev_price) or pd.isna(curr_price):
                    continue

                price_change = curr_price - prev_price

                # Bond prices are quoted per 100 of par (e.g., 98.5 means 98.5% of par)
                # Divide price_change by 100 to get correct P&L for bonds
                asset_class = asset_class_by_ticker.get(ticker_key, '')
                if asset_class == 'Bond':
                    price_change = price_change / 100

                daily_pnl += qty * price_change

            daily_return = daily_pnl / nav_today if nav_today > 0 else 0
            pnl_returns.append(daily_return)

        except Exception:
            continue

    if len(pnl_returns) < 10:
        raise ValueError(f"Insufficient P&L observations ({len(pnl_returns)})")

    return np.array(pnl_returns), nav_today


def compute_var_from_pnl(
    pnl_returns: np.ndarray,
    nav_eur: float,
    confidence: float = 0.99,
    horizon: int = 1,
) -> dict:
    """
    Step 2: Compute VaR and ES from P&L series at any confidence and horizon.

    Parameters
    ----------
    pnl_returns : np.ndarray
        Daily return series (decimal), e.g., from compute_fixed_position_pnl_series()
    nav_eur : float
        Current portfolio NAV in EUR
    confidence : float, default 0.99
        Confidence level (0-1)
    horizon : int, default 1
        Holding period in days (scales using sqrt(horizon))

    Returns
    -------
    dict
        Keys: var_pct, var_eur, es_pct, es_eur, var_scaled_pct, var_scaled_eur,
              es_scaled_pct, es_scaled_eur, n_observations, distribution
    """
    var_1d_pct = var_historical(pnl_returns, confidence=confidence)
    es_1d_pct = es_historical(pnl_returns, confidence=confidence)

    if horizon > 1:
        var_scaled_pct = var_scale(var_1d_pct, horizon=horizon)
        es_scaled_pct = es_scale(es_1d_pct, horizon=horizon)
    else:
        var_scaled_pct = var_1d_pct
        es_scaled_pct = es_1d_pct

    return {
        'nav_eur': nav_eur,
        'var_pct': var_1d_pct,
        'var_eur': nav_eur * var_1d_pct,
        'es_pct': es_1d_pct,
        'es_eur': nav_eur * es_1d_pct,
        'var_scaled_pct': var_scaled_pct,
        'var_scaled_eur': nav_eur * var_scaled_pct,
        'es_scaled_pct': es_scaled_pct,
        'es_scaled_eur': nav_eur * es_scaled_pct,
        'n_observations': len(pnl_returns),
        'distribution': pnl_returns,
    }


def compute_fixed_position_var_1day(
    engine: Engine,
    fund_id: str,
    valuation_date: str,
    lookback: int = 250,
    confidence: float | list = 0.99,
    horizon: int = 1,
) -> dict | list:
    """
    Compute 1-day fixed-position VaR at one or multiple confidence levels.

    For efficiency: P&L series computed once, then VaR extracted at all requested
    confidence levels from the same distribution.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    fund_id : str
    valuation_date : str
        YYYY-MM-DD
    lookback : int, default 250
    confidence : float or list, default 0.99
        Single confidence level (0.99) or list ([0.95, 0.975, 0.99])
    horizon : int, default 1
        Holding period in days

    Returns
    -------
    dict (if confidence is float)
        VaR result for single confidence level
    list of dicts (if confidence is list)
        VaR results for all requested confidence levels
    """
    pnl_returns, nav = compute_fixed_position_pnl_series(
        engine, fund_id, valuation_date, lookback
    )

    if isinstance(confidence, list):
        return [compute_var_from_pnl(pnl_returns, nav, c, horizon) for c in confidence]
    else:
        return compute_var_from_pnl(pnl_returns, nav, confidence, horizon)
