"""
P&L Attribution analysis — daily factor decomposition.

Implements sensitivity-based attribution against market risk factors
(equity, rates, FX) with residual quality monitoring.

Regulatory context:
    AIFMD Art. 15 — risk function must monitor each position's contribution
                    to overall risk profile and return drivers
    CSSF expects risk manager to explain return/loss by factor
"""

import numpy as np
import pandas as pd
import sqlalchemy as sa
from src.risk.risk_utils import compute_pnl_attribution
from src.data.database import query_nav_history


def compute_daily_attribution(
    engine,
    fund_id: str,
    bbg,
    valuation_date: str,
    residual_threshold_pct: float = 0.20,
) -> dict:
    """
    Compute daily P&L attribution by risk factor.

    Parameters
    ----------
    engine : SQLAlchemy engine
        Database connection
    fund_id : str
        Fund identifier (e.g., 'AIFM_HedgeFund')
    bbg : MockBloomberg or BloombergAPI
        Bloomberg data provider
    valuation_date : str
        Valuation date for end of period (YYYY-MM-DD)
    residual_threshold_pct : float, optional
        Threshold for flagging residual attribution (default 0.20 = 20%)

    Returns
    -------
    dict with keys:
        attr : pd.DataFrame
            Daily attribution with columns:
            pnl_equity, pnl_rates, pnl_fx, pnl_residual, pct_explained
        flagged : pd.DataFrame
            Days where residual exceeds threshold
        attr_cumsum : pd.DataFrame
            Cumulative attribution (for plotting)
    """

    # ── Daily P&L ────────────────────────────────────────────────────────────
    nav_history = query_nav_history(engine, fund_id)
    nav_history['date'] = pd.to_datetime(nav_history['date'])
    nav_history = nav_history.set_index('date').sort_index()
    pnl_actual = nav_history['pnl_eur'].dropna()

    start_date = pnl_actual.index.min().strftime('%Y-%m-%d')
    valuation_date_str = valuation_date

    # ── Market factors ───────────────────────────────────────────────────────
    # Equity: SPY total return
    spy_bm = bbg.bdh('SPY US Equity', 'PX_LAST', start_date, valuation_date_str)
    spy_bm['r_market'] = spy_bm['PX_LAST'].pct_change()

    # Rates: simulated parallel yield shift
    np.random.seed(42)
    rate_series = pd.Series(
        np.random.normal(0, 0.0005, len(spy_bm)),
        index=spy_bm.index,
        name='dy',
    )

    # FX: EUR/USD
    usd = bbg.bdh('EURUSD Curncy', 'PX_LAST', start_date, valuation_date_str)
    usd['r_fx_USD'] = usd['PX_LAST'].pct_change()

    # Combined market moves
    market_moves = pd.DataFrame(index=spy_bm.index)
    market_moves['r_market'] = spy_bm['r_market']
    market_moves['dy'] = rate_series
    market_moves['r_fx_USD'] = usd['r_fx_USD']
    market_moves = market_moves.dropna()

    # ── Positions history ────────────────────────────────────────────────────
    with engine.connect() as conn:
        positions_history = pd.read_sql(
            sa.text(
                """
            SELECT p.date, p.isin, p.asset_class, p.currency,
                   p.market_value_eur, pe.beta, pe.dur_adj_mid
            FROM positions p
            LEFT JOIN positions_enriched pe
                ON p.isin = pe.isin AND p.fund_id = pe.fund_id
            WHERE p.fund_id = :fund_id
            ORDER BY p.date
        """
            ),
            conn,
            params={'fund_id': fund_id},
        )

    positions_history['date'] = pd.to_datetime(positions_history['date'])

    # ── Alignment ────────────────────────────────────────────────────────────
    common_dates = market_moves.index.intersection(pnl_actual.index)
    market_moves_aln = market_moves.loc[common_dates]
    pnl_aligned = pnl_actual.loc[common_dates]
    pos_history_aln = positions_history[
        positions_history['date'].isin(common_dates)
    ]

    # ── Attribution ──────────────────────────────────────────────────────────
    attr = compute_pnl_attribution(pos_history_aln, market_moves_aln, pnl_aligned)

    # ── Model quality ────────────────────────────────────────────────────────
    resid_vol = attr['pnl_residual'].std()
    flagged = attr[
        (attr['pct_explained'].notna())
        & (
            (1 - attr['pct_explained'] > residual_threshold_pct)
            | (attr['pnl_residual'].abs() > 2.0 * resid_vol)
        )
    ].copy()

    # Cumulative for plotting
    attr_cumsum = (
        attr[['pnl_equity', 'pnl_rates', 'pnl_fx', 'pnl_residual']].cumsum() / 1e6
    )

    return {
        'attr': attr,
        'flagged': flagged,
        'attr_cumsum': attr_cumsum,
    }
