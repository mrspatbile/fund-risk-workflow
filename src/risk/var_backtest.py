"""
var_backtest.py
===============
Fixed-position historical VaR with duration-based bond P&L and backtesting.

Functions
---------
    compute_var_backtest_fixed_position_multi_duration: rolling VaR computation
    get_yield_tenor_for_bond: map bond maturity to constant-tenor yield series
    create_var_es_summary: extract latest VaR/ES for display
    create_backtest_report_multi_confidence: Kupiec & Christoffersen tests
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from sqlalchemy import text

from src.data.database import query_positions
from src.data.mock_bloomberg import MockBloomberg
from src.risk.risk_utils import kupiec_test, christoffersen_test


def get_yield_tenor_for_bond(maturity_str: str, currency: str) -> str:
    """
    Map bond maturity to constant-tenor yield series.

    Parameters
    ----------
    maturity_str : str
        Bond maturity date (e.g., '2029-08-15')
    currency : str
        Currency code (e.g., 'EUR', 'USD')

    Returns
    -------
    str
        Tenor series name (e.g., 'EUR_2Y', 'USD_5Y')
    """
    try:
        maturity = pd.Timestamp(maturity_str)
        years_to_maturity = (maturity - pd.Timestamp('2026-05-13')).days / 365.25
    except:
        years_to_maturity = 5

    if currency == 'EUR':
        if years_to_maturity <= 3:
            return 'EUR_2Y'
        elif years_to_maturity <= 7:
            return 'EUR_5Y'
        else:
            return 'EUR_10Y'
    else:
        if years_to_maturity <= 3:
            return 'USD_2Y'
        elif years_to_maturity <= 7:
            return 'USD_5Y'
        else:
            return 'USD_10Y'


def compute_var_backtest_fixed_position_multi_duration(
    engine,
    fund_id,
    start_date,
    end_date,
    confidence_levels=[0.95, 0.975, 0.99],
    lookback=250,
    buffer_days=120,
):
    """
    Rolling fixed-position Historical VaR with duration-based bond P&L.

    For each date d:
    1. Fix portfolio at date d (quantities and market values).
    2. For non-bond positions: compute daily P&L from price changes.
    3. For bond positions: compute daily P&L as -duration × MV × Δyield.
    4. Calculate 1-day VaR using 250-day historical return distribution.
    5. Compute realized P&L from day d to d+1 for backtesting.

    Bond-to-yield-tenor mapping is based on bond maturity (e.g., 2-3Y bonds use EUR_2Y).

    **Limitation:** Bond VaR captures interest-rate risk only.
    Credit spread risk is not yet modeled.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    fund_id : str
    start_date : str or Timestamp
        Start date (format: YYYY-MM-DD)
    end_date : str or Timestamp
        End date (format: YYYY-MM-DD)
    confidence_levels : list of float, default [0.95, 0.975, 0.99]
        Confidence levels for VaR computation
    lookback : int, default 250
        Number of business days for historical lookback
    buffer_days : int, default 120
        Additional days to fetch for warm-up

    Returns
    -------
    pd.DataFrame
        Columns: date, portfolio_value, realised_return,
                 var_1d_0.95, var_1d_0.975, var_1d_0.99,
                 breach_0.95, breach_0.975, breach_0.99
    """
    bbg = MockBloomberg()
    rows = []

    for d in pd.date_range(start_date, end_date, freq="B"):
        try:
            d_str = d.strftime("%Y-%m-%d")

            # Load positions
            positions = query_positions(engine, fund_id, d_str)
            positions = positions.dropna(subset=["bloomberg_ticker", "quantity"])

            if positions.empty:
                continue

            qty = positions.groupby("bloomberg_ticker")["quantity"].sum().astype(float)
            tickers = qty.index.tolist()

            if not tickers:
                continue

            # Load enriched data (for duration)
            with engine.connect() as conn:
                enriched_sql = text(
                    'SELECT isin, dur_adj_mid FROM positions_enriched '
                    'WHERE fund_id = :fund_id AND date = :date'
                )
                enriched = pd.read_sql(enriched_sql, conn,
                                      params={'fund_id': fund_id, 'date': d_str})

            # Map ISIN to duration
            duration_dict = dict(zip(enriched['isin'], enriched['dur_adj_mid']))

            # Identify bonds and non-bonds
            bonds_in_portfolio = positions[positions['asset_class'] == 'Bond']
            bond_tickers = bonds_in_portfolio['bloomberg_ticker'].unique().tolist()
            non_bond_tickers = [t for t in tickers if t not in bond_tickers]

            # Get currency
            bond_currency = bonds_in_portfolio['currency'].iloc[0] if len(bonds_in_portfolio) > 0 else 'EUR'

            # Map bonds to tenors based on maturity
            bond_tenor_map = {}
            for bond_ticker in bond_tickers:
                bond_pos = positions[positions['bloomberg_ticker'] == bond_ticker].iloc[0]
                maturity = bond_pos['maturity']
                tenor = get_yield_tenor_for_bond(maturity, bond_currency)
                bond_tenor_map[bond_ticker] = tenor

            # Query price history for non-bonds
            price_start = d - timedelta(days=lookback + buffer_days)
            price_end = d

            prices = None
            if non_bond_tickers:
                raw = bbg.bdh(non_bond_tickers, 'PX_LAST',
                             price_start.strftime("%Y-%m-%d"),
                             price_end.strftime("%Y-%m-%d"))
                if len(non_bond_tickers) == 1:
                    prices = raw[["PX_LAST"]].rename(columns={"PX_LAST": non_bond_tickers[0]})
                else:
                    prices = raw["PX_LAST"].unstack("security")
                prices = prices.sort_index().dropna(how="any")

            # Query yield history for bonds (one query per unique tenor)
            yields_dict = {}
            unique_tenors = set(bond_tenor_map.values()) if bond_tenor_map else set()

            for tenor in unique_tenors:
                yields = bbg.bdh(tenor, 'YLD_YTM_MID',
                                price_start.strftime("%Y-%m-%d"),
                                price_end.strftime("%Y-%m-%d"))
                if isinstance(yields.index, pd.MultiIndex):
                    yields = yields.xs(tenor, level='security')
                yields = yields.sort_index().dropna()
                yields_dict[tenor] = yields

            # Check data availability
            has_enough_prices = prices is not None and len(prices) >= lookback + 2
            has_enough_yields = len(yields_dict) > 0 and all(len(y) >= lookback + 2 for y in yields_dict.values())

            if not (has_enough_prices or has_enough_yields):
                continue

            # Trim to lookback + 2
            if has_enough_prices:
                prices = prices.tail(lookback + 2)

            for tenor in yields_dict:
                if len(yields_dict[tenor]) >= lookback + 2:
                    yields_dict[tenor] = yields_dict[tenor].tail(lookback + 2)

            # Get latest prices/yields for portfolio valuation
            portfolio_value = 0.0

            if has_enough_prices:
                for ticker in non_bond_tickers:
                    if ticker in prices.columns:
                        portfolio_value += qty.get(ticker, 0) * prices[ticker].iloc[-2]

            for bond_ticker in bond_tickers:
                bond_pos = positions[positions['bloomberg_ticker'] == bond_ticker].iloc[0]
                portfolio_value += bond_pos['market_value_eur']

            if portfolio_value <= 0:
                continue

            # Compute daily P&L for non-bonds (price-based)
            all_daily_pnls = []

            if has_enough_prices:
                hist_prices = prices.iloc[:-1]
                for ticker in non_bond_tickers:
                    if ticker in hist_prices.columns:
                        daily_change = hist_prices[ticker].diff()
                        daily_pnl = qty.get(ticker, 0) * daily_change
                        all_daily_pnls.append(daily_pnl)

            # Compute daily P&L for bonds (duration-based)
            for bond_ticker in bond_tickers:
                tenor = bond_tenor_map[bond_ticker]
                if tenor in yields_dict and len(yields_dict[tenor]) > 0:
                    bond_pos = positions[positions['bloomberg_ticker'] == bond_ticker].iloc[0]
                    isin = bond_pos['isin']
                    duration = duration_dict.get(isin)

                    if duration and not pd.isna(duration):
                        hist_yields = yields_dict[tenor].iloc[:-1]
                        daily_yield_change = hist_yields.diff()
                        daily_pnl = -duration * bond_pos['market_value_eur'] * daily_yield_change
                        all_daily_pnls.append(daily_pnl)

            if not all_daily_pnls:
                continue

            total_daily_pnl = pd.concat(all_daily_pnls, axis=1).sum(axis=1)
            hist_returns = (total_daily_pnl / portfolio_value).dropna()
            hist_returns = hist_returns.tail(lookback)

            if len(hist_returns) != lookback:
                continue

            # Compute realized P&L
            realised_pnl = 0.0

            # Non-bonds
            if has_enough_prices:
                for ticker in non_bond_tickers:
                    if ticker in prices.columns:
                        realised_pnl += qty.get(ticker, 0) * (prices[ticker].iloc[-1] - prices[ticker].iloc[-2])

            # Bonds
            for bond_ticker in bond_tickers:
                tenor = bond_tenor_map[bond_ticker]
                if tenor in yields_dict and len(yields_dict[tenor]) >= 2:
                    bond_pos = positions[positions['bloomberg_ticker'] == bond_ticker].iloc[0]
                    isin = bond_pos['isin']
                    duration = duration_dict.get(isin)

                    if duration and not pd.isna(duration):
                        yield_series = yields_dict[tenor]
                        realised_pnl += -duration * bond_pos['market_value_eur'] * (yield_series.iloc[-1] - yield_series.iloc[-2])

            realised_return = realised_pnl / portfolio_value

            # Compute VaR for each confidence level
            row = {
                "date": d,
                "portfolio_value": portfolio_value,
                "realised_return": realised_return,
            }

            for conf in confidence_levels:
                alpha = 1 - conf
                quantile_val = np.quantile(hist_returns, alpha)
                var_1d = float(-quantile_val)
                row[f"var_1d_{conf}"] = var_1d
                row[f"breach_{conf}"] = realised_return < -var_1d

            rows.append(row)

        except Exception:
            continue

    return pd.DataFrame(rows).reset_index(drop=True)


def create_var_es_summary(backtest_df: pd.DataFrame, confidence: float = 0.99) -> dict:
    """
    Extract latest VaR/ES for display_var_es.

    Parameters
    ----------
    backtest_df : pd.DataFrame
        Output from compute_var_backtest_fixed_position_multi_duration
    confidence : float, default 0.99
        Which confidence level to extract (0.95, 0.975, or 0.99)

    Returns
    -------
    dict with keys: var_1d, var_20d, es_1d, es_20d, nav
    """
    if backtest_df.empty:
        raise ValueError("No backtest data")

    latest = backtest_df.iloc[-1]
    var_1d = latest[f'var_1d_{confidence}']

    return {
        'var_1d': var_1d,
        'var_20d': var_1d * np.sqrt(20),
        'es_1d': var_1d * 1.25,  # Rough approximation
        'es_20d': var_1d * 1.25 * np.sqrt(20),
        'nav': latest['portfolio_value'],
    }


def create_backtest_report_multi_confidence(
    backtest_df: pd.DataFrame,
    confidence_levels: list = [0.95, 0.975, 0.99],
    window_size: int = 250
) -> pd.DataFrame:
    """
    Create backtest report with Kupiec & Christoffersen tests.

    Parameters
    ----------
    backtest_df : pd.DataFrame
        Output from compute_var_backtest_fixed_position_multi_duration
    confidence_levels : list, default [0.95, 0.975, 0.99]
        Confidence levels to test
    window_size : int, default 250
        Lookback window for VaR (for documentation)

    Returns
    -------
    pd.DataFrame
        One row per confidence level with Kupiec/Christoffersen results
    """
    # Use last window_size observations only
    bt_window = backtest_df.tail(window_size).copy()
    bt_window = bt_window.dropna(subset=['realised_return'])

    rows = []

    for confidence in confidence_levels:
        var_col = f'var_1d_{confidence}'

        if var_col not in bt_window.columns:
            continue

        # Ensure data is numeric and clean
        returns = pd.to_numeric(bt_window['realised_return'], errors='coerce').values
        var_series = pd.to_numeric(bt_window[var_col], errors='coerce').values

        # Remove NaN pairs
        mask = ~(np.isnan(returns) | np.isnan(var_series))
        returns = returns[mask]
        var_series = var_series[mask]

        if len(returns) < 10:
            continue

        kupiec_result = kupiec_test(
            returns_series=returns,
            var_series=var_series,
            confidence=confidence,
        )

        christoffersen_result = christoffersen_test(
            returns_series=returns,
            var_series=var_series,
            confidence=confidence,
        )

        result = 'PASS' if (
            kupiec_result['result'] == 'PASS' and
            christoffersen_result['result'] == 'PASS'
        ) else 'FAIL'

        rows.append({
            'model': '1-Day Historical',
            'confidence': f'{confidence*100:.2f}%',
            'n_obs': kupiec_result['n_obs'],
            'n_breaches': kupiec_result['n_breaches'],
            'breach_rate': kupiec_result['breach_rate'],
            'expected': kupiec_result['expected'],
            'kupiec_p': kupiec_result['p_value'],
            'christoffersen_p': christoffersen_result['p_value'],
            'result': result,
        })

    return pd.DataFrame(rows)
