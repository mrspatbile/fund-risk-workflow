"""
leverage.py
===========
Pure leverage computation module.

Computes gross and commitment leverage per EU Regulation 231/2013 Articles 7-8.

All functions are stateless, depend only on numpy/pandas, and require
no database access, file I/O, or external services (Bloomberg is optional).

Functions
---------
    compute_leverage()   Gross and commitment leverage (EU231/2013 Arts. 7-8)
"""

import pandas as pd


def compute_leverage(
    positions_df: pd.DataFrame,
    nav: float,
    bbg=None,
    deriv_bbg_map: dict | None = None,
    currency_bbg_map: dict | None = None,
    external_borrowings_eur: float = 0.0,
) -> dict:
    """
    Compute gross and commitment leverage per EU231/2013 Articles 7-8.

    Mirrors the Section 4 notebook computation exactly when bbg and maps
    are provided. Falls back to abs(market_value_eur) for derivatives
    when bbg is not available (conservative; correct for linear instruments).

    Parameters
    ----------
    positions_df     : enriched positions DataFrame
    nav              : fund NAV in EUR
    bbg              : MockBloomberg instance (optional)
    deriv_bbg_map    : dict  instrument_name → BBG ticker
    currency_bbg_map : dict  CCY → BBG FX ticker  e.g. {'USD': 'EURUSD Curncy'}
    external_borrowings_eur : float, default 0.0
        External borrowings in EUR (e.g., from parent company)

    Returns
    -------
    dict with keys:
        gross_leverage, commitment_leverage,
        gross_exposure, commitment_exposure,
        long_eq, short_hedge, short_spec, net_eq,
        bonds, fx_exposure, deriv_notional_commitment, borrowings
    """
    df = positions_df.copy()
    df['abs_exposure'] = df['market_value_eur'].abs()

    # ── derivative notionals ───────────────────────────────────────────────
    deriv_gross_map:      dict = {}
    deriv_commitment_map: dict = {}

    for idx, row in df[df['asset_class'] == 'Derivative'].iterrows():
        use_bbg = (
            bbg is not None
            and deriv_bbg_map is not None
            and row['instrument_name'] in deriv_bbg_map
        )
        if use_bbg:
            ticker  = deriv_bbg_map[row['instrument_name']]
            bd      = bbg.bdp(ticker, ['DELTA', 'OPT_UNDL_PX', 'CONTRACT_SIZE', 'CRNCY'])
            delta   = bd.loc[ticker, 'DELTA']
            undl_px = bd.loc[ticker, 'OPT_UNDL_PX']
            csize   = bd.loc[ticker, 'CONTRACT_SIZE']
            ccy     = bd.loc[ticker, 'CRNCY']
            qty     = row['quantity']
            fx_rate = 1.0
            if ccy != 'EUR' and currency_bbg_map and ccy in currency_bbg_map:
                fx_tkr  = currency_bbg_map[ccy]
                fx_rate = 1 / bbg.bdp(fx_tkr, ['PX_LAST']).loc[fx_tkr, 'PX_LAST']
            deriv_gross_map[idx]      = abs(qty) * csize * undl_px * fx_rate
            deriv_commitment_map[idx] = (
                delta * qty * csize * undl_px * fx_rate
                if row.get('is_hedge', 0) != 1 else 0.0
            )
        else:
            deriv_gross_map[idx]      = abs(row['market_value_eur'])
            deriv_commitment_map[idx] = (
                row['market_value_eur']
                if row.get('is_hedge', 0) != 1 else 0.0
            )

    # ── gross (Art. 7) ─────────────────────────────────────────────────
    # Cash (uninvested) excluded; Borrowing handled separately below.
    gross_exposure = df.apply(
        lambda r: deriv_gross_map.get(r.name, 0.0) if r['asset_class'] == 'Derivative'
        else (0.0 if r['asset_class'] in ('Cash', 'Borrowing') else r['abs_exposure']),
        axis=1,
    ).sum()

    # Borrowings — EU231/2013 Recital 13: all borrowings included at absolute value.
    # Exception (Recital 14): capital call credit facilities that are temporary and fully
    # covered by investor commitments are excluded (PE/infra only, not applicable to HF).
    borrowings = df.loc[df['asset_class'] == 'Borrowing', 'market_value_eur'].abs().sum()
    borrowings += abs(external_borrowings_eur)

    gross_exposure += borrowings
    gross_leverage  = gross_exposure / nav if nav else 0.0

    # ── commitment (Art. 8) ────────────────────────────────────────────
    mask_eq    = df['asset_class'] == 'Equity'
    mask_long  = df['market_value_eur'] >= 0
    mask_hedge = df['is_hedge'].fillna(0) == 1

    long_eq     = df.loc[mask_eq & mask_long,               'market_value_eur'].sum()
    short_hedge = df.loc[mask_eq & ~mask_long & mask_hedge,  'market_value_eur'].sum()
    short_spec  = df.loc[mask_eq & ~mask_long & ~mask_hedge, 'market_value_eur'].abs().sum()
    net_eq      = abs(long_eq + short_hedge) + short_spec

    bonds = df.loc[
        df['asset_class'].isin(['Bond', 'Loan', 'CLO']), 'market_value_eur'
    ].abs().sum()

    fx_exposure = df.loc[
        (df['asset_class'] == 'FX') & (df['is_hedge'].fillna(0) != 1),
        'market_value_eur',
    ].abs().sum()

    deriv_notional_commitment = sum(deriv_commitment_map.values())
    # Borrowings also added to commitment exposure (Recital 13 applies to both methods).
    commitment_exposure = net_eq + bonds + fx_exposure + deriv_notional_commitment + borrowings
    commitment_leverage = commitment_exposure / nav if nav else 0.0

    return {
        'gross_leverage'            : gross_leverage,
        'commitment_leverage'       : commitment_leverage,
        'gross_exposure'            : gross_exposure,
        'commitment_exposure'       : commitment_exposure,
        'long_eq'                   : long_eq,
        'short_hedge'               : short_hedge,
        'short_spec'                : short_spec,
        'net_eq'                    : net_eq,
        'bonds'                     : bonds,
        'fx_exposure'               : fx_exposure,
        'deriv_notional_commitment' : deriv_notional_commitment,
        'borrowings'                : borrowings,
    }
