"""
var_backtest.py
===============
Fixed-position VaR with modular P&L and VaR computation.

Functions
---------
    compute_pnl_series_fixed_position: compute P&L series (price + duration-based)
    compute_var_historical_multi_confidence: historical VaR from P&L series
    compute_var_parametric_multi_confidence: parametric VaR from P&L series (TODO)
    get_yield_tenor_for_bond: map bond maturity to constant-tenor yield
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


def compute_pnl_series_fixed_position(
    engine,
    fund_id,
    start_date,
    end_date,
    lookback=250,
    buffer_days=120,
) -> pd.DataFrame:
    """
    Compute fixed-position P&L series with duration-based bond P&L.

    For each date d:
    - Fix portfolio at date d
    - For non-bonds: daily P&L = qty × (price_d - price_d-1)
    - For bonds: daily P&L = -duration × MV × Δyield

    **Limitation:** Bond P&L captures interest-rate risk only.
    Credit spread risk is not yet modeled.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    fund_id : str
    start_date : str or Timestamp
    end_date : str or Timestamp
    lookback : int, default 250
        Number of business days for lookback (needed for data fetch)
    buffer_days : int, default 120
        Additional days to fetch

    Returns
    -------
    pd.DataFrame
        Columns: date, portfolio_value, realised_return
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

            duration_dict = dict(zip(enriched['isin'], enriched['dur_adj_mid']))

            # Identify bonds
            bonds_in_portfolio = positions[positions['asset_class'] == 'Bond']
            bond_tickers = bonds_in_portfolio['bloomberg_ticker'].unique().tolist()
            non_bond_tickers = [t for t in tickers if t not in bond_tickers]

            bond_currency = bonds_in_portfolio['currency'].iloc[0] if len(bonds_in_portfolio) > 0 else 'EUR'

            # Map bonds to tenors
            bond_tenor_map = {}
            for bond_ticker in bond_tickers:
                bond_pos = positions[positions['bloomberg_ticker'] == bond_ticker].iloc[0]
                maturity = bond_pos['maturity']
                tenor = get_yield_tenor_for_bond(maturity, bond_currency)
                bond_tenor_map[bond_ticker] = tenor

            # Query price history
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

            # Query yield history for bonds
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

            if has_enough_prices:
                prices = prices.tail(lookback + 2)
            for tenor in yields_dict:
                if len(yields_dict[tenor]) >= lookback + 2:
                    yields_dict[tenor] = yields_dict[tenor].tail(lookback + 2)

            # Portfolio value at d-1
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

            # Realized P&L (d-1 to d)
            realised_pnl = 0.0
            if has_enough_prices:
                for ticker in non_bond_tickers:
                    if ticker in prices.columns:
                        realised_pnl += qty.get(ticker, 0) * (prices[ticker].iloc[-1] - prices[ticker].iloc[-2])

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

            rows.append({
                "date": d,
                "portfolio_value": portfolio_value,
                "realised_return": realised_return,
            })

        except Exception:
            continue

    return pd.DataFrame(rows).reset_index(drop=True)


def compute_var_historical_multi_confidence(
    pnl_series: pd.DataFrame,
    confidence_levels: list = [0.95, 0.975, 0.99],
    lookback: int = 250,
) -> pd.DataFrame:
    """
    Compute historical VaR from P&L series for multiple confidence levels.

    For each date d, uses the previous `lookback` days to estimate the loss distribution,
    then computes the quantile for each confidence level.

    Parameters
    ----------
    pnl_series : pd.DataFrame
        Output from compute_pnl_series_fixed_position
        Must have columns: date, portfolio_value, realised_return
    confidence_levels : list, default [0.95, 0.975, 0.99]
        Confidence levels for VaR
    lookback : int, default 250
        Number of observations for rolling window

    Returns
    -------
    pd.DataFrame
        Columns: date, var_1d_0.95, var_1d_0.975, var_1d_0.99, breach_0.95, etc.
    """
    rows = []

    for i in range(lookback, len(pnl_series)):
        d = pnl_series.iloc[i]['date']
        portfolio_value = pnl_series.iloc[i]['portfolio_value']

        # Get previous 250 returns
        window_returns = pnl_series.iloc[i-lookback:i]['realised_return'].values

        row = {
            "date": d,
            "portfolio_value": portfolio_value,
            "realised_return": pnl_series.iloc[i]['realised_return'],
        }

        # Compute VaR for each confidence level
        for conf in confidence_levels:
            alpha = 1 - conf
            quantile_val = np.quantile(window_returns, alpha)
            var_1d = float(-quantile_val)
            row[f"var_1d_{conf}"] = var_1d
            row[f"breach_{conf}"] = pnl_series.iloc[i]['realised_return'] < -var_1d

        rows.append(row)

    return pd.DataFrame(rows).reset_index(drop=True)


def compute_var_parametric_multi_confidence(
    pnl_series: pd.DataFrame,
    confidence_levels: list = [0.95, 0.975, 0.99],
    lookback: int = 250,
    dist: str = 'normal',
) -> pd.DataFrame:
    """
    Compute parametric VaR from P&L series (placeholder for future implementation).

    Parameters
    ----------
    pnl_series : pd.DataFrame
        Output from compute_pnl_series_fixed_position
    confidence_levels : list
    lookback : int
    dist : str
        Distribution assumption ('normal', 'student_t', etc.)

    Returns
    -------
    pd.DataFrame
        Same structure as compute_var_historical_multi_confidence
    """
    raise NotImplementedError("Parametric VaR not yet implemented. Use historical VaR.")


def create_var_es_summary(backtest_df: pd.DataFrame, confidence: float = 0.99) -> dict:
    """
    Extract latest VaR/ES for display_var_es.

    Parameters
    ----------
    backtest_df : pd.DataFrame
        Output from compute_var_historical_multi_confidence
    confidence : float, default 0.99
        Which confidence level to extract

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
        Output from compute_var_historical_multi_confidence
    confidence_levels : list
    window_size : int

    Returns
    -------
    pd.DataFrame
        One row per confidence level with test results
    """
    bt_window = backtest_df.tail(window_size).copy()
    bt_window = bt_window.dropna(subset=['realised_return'])

    rows = []

    for confidence in confidence_levels:
        var_col = f'var_1d_{confidence}'

        if var_col not in bt_window.columns:
            continue

        returns = pd.to_numeric(bt_window['realised_return'], errors='coerce').values
        var_series = pd.to_numeric(bt_window[var_col], errors='coerce').values

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
