"""
risk_utils.py
=============
Shared risk utility functions for AIFM and UCITS risk notebooks.
Implements VaR, ES, backtesting, stress scenarios and liquidity
functions in compliance with AIFMD, UCITS and ESMA guidelines.

Regulatory context
------------------
    AIFMD        : Directive 2011/61/EU
    UCITS        : Directive 2009/65/EC
    AIFMD II     : Directive 2024/927/EU (LMT tools — Article 16a)
    ESMA LST     : ESMA34-39-897 (liquidity stress testing)
    ESMA backt.  : ESMA34-43-392 (VaR backtesting)
    Annex VI     : AIFMD Level 2 stress testing framework

Usage
-----
    from risk_utils import (
        var_historical, var_parametric, var_scale,
        es_historical, es_parametric, es_scale,
        kupiec_test, christoffersen_test,
        exception_report, full_backtest_report,
        stress_equity, stress_rates, stress_credit,
        stress_fx, stress_combined, stress_historical,
        stress_property, stress_rental, stress_ltv,
        days_to_liquidate, liquidity_buckets,
        redemption_stress, lmt_trigger_analysis,
        investor_concentration, load_investor_register,
        'load_counterparty',
        liquidity_adjusted_var, 'compute_pnl_attribution',
        'pre_trade_check',
    )
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm, t as student_t
from typing import Optional
from pathlib import Path

HISTORICAL_SCENARIOS = {
        '2008': {
            'name'         : 'GFC 2008 (Sep-Dec 2008)',
            'delta_equity' : -0.40,
            'delta_y'      : -0.01,
            'delta_spread' : 0.03,
            'fx_shocks'    : {'USD': -0.05, 'GBP': -0.15},
        },
        '2011': {
            'name'         : 'EU Sovereign Debt Crisis 2011 (Jul-Nov 2011)',
            'delta_equity' : -0.25,
            'delta_y'      : -0.015,
            'delta_spread' : 0.02,
            'fx_shocks'    : {'USD': 0.15, 'GBP': 0.02},
        },
        '2020': {
            'name'         : 'Covid 2020 (Feb-Mar 2020)',
            'delta_equity' : -0.30,
            'delta_y'      : -0.005,
            'delta_spread' : 0.02,
            'fx_shocks'    : {'USD': 0.05, 'GBP': -0.05},
        },
        '2022': {
            'name'         : 'Rate shock 2022 (Jan-Dec 2022)',
            'delta_equity' : -0.20,
            'delta_y'      : 0.03,
            'delta_spread' : 0.015,
            'fx_shocks'    : {'USD': 0.10, 'GBP': -0.05},
        },
    }

_DIR = Path(__file__).parent.parent 


# ================================================================
# VaR functions
# ================================================================

def var_historical(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Historical simulation VaR.
    Sorts actual returns and reads off empirical quantile.
    No distribution assumption.

    Parameters
    ----------
    returns : array-like
        Daily portfolio returns in decimal (e.g. -0.02 for -2%)
    confidence : float
        Confidence level. Default 0.99 (AIFMD standard).

    Returns
    -------
    float
        VaR as positive number (loss convention).
        e.g. 0.025 means 2.5% of NAV at risk.

    Examples
    --------
    >>> returns = np.random.normal(0, 0.01, 250)
    >>> var = var_historical(returns, confidence=0.99)
    >>> print(f'99% VaR: {var:.4f}')
    """
    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]
    alpha   = 1 - confidence
    return float(-np.percentile(returns, alpha * 100))


def var_parametric(
    mu: float,
    sigma: float,
    confidence: float = 0.99,
    dist: str = 't',
    df: int = 5,
) -> float:
    """
    Parametric VaR under normal or Student-t distribution.

    VaR = -(mu + z_alpha * sigma)

    sigma is an explicit input, agnostic to source:
    - historical rolling volatility
    - risk system output (Bloomberg PORT, Axioma)
    - fund administrator assumption (illiquid assets)

    Parameters
    ----------
    mu : float
        Mean daily return in decimal.
    sigma : float
        Daily volatility in decimal.
    confidence : float
        Confidence level. Default 0.99.
    dist : str
        Distribution: 't' (Student-t) or 'normal'.
        Student-t recommended for fat tails. Default 't'.
    df : int
        Degrees of freedom for Student-t. Default 5.

    Returns
    -------
    float
        VaR as positive number (loss convention).

    Examples
    --------
    >>> var = var_parametric(mu=0.0005, sigma=0.012,
    ...                      confidence=0.99, dist='t', df=5)
    """
    alpha = 1 - confidence
    if dist == 't':
        z = student_t.ppf(alpha, df=df)
    else:
        z = norm.ppf(alpha)
        
    return float(-(mu + z * sigma))


def var_scale(
    var_1d: float,
    horizon: int = 10, 
) -> float:
    """
    Scale 1-day VaR to longer horizon using square root of time.

    VaR_Td = VaR_1d * sqrt(T)

    Common horizons:
    - 10 days : Basel III regulatory VaR
    - 20 days : UCITS and AIFMD standard

    Parameters
    ----------
    var_1d : float
        1-day VaR as positive number.
    horizon : int
        Number of trading days. Default 10.

    Returns
    -------
    float
        Scaled VaR as positive number.

    Examples
    --------
    >>> var_10d = var_scale(var_1d=0.025, horizon=10)
    >>> var_20d = var_scale(var_1d=0.025, horizon=20)
    """
    return float(var_1d * np.sqrt(horizon))


# ================================================================
# Expected Shortfall functions
# ================================================================

def es_historical(
    returns: np.ndarray | pd.Series,
    confidence: float = 0.99
) -> float:
    """
    Historical Expected Shortfall (CVaR).
    Mean of all returns that breach the VaR threshold.

    ES_alpha = -E[R | R < -VaR]

    Apply to liquid portion only.

    Parameters
    ----------
    returns : array-like
        Daily portfolio returns in decimal.
    confidence : float
        Confidence level. Default 0.99.

    Returns
    -------
    float
        ES as positive number (loss convention).
        Always >= var_historical(returns, confidence).

    Examples
    --------
    >>> returns = np.random.normal(0, 0.01, 250)
    >>> es = es_historical(returns, confidence=0.99)
    """
    returns  = np.asarray(returns)
    returns  = returns[~np.isnan(returns)]
    var      = var_historical(returns, confidence)
    breaches = returns[returns < -var]
    if len(breaches) == 0:
        return var
    return float(-breaches.mean())


def es_parametric(
    sigma: float,
    mu: float = 0.0,
    confidence: float = 0.99,
    dist: str = 't',
    df: int = 5
) -> float:
    """
    Parametric Expected Shortfall.

    - Closed formed solutions (if μ ≠ 0, subtract μ) - 
    1. Normal distribution:
        ES_alpha = sigma * phi(z_alpha) / alpha

    2. Student-t distribution:
        ES_alpha = sigma * f_t(t_alpha) * (nu + t_alpha^2)
                   / [(nu - 1) * (1 - alpha)]

    Parameters
    ----------
    sigma : float
        Daily volatility in decimal.
    mu : float
        Mean daily return. Default 0.
    confidence : float
        Confidence level. Default 0.99.
    dist : str
        'normal' or 't'. Default 't'.
    df : int
        Degrees of freedom for Student-t. Default 5.

    Returns
    -------
    float
        ES as positive number. Always >= var_parametric.

    Examples
    --------
    >>> es = es_parametric(sigma=0.012, confidence=0.99, dist='t')
    """
    alpha = 1 - confidence

    if dist == 'normal':
        z  = norm.ppf(alpha) # ppf is teh inverse of teh cdf, gives zscore s.t. P(X ≤ z) = alpha
        es = sigma * norm.pdf(z) / alpha
        return float(es - mu)

    else:  # Student-t
        t_alpha = student_t.ppf(alpha, df=df)
        f_t     = student_t.pdf(t_alpha, df=df)
        es      = sigma * f_t * (df + t_alpha**2) / ((df - 1) * alpha)
        return float(es - mu)


def es_scale(
    es_1d: float,
    horizon: int = 10
) -> float:
    """
    Scale 1-day ES to longer horizon using square root of time.

    ES_Td = ES_1d * sqrt(T)

    Parameters
    ----------
    es_1d : float
        1-day ES as positive number.
    horizon : int
        Number of trading days. Default 10.

    Returns
    -------
    float
        Scaled ES as positive number.

    Examples
    --------
    >>> es_20d = es_scale(es_1d=0.032, horizon=20)
    """
    return float(es_1d * np.sqrt(horizon))


# ================================================================
# Backtesting functions
# ================================================================

def kupiec_test(
    returns_series: np.ndarray | pd.Series,
    var_series: np.ndarray | pd.Series,
    confidence: float = 0.99
) -> dict:
    """
    Kupiec Proportion of Failures (POF) test.
    Tests whether the breach rate equals the expected rate.

    H0: breach rate = 1 - confidence
    Reject H0 if model is miscalibrated.

    Parameters
    ----------
    returns_series : array-like
        Daily P&L in decimal. Negative = loss.
    var_series : array-like
        Daily VaR estimates as positive numbers.
    confidence : float
        Confidence level. Default 0.99.

    Returns
    -------
    dict with keys:
        n_obs      : number of observations
        n_breaches : number of VaR breaches
        breach_rate: actual breach rate
        expected   : expected breach rate (1 - confidence)
        lr_stat    : likelihood ratio statistic
        p_value    : p-value (reject H0 if < 0.05)
        result     : 'PASS' or 'FAIL'

    Examples
    --------
    >>> result = kupiec_test(returns_series, var_series, confidence=0.99)
    >>> print(result['result'])
    """
    ret = np.asarray(returns_series)
    var = np.asarray(var_series)

    mask       = ~(np.isnan(ret) | np.isnan(var))
    ret, var   = ret[mask], var[mask]

    n          = len(ret)
    breaches   = (ret < -var).sum()
    p_actual   = breaches / n
    p_expected = 1 - confidence

    # handle edge cases
    if breaches == 0:
        lr = -2 * n * np.log(1 - p_expected)
    elif breaches == n:
        lr = -2 * n * np.log(p_expected)
    else:
        lr = -2 * (
            np.log((1 - p_expected)**(n - breaches) *
                   p_expected**breaches) -
            np.log((1 - p_actual)**(n - breaches) *
                   p_actual**breaches)
        )

    p_value = 1 - stats.chi2.cdf(lr, df=1)

    return {
        'n_obs'      : int(n),
        'n_breaches' : int(breaches),
        'breach_rate': round(float(p_actual), 4),
        'expected'   : round(float(p_expected), 4),
        'lr_stat'    : round(float(lr), 4),
        'p_value'    : round(float(p_value), 4),
        'result'     : 'PASS' if p_value > 0.05 else 'FAIL',
    }


def christoffersen_test(
    returns_series: np.ndarray | pd.Series,
    var_series: np.ndarray | pd.Series,
    confidence: float = 0.99
) -> dict:
    """
    Christoffersen independence test.
    Tests whether VaR breaches are independent over time.
    Clustered breaches indicate model failure even if the
    total breach count is acceptable.

    Parameters
    ----------
    returns_series : array-like
        Daily P&L in decimal.
    var_series : array-like
        Daily VaR estimates as positive numbers.
    confidence : float
        Confidence level. Default 0.99.

    Returns
    -------
    dict with keys:
        n00, n01, n10, n11 : transition counts
        p01, p11           : transition probabilities
        lr_ind             : independence LR statistic
        p_value            : p-value
        result             : 'PASS' or 'FAIL'

    Examples
    --------
    >>> result = christoffersen_test(returns, var, confidence=0.99)
    """
    ret = np.asarray(returns_series)
    var = np.asarray(var_series)

    mask     = ~(np.isnan(ret) | np.isnan(var))
    ret, var = ret[mask], var[mask]

    breaches = (ret < -var).astype(int)

    # transition counts
    n00 = ((breaches[:-1] == 0) & (breaches[1:] == 0)).sum()
    n01 = ((breaches[:-1] == 0) & (breaches[1:] == 1)).sum()
    n10 = ((breaches[:-1] == 1) & (breaches[1:] == 0)).sum()
    n11 = ((breaches[:-1] == 1) & (breaches[1:] == 1)).sum()

    # transition probabilities
    p01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0
    p11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0
    p   = (n01 + n11) / (n00 + n01 + n10 + n11)

    # LR statistic
    def safe_log(x):
        return np.log(x) if x > 0 else 0

    lr_ind = -2 * (
        (n00 + n10) * safe_log(1 - p) +
        (n01 + n11) * safe_log(p) -
        n00 * safe_log(1 - p01) -
        n01 * safe_log(p01 if p01 > 0 else 1e-10) -
        n10 * safe_log(1 - p11) -
        n11 * safe_log(p11 if p11 > 0 else 1e-10)
    )

    p_value = 1 - stats.chi2.cdf(lr_ind, df=1)

    return {
        'n00'    : int(n00),
        'n01'    : int(n01),
        'n10'    : int(n10),
        'n11'    : int(n11),
        'p01'    : round(float(p01), 4),
        'p11'    : round(float(p11), 4),
        'lr_ind' : round(float(lr_ind), 4),
        'p_value': round(float(p_value), 4),
        'result' : 'PASS' if p_value > 0.05 else 'FAIL',
    }


def exception_report(
    returns_series: pd.Series,
    var_series: pd.Series,
    confidence: float = 0.99,
    dates: Optional[pd.DatetimeIndex] = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    ESMA exception report: documents each VaR breach.
    For funds the regulatory standard is exception-based,
    not the Basel traffic light capital multiplier framework.

    Breach rate thresholds (ESMA/CSSF standard):
    - < 1% at 99% : model acceptable
    - 1-2% at 99% : review assumptions, document
    - > 2% at 99% : model review required, notify board

    Parameters
    ----------
    returns_series : pd.Series
        Daily P&L in decimal.
    var_series : pd.Series
        Daily VaR estimates as positive numbers.
    confidence : float
        Confidence level. Default 0.99.
    dates : pd.DatetimeIndex, optional
        Dates corresponding to returns and var series.

    Returns
    -------
    pd.DataFrame
        One row per breach with columns:
        date, returns, var, excess_loss, action_required
    """
    ret = np.asarray(returns_series)
    var = np.asarray(var_series)

    mask         = ~(np.isnan(ret) | np.isnan(var))
    breach_mask  = (ret < -var) & mask
    breach_idx   = np.where(breach_mask)[0]

    n            = mask.sum()
    n_breaches   = breach_mask.sum()
    breach_rate  = n_breaches / n if n > 0 else 0

    if breach_rate < 0.01:
        action = 'Model acceptable'
    elif breach_rate < 0.02:
        action = 'Review assumptions, document'
    else:
        action = 'Model review required, notify board'

    rows = []
    for idx in breach_idx:
        rows.append({
            'date'       : dates[idx] if dates is not None
                           else idx,
            'return'        : round(float(ret[idx]), 6),
            'var'        : round(float(var[idx]), 6),
            'excess_loss': round(float(-ret[idx] - var[idx]), 6),
            'action'     : action,
        })

    report = pd.DataFrame(rows)
    if verbose:
        print(f'Exception report ({confidence*100:.0f}% VaR):')
        print(f'  observations : {n}')
        print(f'  breaches     : {n_breaches}')
        print(f'  breach rate  : {breach_rate*100:.2f}%'
            f' (expected {(1-confidence)*100:.1f}%)')
        print(f'  action       : {action}')

    return report


def full_backtest_report(
    returns_series: pd.Series,
    var_dict: dict,
    dates: Optional[pd.DatetimeIndex] = None
) -> pd.DataFrame:
    """
    Full backtesting report running all tests for all
    confidence levels and models.

    Parameters
    ----------
    returns_series : pd.Series
        Daily returns in decimal.
    var_dict : dict
        Dictionary of {model_name: var_series}.
        e.g. {'historical': var_hist, 'parametric': var_param}
    dates : pd.DatetimeIndex, optional

    Returns
    -------
    pd.DataFrame
        Rows: models x confidence levels
        Columns: n_obs, n_breaches, breach_rate, expected,
                 kupiec_p, christoffersen_p, result

    Examples
    --------
    >>> report = full_backtest_report(
    ...     return,
    ...     {'historical': var_hist, 'parametric': var_param}
    ... )
    """
    rows = []
    for model_name, var_series in var_dict.items():
        for confidence in [0.99, 0.975, 0.95]:
            kup  = kupiec_test(returns_series, var_series, confidence)
            chri = christoffersen_test(
                returns_series, var_series, confidence)

            rows.append({
                'model'            : model_name,
                'confidence'       : f'{confidence*100:.1f}%',
                'n_obs'            : kup['n_obs'],
                'n_breaches'       : kup['n_breaches'],
                'breach_rate'      : kup['breach_rate'],
                'expected'         : kup['expected'],
                'kupiec_p'         : kup['p_value'],
                'christoffersen_p' : chri['p_value'],
                'result'           : (
                    'PASS'
                    if kup['result'] == 'PASS' and
                       chri['result'] == 'PASS'
                    else 'FAIL'
                ),
            })

    return pd.DataFrame(rows)


# ================================================================
# Stress scenario functions (AIFMD Annex VI)
# ================================================================

def stress_equity(
    positions: pd.DataFrame,
    delta_equity: float = -0.30
) -> dict:
    """
    Equity stress scenario.
    Applies a parallel shift to all equity positions.

    ΔP = beta * delta_equity * market_value_eur

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with columns:
        asset_class, beta, market_value_eur
    delta_equity : float
        Equity market shock. Default -0.30 (-30%).

    Returns
    -------
    dict with keys:
        stressed_pnl_eur : total P&L in EUR
        stressed_nav_pct : stressed return as % of NAV
        by_position      : pd.DataFrame with position-level P&L

    Examples
    --------
    >>> result = stress_equity(positions, delta_equity=-0.30)
    >>> print(f'Equity crash P&L: {result["stressed_pnl_eur"]:,.0f}')
    """
    eq = positions[
        positions['asset_class'].isin(['Equity', 'Real Estate'])
    ].copy()

    eq['beta']           = eq['beta'].fillna(1.0)
    eq['stressed_pnl']   = (
        eq['beta'] * delta_equity * eq['market_value_eur'])

    nav = positions['market_value_eur'].sum()

    return {
        'scenario'        : f'Equity {delta_equity*100:.0f}%',
        'stressed_pnl_eur': float(eq['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            eq['stressed_pnl'].sum() / nav * 100),
        'by_position'     : eq[[
            'instrument_name', 'asset_class',
            'market_value_eur', 'beta', 'stressed_pnl'
        ]],
    }


def stress_rates(
    positions: pd.DataFrame,
    delta_y: float = 0.02
) -> dict:
    """
    Parallel rate shift stress scenario.
    Uses duration-convexity approximation.

    ΔP = -D * Δy * MV + ½ * C * Δy² * MV

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with columns:
        asset_class, dur_adj_mid, convexity, market_value_eur
    delta_y : float
        Rate shock in decimal. Default 0.02 (+200bps).

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct, by_position

    Examples
    --------
    >>> result = stress_rates(positions, delta_y=0.02)
    >>> print(f'Rate shock P&L: {result["stressed_pnl_eur"]:,.0f}')
    """
    bonds = positions[
        positions['asset_class'].isin(
            ['Bond', 'Loan', 'CLO'])
    ].copy()

    bonds['dur_adj_mid'] = bonds['dur_adj_mid'].fillna(0.0)
    bonds['convexity']   = bonds['convexity'].fillna(0.0)

    bonds['stressed_pnl'] = (
        -bonds['dur_adj_mid'] * delta_y *
        bonds['market_value_eur'] +
        0.5 * bonds['convexity'] * delta_y**2 *
        bonds['market_value_eur']
    )

    nav = positions['market_value_eur'].sum()

    return {
        'scenario'        : f'Rates {delta_y*100:+.0f}bps',
        'stressed_pnl_eur': float(bonds['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            bonds['stressed_pnl'].sum() / nav * 100),
        'by_position'     : bonds[[
            'instrument_name', 'asset_class',
            'market_value_eur', 'dur_adj_mid',
            'convexity', 'stressed_pnl'
        ]],
    }


def stress_credit(
    positions: pd.DataFrame,
    delta_spread: float = 0.03
) -> dict:
    """
    Credit spread stress scenario.

    ΔP = -D_spread * delta_spread * MV

    Uses dur_adj_mid as proxy for spread duration
    when specific spread duration is not available.

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with columns:
        asset_class, dur_adj_mid, market_value_eur
    delta_spread : float
        Credit spread shock in decimal. Default 0.03 (+300bps).

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct, by_position

    Examples
    --------
    >>> result = stress_credit(positions, delta_spread=0.03)
    """
    credit = positions[
        positions['asset_class'].isin(
            ['Bond', 'Loan', 'CLO'])
    ].copy()

    # exclude government bonds (no credit spread)
    credit = credit[
        ~credit['sub_asset_class'].isin(
            ['Government', 'Government Bond'])
    ].copy()

    credit['dur_adj_mid']  = credit['dur_adj_mid'].fillna(0.0)
    credit['stressed_pnl'] = (
        -credit['dur_adj_mid'] * delta_spread *
        credit['market_value_eur']
    )

    nav = positions['market_value_eur'].sum()

    return {
        'scenario'        : f'Credit +{delta_spread*100:.0f}bps',
        'stressed_pnl_eur': float(credit['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            credit['stressed_pnl'].sum() / nav * 100),
        'by_position'     : credit[[
            'instrument_name', 'asset_class',
            'market_value_eur', 'dur_adj_mid', 'stressed_pnl'
        ]],
    }


def stress_fx(
    positions: pd.DataFrame,
    fx_shocks: dict | None = None
) -> dict:
    """
    FX stress scenario.

    ΔP = notional_foreign * delta_fx

    For non-EUR positions: uses market_value_eur as proxy
    for notional exposure.

    Parameters
    ----------
    positions : pd.DataFrame
        Positions with columns: currency, market_value_eur
    fx_shocks : dict, optional
        {currency: shock} e.g. {'USD': -0.10, 'GBP': -0.15}
        Default: USD -10%, GBP -15%, JPY -10%

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct, by_currency

    Examples
    --------
    >>> result = stress_fx(positions,
    ...     fx_shocks={'USD': -0.10, 'GBP': -0.15})
    """
    if fx_shocks is None:
        fx_shocks = {'USD': -0.10, 'GBP': -0.15, 'JPY': -0.10}

    fx_pos = positions[
        positions['currency'] != 'EUR'].copy()

    fx_pos['fx_shock']     = fx_pos['currency'].map(fx_shocks).fillna(0)
    fx_pos['stressed_pnl'] = (
        fx_pos['market_value_eur'] * fx_pos['fx_shock'])

    nav = positions['market_value_eur'].sum()

    by_ccy = fx_pos.groupby('currency').agg(
        market_value_eur=('market_value_eur', 'sum'),
        fx_shock=('fx_shock', 'first'),
        stressed_pnl=('stressed_pnl', 'sum')
    ).reset_index()

    return {
        'scenario'        : 'FX stress',
        'stressed_pnl_eur': float(fx_pos['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            fx_pos['stressed_pnl'].sum() / nav * 100),
        'by_currency'     : by_ccy,
    }


def stress_combined(
    positions: pd.DataFrame,
    scenario: dict | None = None
) -> dict:
    """
    Combined stress scenario applying multiple shocks
    simultaneously (AIFMD Annex VI requirement).

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions DataFrame.
    scenario : dict, optional
        Shock parameters. Default: Annex VI combined scenario.
        Keys: delta_equity, delta_y, delta_spread, fx_shocks

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct,
        equity_pnl, rates_pnl, credit_pnl, fx_pnl

    Examples
    --------
    >>> result = stress_combined(positions, scenario={
    ...     'delta_equity' : -0.20,
    ...     'delta_y'      : 0.01,
    ...     'delta_spread' : 0.015,
    ...     'fx_shocks'    : {'USD': -0.10}
    ... })
    """
    if scenario is None:
        scenario = {
            'delta_equity' : -0.20,
            'delta_y'      : 0.01,
            'delta_spread' : 0.015,
            'fx_shocks'    : {'USD': -0.10, 'GBP': -0.15},
        }

    eq_res  = stress_equity(
        positions, scenario.get('delta_equity', -0.20))
    rate_res = stress_rates(
        positions, scenario.get('delta_y', 0.01))
    cr_res  = stress_credit(
        positions, scenario.get('delta_spread', 0.015))
    fx_res  = stress_fx(
        positions, scenario.get('fx_shocks'))

    total_pnl = (
        eq_res['stressed_pnl_eur'] +
        rate_res['stressed_pnl_eur'] +
        cr_res['stressed_pnl_eur'] +
        fx_res['stressed_pnl_eur']
    )
    nav = positions['market_value_eur'].sum()

    return {
        'scenario'        : 'Combined stress',
        'stressed_pnl_eur': float(total_pnl),
        'stressed_nav_pct': float(total_pnl / nav * 100),
        'equity_pnl'      : eq_res['stressed_pnl_eur'],
        'rates_pnl'       : rate_res['stressed_pnl_eur'],
        'credit_pnl'      : cr_res['stressed_pnl_eur'],
        'fx_pnl'          : fx_res['stressed_pnl_eur'],
    }


def stress_historical(
    positions: pd.DataFrame,
    scenario: str = '2020'
) -> dict:
    """
    Historical stress scenario using predefined factor shocks
    from actual stress periods.

    Available scenarios:
    - '2008' : GFC Sep-Dec 2008
    - '2020' : Covid Feb-Mar 2020
    - '2022' : Rate shock Jan-Dec 2022

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions DataFrame.
    scenario : str
        Scenario name. Default '2020'.

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct,
        equity_pnl, rates_pnl, credit_pnl

    Examples
    --------
    >>> result = stress_historical(positions, scenario='2008')
    """
    scenarios = HISTORICAL_SCENARIOS

    if scenario not in scenarios:
        raise ValueError(
            f'Unknown scenario: {scenario}. '
            f'Choose from {list(scenarios.keys())}')

    params = scenarios[scenario]
    result = stress_combined(positions, params)
    result['scenario'] = params['name']

    return result


def stress_property(
    positions: pd.DataFrame,
    delta_value_by_type: dict | None = None
) -> dict:
    """
    Real estate property value stress scenario.
    Applied to direct property holdings only.

    ΔP = delta_property_value * market_value_eur

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with columns:
        is_direct_property, property_type, market_value_eur
    delta_value_by_type : dict, optional
        {property_type: shock}
        Default: Office -20%, Retail -25%,
                 Residential -10%, Logistics -5%

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct, by_property_type

    Examples
    --------
    >>> result = stress_property(positions,
    ...     delta_value_by_type={'Office': -0.25})
    """
    if delta_value_by_type is None:
        delta_value_by_type = {
            'Office'     : -0.20,
            'Retail'     : -0.25,
            'Residential': -0.10,
            'Logistics'  : -0.05,
        }

    direct = positions[
        positions['is_direct_property'] == True].copy()

    if direct.empty:
        return {
            'scenario'        : 'Property value stress',
            'stressed_pnl_eur': 0.0,
            'stressed_nav_pct': 0.0,
            'by_property_type': pd.DataFrame(),
        }

    direct['shock'] = direct['property_type'].map(
        delta_value_by_type).fillna(-0.15)

    # property value decline: shock is negative, so pnl is negative
    direct['stressed_pnl'] = (
        direct['shock'] * direct['market_value_eur']
    )

    nav = positions['market_value_eur'].sum()

    by_type = direct.groupby('property_type').agg(
        market_value_eur=('market_value_eur', 'sum'),
        shock=('shock', 'first'),
        stressed_pnl=('stressed_pnl', 'sum')
    ).reset_index()

    return {
        'scenario'        : 'Property value stress',
        'stressed_pnl_eur': float(direct['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            direct['stressed_pnl'].sum() / nav * 100),
        'by_property_type': by_type,
    }


def stress_rental(
    positions: pd.DataFrame,
    delta_vacancy: float = 0.10,
    delta_yield: float = -0.005
) -> dict:
    """
    Real estate rental income stress scenario.
    Applied to direct property holdings only.

    ΔIncome = (delta_vacancy + delta_yield) * market_value_eur

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with is_direct_property flag.
    delta_vacancy : float
        Vacancy rate increase in percentage points.
        Default 0.10 (+10pp).
    delta_yield : float
        Rental yield compression in decimal.
        Default -0.005 (-50bps).

    Returns
    -------
    dict with keys:
        stressed_pnl_eur, stressed_nav_pct, by_position

    Examples
    --------
    >>> result = stress_rental(positions,
    ...     delta_vacancy=0.10, delta_yield=-0.005)
    """
    direct = positions[
        positions['is_direct_property'] == True].copy()

    if direct.empty:
        return {
            'scenario'        : 'Rental income stress',
            'stressed_pnl_eur': 0.0,
            'stressed_nav_pct': 0.0,
            'by_position'     : pd.DataFrame(),
        }

    # vacancy increase and yield compression both reduce income
    # delta_vacancy is positive (more vacancy = less income)
    # delta_yield is negative (lower yield = less income)
    direct['stressed_pnl'] = (
        (-delta_vacancy + delta_yield) *
        direct['market_value_eur']
    )

    nav = positions['market_value_eur'].sum()

    return {
        'scenario'        : (f'Rental stress: vacancy '
                             f'+{delta_vacancy*100:.0f}pp, '
                             f'yield {delta_yield*100:+.0f}bps'),
        'stressed_pnl_eur': float(direct['stressed_pnl'].sum()),
        'stressed_nav_pct': float(
            direct['stressed_pnl'].sum() / nav * 100),
        'by_position'     : direct[[
            'instrument_name', 'property_type',
            'market_value_eur', 'stressed_pnl'
        ]],
    }


def stress_ltv(
    positions: pd.DataFrame,
    delta_property_value: float = -0.20,
    ltv_threshold: float = 0.75
) -> dict:
    """
    LTV covenant breach stress scenario.
    Tests whether a property value decline causes LTV
    to breach the covenant threshold.

    Parameters
    ----------
    positions : pd.DataFrame
        Enriched positions with ltv_pct column.
    delta_property_value : float
        Property value decline. Default -0.20 (-20%).
    ltv_threshold : float
        LTV covenant threshold. Default 0.75 (75%).

    Returns
    -------
    dict with keys:
        n_breaches, breaching_properties, by_position

    Examples
    --------
    >>> result = stress_ltv(positions,
    ...     delta_property_value=-0.20, ltv_threshold=0.75)
    """
    direct = positions[
        positions['is_direct_property'] == True].copy()

    if direct.empty or 'ltv_pct' not in direct.columns:
        return {
            'scenario'            : 'LTV covenant stress',
            'n_breaches'          : 0,
            'breaching_properties': [],
            'by_position'         : pd.DataFrame(),
        }

    # stressed LTV: if property value falls, LTV rises
    # stressed_ltv = current_ltv / (1 + delta_property_value)
    direct['ltv_pct_decimal'] = direct['ltv_pct'] / 100
    direct['stressed_ltv']    = (
        direct['ltv_pct_decimal'] / (1 + delta_property_value))
    direct['ltv_breach']      = (
        direct['stressed_ltv'] > ltv_threshold)

    breaching = direct[direct['ltv_breach']]

    return {
        'scenario'            : (f'LTV stress: property '
                                 f'{delta_property_value*100:.0f}%'),
        'n_breaches'          : int(direct['ltv_breach'].sum()),
        'breaching_properties': breaching[
            'instrument_name'].tolist(),
        'by_position'         : direct[[
            'instrument_name', 'property_type',
            'ltv_pct', 'stressed_ltv', 'ltv_breach'
        ]],
    }


# ================================================================
# Liquidity functions (ESMA34-39-897)
# ================================================================
def days_to_liquidate(
    positions: pd.DataFrame,
    pct_adv: float = 0.25
) -> pd.DataFrame:
    """
    Estimate days to liquidate each position assuming the
    fund can trade pct_adv of average daily volume per day.

    days_i = market_value_i / (ADV_i * pct_adv)

    Special cases (independent of ADV):
    - Cash: 0 days (immediate)
    - FX forwards: 2 days (OTC T+2 settlement)
    - Listed options/derivatives: 1 day (exchange traded)
    - Direct properties and private loans: infinity

    Parameters
    ----------
    positions : pd.DataFrame
        Positions with columns: market_value_eur, adv_eur,
        asset_class, sub_asset_class, is_direct_property
    pct_adv : float
        Fraction of ADV tradeable per day. Default 0.25.

    Returns
    -------
    pd.DataFrame
        Original positions with added column: days_to_liquidate
    """
    df = positions.copy()

    # default: ADV-based liquidation
    illiquid_mask = (
        (df.get('is_direct_property', pd.Series(False, index=df.index)) == True) |
        (df['adv_eur'] == 0) |
        (df['adv_eur'].isna())
    )

    df['days_to_liquidate'] = np.where(
        illiquid_mask,
        np.inf,
        df['market_value_eur'].abs() / (df['adv_eur'] * pct_adv)
    )

    # special cases: override ADV-based estimate
    # cash: immediate
    df.loc[df['asset_class'] == 'Cash', 'days_to_liquidate'] = 0

    # FX forwards: OTC T+2 settlement
    df.loc[df['asset_class'] == 'FX', 'days_to_liquidate'] = 2

    # listed options and listed derivatives: exchange traded, 1 day
    listed_deriv_mask = (
        (df['asset_class'] == 'Derivative') &
        (df.get('sub_asset_class', '') == 'Listed Option')
    )
    df.loc[listed_deriv_mask, 'days_to_liquidate'] = 1

    return df


def liquidity_buckets(
    positions: pd.DataFrame
) -> pd.DataFrame:
    """
    Assign ESMA liquidity buckets based on days to liquidate.

    ESMA standard buckets (ESMA34-39-897):
    - 1 day
    - 2-7 days
    - 8-30 days
    - 31-90 days
    - 91-365 days
    - > 1 year

    Parameters
    ----------
    positions : pd.DataFrame
        Positions with column: days_to_liquidate
        (run days_to_liquidate() first)

    Returns
    -------
    pd.DataFrame
        Original positions with added column: liquidity_bucket

    Examples
    --------
    >>> positions = days_to_liquidate(positions)
    >>> positions = liquidity_buckets(positions)
    >>> print(positions.groupby('liquidity_bucket')[
    ...     'market_value_eur'].sum())
    """
    df = positions.copy()

    bins   = [-np.inf, 1, 7, 30, 90, 365, np.inf]    
    labels = [
        '1 day',
        '2-7 days',
        '8-30 days',
        '31-90 days',
        '91-365 days',
        '> 1 year',
    ]

    df['liquidity_bucket'] = pd.cut(
        df['days_to_liquidate'],
        bins=bins,
        labels=labels,
        right=True
    )

    return df


def redemption_stress(
    positions: pd.DataFrame,
    nav: float,
    redemption_pct: float = 0.25,
    notice_days: int = 5
) -> dict:
    """
    Redemption stress test: can the fund meet redemptions
    by selling liquid assets within the notice period?

    liquidity_gap = liquid_assets - redemption_amount
    - positive: fund can meet redemption
    - negative: shortfall, gate or side pocket needed

    Parameters
    ----------
    positions : pd.DataFrame
        Positions with liquidity_bucket column.
        Run days_to_liquidate() and liquidity_buckets() first.
    nav : float
        Fund NAV in EUR.
    redemption_pct : float
        Redemption as fraction of NAV. Default 0.25 (25%).
    notice_days : int
        Notice period in days. Default 5.

    Returns
    -------
    dict with keys:
        redemption_amount_eur : redemption in EUR
        liquid_assets_eur     : assets liquidatable in notice period
        liquidity_gap_eur     : gap (positive = can meet)
        coverage_ratio        : liquid / redemption
        can_meet_redemption   : bool
        recommendation        : action if shortfall

    Examples
    --------
    >>> result = redemption_stress(positions, nav=250e6,
    ...     redemption_pct=0.25, notice_days=5)
    >>> print(result['recommendation'])
    """
    redemption_amount = nav * redemption_pct

    # assets liquidatable within notice period
    liquid_buckets = ['1 day', '2-7 days']
    if notice_days >= 8:
        liquid_buckets.append('8-30 days')

    liquid_assets = positions[
        positions['liquidity_bucket'].isin(liquid_buckets)
    ]['market_value_eur'].sum()

    liquidity_gap  = liquid_assets - redemption_amount
    coverage_ratio = (liquid_assets / redemption_amount
                      if redemption_amount > 0 else np.inf)

    if liquidity_gap >= 0:
        recommendation = 'Fund can meet redemption'
    elif coverage_ratio >= 0.5:
        recommendation = 'Partial gate recommended'
    else:
        recommendation = ('Full gate or side pocket required '
                          'for illiquid assets')

    return {
        'redemption_pct'      : redemption_pct,
        'redemption_amount_eur': float(redemption_amount),
        'liquid_assets_eur'   : float(liquid_assets),
        'liquidity_gap_eur'   : float(liquidity_gap),
        'coverage_ratio'      : round(float(coverage_ratio), 4),
        'can_meet_redemption' : bool(liquidity_gap >= 0),
        'recommendation'      : recommendation,
    }


def lmt_trigger_analysis(
    nav: float,
    liquid_pct: float,
    gate_threshold: float,
    swing_threshold: float,
    redemption_schedule: list,
    consecutive_gate_for_suspension: int   = 3,
    backlog_pct_for_suspension: float      = 0.25,
    swing_factor: float                    = 0.005,
    contagion_multiplier: float            = 1.0,
) -> pd.DataFrame:
    """
    MRS-84: AIFMD II LMT time-series simulation.

    Simulates 12 months of redemptions for an open-ended fund, modelling
    gate activation, swing pricing, contagion feedback, and suspension
    mechanics per the AIFMD II LMT framework (Directive 2024/927/EU,
    Article 16a; ESMA Guidelines ESMA34-671404336-1364, April 2025).

    The illiquid sleeve is treated as static (no return, no new investment).
    The liquid sleeve shrinks as redemptions are paid. No new subscriptions.

    Gate threshold semantics
    ------------------------
    The gate cap is expressed as a fraction of *total NAV*, consistent with
    how fund documents define the gate (e.g. "redemptions shall not exceed
    10% of NAV in any dealing period"). However, the fund can only pay what
    it can actually liquidate, so the effective payment ceiling is:

        gate_cap = min(gate_threshold * total_nav, liquid_nav)

    This distinction matters for illiquid funds: a 10%-of-NAV gate on a fund
    with only 15% liquid assets is contractually generous but practically
    binding from month 1 of any stress scenario.

    Contagion feedback
    ------------------
    When the gate was active in the previous month, remaining investors
    rationally accelerate their own redemption requests to avoid being locked
    in while others exit ahead of them. This is captured by scaling the
    next period's gross redemption rate:

        effective_gross_pct_t = min(schedule_t * contagion_multiplier, 1.0)
            if gate was active in period t-1, else schedule_t

    Typical calibration for institutional/sophisticated investor bases: 1.3–1.5.
    Default 1.0 disables contagion (backward-compatible).

    Suspension note
    ---------------
    Suspension is modelled as auto-triggering on two quantitative conditions.
    Under AIFMD II and ESMA Guidelines (ESMA34-671404336-1364, April 2025),
    actual suspension requires exceptional circumstances and a board decision
    — it cannot be automatic. The auto-trigger here is a simulation
    convenience for stress-testing purposes only.

    Parameters
    ----------
    nav : float
        Total fund NAV in EUR at month 0.
    liquid_pct : float
        Fraction of NAV in the liquid sleeve (0–1).
    gate_threshold : float
        Gate triggers when gross redemption demand exceeds this fraction of
        *total NAV*. Paid redemptions are capped at min(gate_threshold *
        total_nav, liquid_nav); excess is deferred into the backlog.
    swing_threshold : float
        Swing pricing activates when the gross (contagion-adjusted) redemption
        rate exceeds this fraction of total NAV. Applies a dilution levy of
        swing_factor to the effective NAV per unit, protecting remaining
        investors from transaction-cost dilution.
    redemption_schedule : list of float
        12 base gross redemption requests, each as a fraction of *that
        month's* total NAV before contagion scaling. len >= 12; only first
        12 elements are used.
    consecutive_gate_for_suspension : int
        Number of consecutive months the gate must be active before the
        suspension condition can be evaluated (AIFMD II Article 16a,
        condition 1). Default 3.
    backlog_pct_for_suspension : float
        Outstanding backlog as a fraction of liquid NAV that must also be
        breached simultaneously for suspension to trigger (condition 2).
        Default 0.25 (25%).
    swing_factor : float
        Dilution levy when swing pricing is active, expressed as a fraction
        of NAV per unit (e.g. 0.005 = 50 bps). Default 0.005.
    contagion_multiplier : float
        Scaling factor applied to the base redemption schedule in any month
        immediately following a month in which the gate was active.
        Default 1.0 (no contagion). Set to 1.3–1.5 for realistic open-ended
        fund stress scenarios.

    Returns
    -------
    pd.DataFrame with 12 rows and columns:
        month                    : period number (1–12)
        base_gross_pct           : raw schedule value before contagion (%)
        effective_gross_pct      : contagion-adjusted gross rate actually used (%)
        effective_gross_eur      : contagion-adjusted gross request in EUR
        paid_eur                 : amount paid to redeeming investors this month
        deferred_eur             : newly deferred from this month's gross request
        backlog_eur              : cumulative unpaid balance carried forward
        gate_active              : bool — gate in force this month
        swing_active             : bool — swing pricing applied this month
        suspension_active        : bool — suspension in force (simulation only)
        consecutive_gate_months  : running count of consecutive gate months
        liquid_nav_eur           : liquid sleeve at end of month
        illiquid_nav_eur         : illiquid sleeve (static)
        total_nav_eur            : liquid + illiquid at end of month

    Examples
    --------
    >>> schedule = [0.05, 0.08, 0.12, 0.15, 0.10, 0.06,
    ...             0.04, 0.03, 0.02, 0.02, 0.02, 0.01]
    >>> df = lmt_trigger_analysis(
    ...     nav=250e6, liquid_pct=0.70,
    ...     gate_threshold=0.10, swing_threshold=0.05,
    ...     redemption_schedule=schedule,
    ...     contagion_multiplier=1.5)
    >>> df[['month', 'effective_gross_pct', 'paid_eur',
    ...     'gate_active', 'suspension_active']]
    """
    liquid_nav      = nav * liquid_pct
    illiquid_nav    = nav * (1.0 - liquid_pct)
    backlog         = 0.0
    consec_gate     = 0
    prev_gate       = False   # tracks whether gate was active last month
    rows            = []

    for month in range(1, 13):
        total_nav     = liquid_nav + illiquid_nav
        base_pct      = float(redemption_schedule[month - 1])

        # contagion: scale up demand if gate fired last period
        if prev_gate and contagion_multiplier != 1.0:
            eff_pct = min(base_pct * contagion_multiplier, 1.0)
        else:
            eff_pct = base_pct

        eff_eur = eff_pct * total_nav

        # swing pricing: activates on effective gross rate
        swing_active = eff_pct > swing_threshold
        if swing_active:
            # dilution levy adjusts effective NAV per unit upward,
            # protecting remaining investors from transaction costs
            effective_nav = total_nav * (1.0 + swing_factor)  # noqa: F841
        else:
            effective_nav = total_nav                          # noqa: F841

        # gate cap: contractual limit (% of total NAV) floored by liquid sleeve
        # — the fund cannot pay more than it can liquidate regardless of the
        # contractual cap
        contractual_cap = gate_threshold * total_nav
        gate_cap_eur    = min(contractual_cap, liquid_nav)

        # total demand this month = new contagion-adjusted requests + backlog
        total_demand = eff_eur + backlog

        # suspension check (evaluated before paying redemptions)
        # Note: in practice requires a board decision (ESMA34-671404336-1364);
        # auto-trigger here is a simulation simplification only.
        suspension_active = (
            consec_gate >= consecutive_gate_for_suspension
            and (backlog / liquid_nav if liquid_nav > 0 else 0.0)
                 >= backlog_pct_for_suspension
        )

        if suspension_active:
            # no redemptions paid; all new requests accumulate in backlog
            paid_eur     = 0.0
            deferred_eur = eff_eur
            gate_active  = True   # gate condition persists during suspension
            consec_gate += 1
        else:
            if total_demand > gate_cap_eur:
                gate_active  = True
                paid_eur     = min(gate_cap_eur, total_demand)
                # deferred = portion of this month's new gross not covered by
                # remaining gate capacity after servicing old backlog
                deferred_eur = max(0.0, eff_eur - max(0.0, gate_cap_eur - backlog))
                consec_gate += 1
            else:
                gate_active  = False
                paid_eur     = total_demand
                deferred_eur = 0.0
                consec_gate  = 0

        prev_gate  = gate_active
        backlog    = max(0.0, total_demand - paid_eur)

        # liquid sleeve shrinks by the amount actually paid out
        liquid_nav = max(0.0, liquid_nav - paid_eur)

        rows.append({
            'month'                  : month,
            'base_gross_pct'         : round(base_pct * 100, 4),
            'effective_gross_pct'    : round(eff_pct * 100, 4),
            'effective_gross_eur'    : round(eff_eur, 2),
            'paid_eur'               : round(paid_eur, 2),
            'deferred_eur'           : round(deferred_eur, 2),
            'backlog_eur'            : round(backlog, 2),
            'gate_active'            : gate_active,
            'swing_active'           : swing_active,
            'suspension_active'      : suspension_active,
            'consecutive_gate_months': consec_gate,
            'liquid_nav_eur'         : round(liquid_nav, 2),
            'illiquid_nav_eur'       : round(illiquid_nav, 2),
            'total_nav_eur'          : round(liquid_nav + illiquid_nav, 2),
        })

    return pd.DataFrame(rows)


def investor_concentration(
    investor_df: pd.DataFrame,
    nav: float,
    threshold: float = 0.20
) -> dict:
    """
    Investor concentration analysis per ESMA guidelines.

    ESMA thresholds:
    - single investor > 20% of NAV: flag as concentration risk
    - top 3 investors > 50% of NAV: flag as high concentration

    Parameters
    ----------
    investor_df : pd.DataFrame
        Investor register with columns:
        investor_id, investor_name, aum_eur
    nav : float
        Fund NAV in EUR.
    threshold : float
        Single investor threshold. Default 0.20 (20%).

    Returns
    -------
    dict with keys:
        largest_investor_pct  : largest investor % of NAV
        top3_pct              : top 3 investors % of NAV
        concentration_flag    : bool
        high_concentration    : bool
        largest_redemption_eur: largest investor AUM in EUR
        by_investor           : pd.DataFrame

    Examples
    --------
    >>> investors = pd.DataFrame({
    ...     'investor_id'  : ['INV001', 'INV002'],
    ...     'investor_name': ['Pension Fund A', 'Insurance B'],
    ...     'aum_eur'      : [50e6, 30e6]
    ... })
    >>> result = investor_concentration(investors, nav=250e6)
    """
    df = investor_df.copy()
    df['pct_nav'] = df['aum_eur'] / nav

    df = df.sort_values('aum_eur', ascending=False)

    largest_pct = float(df['pct_nav'].iloc[0])
    top3_pct    = float(df['pct_nav'].head(3).sum())

    return {
        'largest_investor_pct' : round(largest_pct, 4),
        'top3_pct'             : round(top3_pct, 4),
        'concentration_flag'   : bool(largest_pct > threshold),
        'high_concentration'   : bool(top3_pct > 0.50),
        'largest_redemption_eur': float(df['aum_eur'].iloc[0]),
        'by_investor'          : df[[
            'investor_id', 'investor_name',
            'aum_eur', 'pct_nav'
        ]],
    }

def load_investor_register(fund_id: str, nav: float) -> pd.DataFrame:
    """
    Load investor register from reference_data/investor_register/<fund_id>_inv.json
    and return a DataFrame ready for investor_concentration().

    Adds aum_eur = weight * nav.

    Parameters
    ----------
    fund_id : str   e.g. 'AIFM_HedgeFund'
    nav     : float fund NAV in EUR

    Returns
    -------
    pd.DataFrame with columns: investor_id, investor_name, investor_type, weight, aum_eur
    """
    
    path = _DIR / 'reference_data' / 'investor_register' / f'{fund_id}_inv.json'
    df = pd.read_json(path)
    df['aum_eur'] = df['weight'] * nav
    return df

def load_counterparty(fund_id: str) -> pd.DataFrame:
    """
    Load counterparty from reference_data/counterparty/<fund_id>_counterparty.json
    and return a DataFrame.

    Parameters
    ----------
    fund_id : str   e.g. 'AIFM_HedgeFund'

    Returns
    -------
    pd.DataFrame with columns: ounterparty, type, exposure_pct, collateral_cover
    """

    
    path = _DIR / 'reference_data' / 'counterparty' / f'{fund_id}_counterparty.json'
    df = pd.read_json(path)
    return df


def liquidity_adjusted_var(
    var: float,
    positions: pd.DataFrame,
    stress_multiplier: float = 3.0
) -> dict:
    """
    Liquidity-adjusted VaR (LVaR).
    Add liquidity cost (positions cant be unwind immediatelly)

    LVaR = VaR + liquidity_cost
    liquidity_cost = ½ * spread * MV * stress_multiplier

    Default spreads by asset class (in decimal):
    - Large cap equity  : 5bps  * 3x  = 15bps stressed
    - IG bonds          : 10bps * 5x  = 50bps stressed
    - HY bonds          : 50bps * 10x = 500bps stressed
    - Senior loans      : 100bps* 20x = 2000bps stressed
    - Listed REITs      : 15bps * 5x  = 75bps stressed
    - Direct properties : 5-8% transaction cost

    Parameters
    ----------
    var : float
        Standard VaR as positive number.
    positions : pd.DataFrame
        Enriched positions with asset_class, market_value_eur.
    stress_multiplier : float
        Global spread stress multiplier. Default 3.0.

    Returns
    -------
    dict with keys:
        var           : standard VaR
        liquidity_cost: total liquidity cost
        lvar          : liquidity-adjusted VaR
        lvar_pct      : % increase vs standard VaR

    Examples
    --------
    >>> result = liquidity_adjusted_var(
    ...     var=0.025, positions=positions, stress_multiplier=3.0)
    >>> print(f'LVaR: {result["lvar"]:.4f}')
    """
    # normal spreads by asset class (in decimal)
    normal_spreads = {
        'Equity'     : 0.0005,   # 5bps
        'Real Estate': 0.0015,   # 15bps (REITs)
        'Bond'       : 0.0010,   # 10bps (IG default)
        'Loan'       : 0.0100,   # 100bps
        'CLO'        : 0.0050,   # 50bps
        'FX'         : 0.0002,   # 2bps
        'Derivative' : 0.0010,   # 10bps
        'Cash'       : 0.0000,   # no spread
    }

    df = positions.copy()
    df['spread'] = df['asset_class'].map(
        normal_spreads).fillna(0.001)

    # direct properties: use transaction cost instead of spread
    if 'is_direct_property' in df.columns:
        df.loc[df['is_direct_property'] == True, 'spread'] = 0.065

    df['liquidity_cost'] = (
        0.5 * df['spread'] * stress_multiplier *
        df['market_value_eur'].abs()
    )

    total_liq_cost = float(df['liquidity_cost'].sum())
    nav            = float(df['market_value_eur'].sum())
    liq_cost_pct   = total_liq_cost / abs(nav) if nav != 0 else 0

    lvar = var + liq_cost_pct

    return {
        'var'           : round(float(var), 6),
        'liquidity_cost': round(float(liq_cost_pct), 6),
        'lvar'          : round(float(lvar), 6),
        'lvar_pct_increase': round(
            float((lvar - var) / var * 100
                  if var > 0 else 0), 2),
        'by_asset_class': df.groupby('asset_class').agg(
            market_value_eur=('market_value_eur', 'sum'),
            liquidity_cost=('liquidity_cost', 'sum')
        ).reset_index(),
    }

# ---------------------------------------------------------------------------
# MRS-28 | P&L Attribution by Risk Factor — Hedge Fund / UCITS
# ---------------------------------------------------------------------------
# Regulatory context
# AIFMD Article 15 requires the risk function to monitor and measure
# the risk of each position and its contribution to the overall risk
# profile. CSSF expects the risk manager to explain return and loss
# drivers by factor. This is a risk governance output, not a direct
# Annex IV or Annex VI field. It feeds the Board risk report (MRS-37)
# and supports the AIFMD Article 15 evidence pack.
#
# Methodology: sensitivity-based attribution.
# Regression-based approaches give average historical loadings and
# cannot reflect current position changes. Sensitivity-based
# attribution uses actual positions and actual market moves each day,
# consistent with how VaR is computed, and produces explanations that
# hold up in a Board or regulator conversation.
#
# Attribution framework
# ---------------------
# Total P&L = Equity factor P&L + Rates P&L + FX P&L + Residual
#
# Equity:   P&L_eq    = sum(beta_i * r_market * MV_i)
# Rates:    P&L_rates = sum(-D_i * dy * MV_i)
# FX:       P&L_fx    = sum(notional_foreign_i * r_fx_i)
# Residual  = P&L_actual - (P&L_eq + P&L_rates + P&L_fx)
#
# A large or persistent residual signals model limitations, missing
# factors (credit spread, volatility, carry), wrong sensitivity
# estimates, or data issues. It is shown, not suppressed.
# ---------------------------------------------------------------------------

def compute_pnl_attribution(
    positions_history_df: pd.DataFrame,
    market_moves_df: pd.DataFrame,
    pnl_actual_series: pd.Series,
) -> pd.DataFrame:
    """
    Sensitivity-based daily P&L attribution.

    Parameters
    ----------
    positions_history_df : pd.DataFrame
        Daily positions with columns: date, isin, asset_class, currency,
        market_value_eur, beta, dur_adj_mid.
        One row per position per date.
    market_moves_df : pd.DataFrame
        Daily market moves with DatetimeIndex and columns:
        r_market, dy, r_fx_USD
    pnl_actual_series : pd.Series
        Daily actual P&L in EUR, DatetimeIndex.
    """
    BASE_CCY = 'EUR'
    fx_cols  = {c: c.replace('r_fx_', '').upper()
                for c in market_moves_df.columns
                if c.startswith('r_fx_')}

    rows = []
    for date, moves in market_moves_df.iterrows():
        r_market = float(moves.get('r_market', 0.0))
        dy       = float(moves.get('dy', 0.0))

        # Use positions for this specific date
        pos_today = positions_history_df[
            positions_history_df['date'] == date
        ]

        if pos_today.empty:
            continue

        pnl_equity = 0.0
        pnl_rates  = 0.0
        pnl_fx     = 0.0

        for _, pos in pos_today.iterrows():
            mv         = float(pos['market_value_eur'])
            ccy        = str(pos.get('currency', BASE_CCY)).upper()
            asset_class= str(pos.get('asset_class', '')).strip()

            if asset_class == 'Equity':
                beta = pos.get('beta')
                if pd.notna(beta) and beta != 0:
                    pnl_equity += float(beta) * mv * r_market

            if asset_class == 'Bond':
                dur = pos.get('dur_adj_mid')
                if pd.notna(dur) and dur != 0:
                    pnl_rates += -float(dur) * dy * mv

            if ccy != BASE_CCY and asset_class in ('FX', 'Bond'):
                fx_col = f'r_fx_{ccy}'
                r_fx   = float(moves.get(fx_col, 0.0))
                pnl_fx += mv * r_fx

        pnl_explained = pnl_equity + pnl_rates + pnl_fx
        pnl_actual    = float(pnl_actual_series.get(date, float('nan')))
        pnl_residual  = pnl_actual - pnl_explained

        pct_explained = (
            abs(pnl_explained) / abs(pnl_actual)
            if pd.notna(pnl_actual) and abs(pnl_actual) > 1_000
            else float('nan')
        )

        rows.append({
            'date':          date,
            'pnl_actual':    pnl_actual,
            'pnl_equity':    pnl_equity,
            'pnl_rates':     pnl_rates,
            'pnl_fx':        pnl_fx,
            'pnl_explained': pnl_explained,
            'pnl_residual':  pnl_residual,
            'pct_explained': pct_explained,
        })

    return pd.DataFrame(rows).set_index('date')


# ================================================================
# Pre-trade compliance
# ================================================================

_SIGMA_MARKET   = 0.010    # daily equity market vol (1%)
_SIGMA_RATES    = 0.005    # daily rate vol (50bps)
_Z99            = 2.3263   # norm.ppf(0.99)
_HOLDING_DAYS   = 20       # UCITS holding period (days)

_UCITS_INELIGIBLE = frozenset({
    'Loan', 'CLO', 'ABS', 'MBS', 'CMBS', 'CDO',
    'Real Estate', 'Property', 'Private Equity',
})

_HY_SUB_CLASSES = frozenset({
    'HY Corporate', 'Second Lien', 'Mezzanine', 'CLO BB', 'CLO Equity',
})
_HY_RATINGS = frozenset({
    'BB+', 'BB', 'BB-', 'B+', 'B', 'B-',
    'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D',
})


def _ptc_apply_trade(positions: pd.DataFrame, trade: dict) -> pd.DataFrame:
    """Return pro-forma positions after applying the proposed trade.

    pct_financed (0.0–1.0) in the trade dict controls how much of the notional
    is prime-broker financed vs cash-funded. 1.0 = fully leveraged (no cash
    reduction); 0.0 = fully cash-funded (cash reduced by full notional).
    Defaults to 1.0 so calls without the field behave as before.
    """
    direction = trade['direction'].lower()
    mv_delta  = float(trade['quantity']) * float(trade['price_eur'])
    if direction in ('sell', 'short'):
        mv_delta = -mv_delta

    pro_forma = positions.copy()
    mask = pro_forma['isin'] == trade['isin']

    if mask.any():
        pro_forma.loc[mask, 'market_value_eur'] += mv_delta
    else:
        new_row = {col: None for col in pro_forma.columns}
        new_row.update({
            'isin'              : trade['isin'],
            'asset_class'       : trade.get('asset_class', 'Equity'),
            'sub_asset_class'   : trade.get('sub_asset_class', ''),
            'market_value_eur'  : mv_delta,
            'beta'              : trade.get('beta', 1.0),
            'dur_adj_mid'       : trade.get('dur_adj_mid', 0.0),
            'currency'          : trade.get('currency', 'EUR'),
            'adv_eur'           : trade.get('adv_eur', 0.0),
            'is_direct_property': False,
            'sector'            : trade.get('sector', None),
        })
        pro_forma = pd.concat(
            [pro_forma, pd.DataFrame([new_row])], ignore_index=True
        )

    # pct_financed=0.0: cash-funded (cash reduced, no new borrowing)
    # pct_financed=1.0: fully PB financed (cash unchanged, borrowing created)
    pct_financed   = float(trade.get('pct_financed', 1.0))
    cash_reduction = mv_delta * (1.0 - pct_financed)
    if cash_reduction != 0.0:
        cash_mask = pro_forma['asset_class'] == 'Cash'
        if cash_mask.any():
            pro_forma.loc[cash_mask, 'market_value_eur'] -= cash_reduction

    # Leveraged portion creates a PB borrowing (EU 231/2013 Recital 13: included in
    # both gross and commitment at absolute value). Modelled as a 'Borrowing' row
    # with negative market_value_eur so compute_leverage can pick it up.
    borrowing_notional = mv_delta * pct_financed
    if borrowing_notional > 0.0:
        borrow_mask = pro_forma['asset_class'] == 'Borrowing'
        if borrow_mask.any():
            pro_forma.loc[borrow_mask, 'market_value_eur'] -= borrowing_notional
        else:
            borrow_row = {col: None for col in pro_forma.columns}
            borrow_row.update({
                'asset_class'       : 'Borrowing',
                'sub_asset_class'   : 'PB Financing',
                'instrument_name'   : 'Prime Broker Financing',
                'market_value_eur'  : -borrowing_notional,
                'adv_eur'           : 0.0,
                'is_direct_property': False,
                'is_hedge'          : False,
            })
            pro_forma = pd.concat(
                [pro_forma, pd.DataFrame([borrow_row])], ignore_index=True
            )

    return pro_forma


def _ptc_portfolio_var(pro_forma: pd.DataFrame, nav: float) -> float:
    """
    20-day 99% parametric VaR as decimal fraction of NAV.
    Equity: beta-weighted. Rates: duration-weighted. Components independent.
    """
    if nav == 0:
        return 0.0
    eq = pro_forma[pro_forma['asset_class'] == 'Equity']
    bd = pro_forma[pro_forma['asset_class'] == 'Bond']
    port_beta = (eq['beta'].fillna(0) * eq['market_value_eur']).sum() / nav
    port_dur  = (bd['dur_adj_mid'].fillna(0) * bd['market_value_eur']).sum() / nav
    sigma = np.sqrt(
        (port_beta * _SIGMA_MARKET) ** 2 +
        (port_dur  * _SIGMA_RATES)  ** 2
    )
    return float(sigma * np.sqrt(_HOLDING_DAYS) * _Z99)


def _ptc_reference_var() -> float:
    """20-day 99% VaR for 60/40 reference portfolio (beta=1, 5yr duration)."""
    sigma = np.sqrt(
        (0.60 * _SIGMA_MARKET)       ** 2 +
        (0.40 * 5.0 * _SIGMA_RATES)  ** 2
    )
    return float(sigma * np.sqrt(_HOLDING_DAYS) * _Z99)


def _ptc_issuer_exposure(pro_forma: pd.DataFrame, nav: float) -> pd.Series:
    """Issuer exposure as % of NAV. Uses 'issuer' column if present, else 'isin'."""
    key = 'issuer' if 'issuer' in pro_forma.columns else 'isin'
    return (
        pro_forma
        .groupby(pro_forma[key].fillna(pro_forma['isin']))['market_value_eur']
        .sum() / nav * 100
    )


def _breach(check: str, limit: float, actual: float,
            unit: str, message: str) -> dict:
    return {
        'check'  : check,
        'limit'  : limit,
        'actual' : round(actual, 4),
        'unit'   : unit,
        'message': message,
    }


def _check_ucits(
    pro_forma: pd.DataFrame, nav: float, trade: dict
) -> tuple:
    breaches: list = []
    metrics:  dict = {}

    # [1] Absolute VaR < 20% NAV (UCITS 20-day, 99%)
    abs_var = _ptc_portfolio_var(pro_forma, nav)
    metrics['absolute_var_pct'] = abs_var
    if abs_var > 0.20:
        breaches.append(_breach(
            'absolute_var_limit', 0.20, abs_var, '% NAV (decimal)',
            f'Post-trade absolute VaR {abs_var:.2%} exceeds UCITS limit 20.00% NAV '
            f'(UCITS SRRI, 20-day, 99%)'
        ))

    # [2] Relative VaR < 2x reference portfolio
    ref_var  = _ptc_reference_var()
    rel_mult = abs_var / ref_var if ref_var > 0 else 0.0
    metrics['relative_var_multiplier'] = rel_mult
    metrics['reference_var_pct']       = ref_var
    if rel_mult > 2.0:
        breaches.append(_breach(
            'relative_var_limit', 2.0, rel_mult, 'x reference',
            f'Post-trade VaR is {rel_mult:.2f}x reference portfolio '
            f'(60/40 benchmark), limit 2.0x'
        ))

    # [3] 5/10/40 rule (UCITSD Article 52)
    # Scope: excludes government securities and ETFs/funds (apply look-through for ETFs).
    # Government bonds: sovereign risk monitored separately.
    # ETFs/funds: are vehicles, not issuers; constituent look-through applies.
    if 'sector' in pro_forma.columns:
        conc_universe = pro_forma[
            ((pro_forma['sector'].isna()) | (pro_forma['sector'] != 'Government')) &
            (~pro_forma.get('sub_asset_class', '').isin(['ETF', 'Fund']))
        ]
    else:
        conc_universe = pro_forma[
            ~pro_forma.get('sub_asset_class', '').isin(['ETF', 'Fund'])
        ]

    issuer_exp = _ptc_issuer_exposure(conc_universe, nav)
    above_10   = issuer_exp[issuer_exp > 10.0]
    above_5    = issuer_exp[issuer_exp >  5.0]
    sum_above_5 = float(above_5.sum())
    metrics['max_issuer_pct']      = float(issuer_exp.max()) if len(issuer_exp) else 0.0
    metrics['sum_above_5pct_issuers'] = sum_above_5
    for issuer, pct in above_10.items():
        breaches.append(_breach(
            '5_10_40_single_issuer_hard', 10.0, float(pct), '% NAV',
            f'Issuer {issuer}: {pct:.1f}% NAV — exceeds 10% hard limit (5/10/40 rule)'
        ))
    if sum_above_5 > 40.0:
        breaches.append(_breach(
            '5_10_40_bucket_limit', 40.0, sum_above_5, '% NAV',
            f'Positions >5% NAV aggregate to {sum_above_5:.1f}% — exceeds 40% bucket limit'
        ))

    # [4] Eligible assets (UCITSD Article 50)
    asset_class = trade.get('asset_class', '')
    metrics['trade_eligible'] = asset_class not in _UCITS_INELIGIBLE
    if asset_class in _UCITS_INELIGIBLE:
        breaches.append(_breach(
            'eligible_assets_article_50', 1.0, 0.0, 'flag',
            f'{asset_class} ({trade.get("sub_asset_class","")}) is ineligible '
            f'under UCITSD Article 50 — fund cannot hold this instrument'
        ))

    # [5] Counterparty exposure (OTC derivatives)
    cpty       = trade.get('counterparty')
    cpty_type  = trade.get('counterparty_type', 'non_credit_institution')
    cpty_limit = 0.10 if cpty_type == 'credit_institution' else 0.05
    if cpty and trade.get('asset_class') == 'Derivative':
        trade_mv_pct = abs(trade['quantity'] * trade['price_eur']) / nav if nav else 0.0
        metrics[f'counterparty_{cpty}_pct'] = trade_mv_pct
        if trade_mv_pct > cpty_limit:
            breaches.append(_breach(
                'counterparty_exposure', cpty_limit * 100,
                trade_mv_pct * 100, '% NAV',
                f'OTC counterparty {cpty} ({cpty_type}): {trade_mv_pct:.1%} NAV — '
                f'exceeds {cpty_limit:.0%} limit'
            ))

    # [6] Borrowing limit < 10% NAV (UCITSD Article 83 — temporary borrowing only)
    # Proxy: negative cash balances. Real borrowing tracked via prime broker/custodian.
    cash_borrow = pro_forma.loc[
        (pro_forma['asset_class'] == 'Cash') &
        (pro_forma['market_value_eur'] < 0),
        'market_value_eur'
    ].sum()
    borrow_pct = abs(cash_borrow) / nav if nav else 0.0
    metrics['borrowing_pct'] = borrow_pct
    if borrow_pct > 0.10:
        breaches.append(_breach(
            'borrowing_limit', 10.0, borrow_pct * 100, '% NAV',
            f'Temporary borrowing {borrow_pct:.1%} NAV exceeds UCITSD Article 83 limit 10%'
        ))

    return breaches, metrics


def compute_leverage(
    positions_df: pd.DataFrame,
    nav: float,
    bbg=None,
    deriv_bbg_map: dict | None = None,
    currency_bbg_map: dict | None = None,
    external_borrowings_eur: float = 0.0,
) -> dict:
    """
    Compute gross and commitment leverage per EU 231/2013 Articles 7-8.

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

    # ── gross (Article 7) ─────────────────────────────────────────────────
    # Cash (uninvested) excluded; Borrowing handled separately below.
    gross_exposure = df.apply(
        lambda r: deriv_gross_map.get(r.name, 0.0) if r['asset_class'] == 'Derivative'
        else (0.0 if r['asset_class'] in ('Cash', 'Borrowing') else r['abs_exposure']),
        axis=1,
    ).sum()

    # Borrowings — EU 231/2013 Recital 13: all borrowings included at absolute value.
    # Exception (Recital 14): capital call credit facilities that are temporary and fully
    # covered by investor commitments are excluded (PE/infra only, not applicable to HF).
    borrowings = df.loc[df['asset_class'] == 'Borrowing', 'market_value_eur'].abs().sum()
    borrowings += abs(external_borrowings_eur)

    gross_exposure += borrowings
    gross_leverage  = gross_exposure / nav if nav else 0.0

    # ── commitment (Article 8) ────────────────────────────────────────────
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


def _check_aifm_hf(
    pro_forma: pd.DataFrame,
    nav: float,
    trade: dict,
    counterparties_df=None,
    bbg=None,
    deriv_bbg_map: dict | None = None,
    currency_bbg_map: dict | None = None,
    positions_before: pd.DataFrame | None = None,
) -> tuple:
    breaches: list = []
    metrics:  dict = {}

    # [1] & [2] Gross and commitment leverage — EU 231/2013 Articles 7-8
    lev = compute_leverage(pro_forma, nav, bbg=bbg,
                           deriv_bbg_map=deriv_bbg_map,
                           currency_bbg_map=currency_bbg_map)
    metrics.update({
        'gross_leverage'            : lev['gross_leverage'],
        'commitment_leverage'       : lev['commitment_leverage'],
        'gross_exposure'            : lev['gross_exposure'],
        'commitment_exposure'       : lev['commitment_exposure'],
        'net_eq'                    : lev['net_eq'],
        'bonds'                     : lev['bonds'],
        'fx_exposure'               : lev['fx_exposure'],
        'deriv_notional_commitment' : lev['deriv_notional_commitment'],
        'borrowings'                : lev['borrowings'],
    })
    if lev['gross_leverage'] > 3.00:
        breaches.append(_breach(
            'gross_leverage', 3.00, lev['gross_leverage'], 'x NAV',
            f"Post-trade gross leverage {lev['gross_leverage']:.2f}x exceeds 300% NAV RMP limit"
        ))
    if lev['commitment_leverage'] > 2.00:
        breaches.append(_breach(
            'commitment_leverage', 2.00, lev['commitment_leverage'], 'x NAV',
            f"Post-trade commitment leverage {lev['commitment_leverage']:.2f}x exceeds 200% NAV RMP limit"
        ))

    # [3] Single-issuer concentration — 25% NAV RMP limit
    # Only flag if the trade worsened the breach (pre-existing breaches are not the trade's fault).
    issuer_exp = _ptc_issuer_exposure(pro_forma, nav)
    pre_issuer_exp = _ptc_issuer_exposure(positions_before, nav) if positions_before is not None else pd.Series(dtype=float)
    metrics['max_issuer_pct'] = float(issuer_exp.max()) if len(issuer_exp) else 0.0
    for issuer, pct in issuer_exp[issuer_exp > 25.0].items():
        pre_pct = float(pre_issuer_exp.get(issuer, 0.0))
        if pct > pre_pct:
            breaches.append(_breach(
                'issuer_concentration', 25.0, float(pct), '% NAV',
                f'Issuer {issuer}: {pct:.1f}% NAV exceeds RMP single-issuer limit 25% (was {pre_pct:.1f}%)'
            ))

    # [4] Sector concentration — 30% NAV internal RMP limit
    # Scope: equities and corporate bonds/loans/CLOs by GICS sector.
    # Government bonds are excluded (sovereign risk monitored separately via country exposure).
    # FX, derivatives, and cash are excluded as cross-sectoral instruments.
    if 'sector' in pro_forma.columns:
        sector_universe = pro_forma[
            pro_forma['asset_class'].isin(['Equity', 'Bond', 'Loan', 'CLO']) &
            pro_forma['sector'].notna() &
            (pro_forma['sector'] != 'Government')
        ]
    else:
        sector_universe = pro_forma[pro_forma['asset_class'] == 'Equity']

    sector_exp = (
        sector_universe.groupby('sector')['market_value_eur'].sum().abs() / nav * 100
    ) if len(sector_universe) else pd.Series(dtype=float)

    metrics['max_sector_pct'] = float(sector_exp.max()) if len(sector_exp) else 0.0
    for sector, pct in sector_exp[sector_exp > 30.0].items():
        breaches.append(_breach(
            'sector_concentration', 30.0, float(pct), '% NAV',
            f'Sector {sector}: {pct:.1f}% NAV exceeds internal RMP limit 30%'
        ))

    # [5] Counterparty concentration
    # Checks existing register exposure + new trade exposure against limit.
    # Limit: 10% NAV for credit institutions, 5% for others (EU 231/2013 Article 43).
    cpty       = trade.get('counterparty')
    cpty_type  = trade.get('counterparty_type', 'non_credit_institution')
    cpty_limit = 0.10 if cpty_type == 'credit_institution' else 0.05
    if cpty and trade.get('asset_class') == 'Derivative':
        trade_pct    = abs(trade['quantity'] * trade['price_eur']) / nav if nav else 0.0
        existing_pct = 0.0
        if counterparties_df is not None:
            mask = counterparties_df['counterparty'] == cpty
            if mask.any():
                existing_pct = float(counterparties_df.loc[mask, 'exposure_pct'].iloc[0])
        total_pct = existing_pct + trade_pct
        metrics[f'counterparty_{cpty}_existing_pct'] = existing_pct
        metrics[f'counterparty_{cpty}_trade_pct']    = trade_pct
        metrics[f'counterparty_{cpty}_total_pct']    = total_pct
        if total_pct > cpty_limit:
            breaches.append(_breach(
                'counterparty_exposure', cpty_limit * 100, total_pct * 100, '% NAV',
                f'Counterparty {cpty} ({cpty_type}): existing {existing_pct:.1%} '
                f'+ trade {trade_pct:.1%} = {total_pct:.1%} NAV — '
                f'exceeds {cpty_limit:.0%} limit'
            ))

    # [6] Short selling — EU 236/2012: net short > 0.2% NAV is reportable
    # Only flag positions that are new or increased by this trade.
    # Pre-existing reportable shorts are already known and managed separately.
    key       = 'issuer' if 'issuer' in pro_forma.columns else 'isin'
    net_pos   = pro_forma.groupby(pro_forma[key].fillna(pro_forma['isin']))['market_value_eur'].sum()
    net_short = net_pos[net_pos < 0]
    metrics['max_net_short_pct'] = float(
        net_short.min() / nav * 100
    ) if (len(net_short) and nav) else 0.0

    if positions_before is not None:
        pre_net = positions_before.groupby(
            positions_before[key].fillna(positions_before['isin'])
        )['market_value_eur'].sum()
    else:
        pre_net = pd.Series(dtype=float)

    for issuer, mv in net_short.items():
        short_pct  = abs(mv) / nav * 100 if nav else 0.0
        pre_mv     = float(pre_net.get(issuer, 0.0))
        trade_made_worse = mv < pre_mv  # more negative than before
        if short_pct > 0.2 and trade_made_worse:
            breaches.append(_breach(
                'short_selling_eu_236', 0.2, short_pct, '% NAV',
                f'Net short {issuer}: {short_pct:.2f}% NAV — reportable under EU 236/2012'
            ))

    # [7] Liquidity impact — weighted avg days-to-liquidate vs 30-day redemption horizon
    REDEMPTION_HORIZON = 30
    if 'adv_eur' in pro_forma.columns:
        liq_df     = days_to_liquidate(pro_forma.assign(adv_eur=pro_forma['adv_eur'].fillna(0)))
        finite_liq = liq_df[np.isfinite(liq_df['days_to_liquidate'])]
        total_abs  = finite_liq['market_value_eur'].abs().sum()
        wtd_days   = (
            (finite_liq['days_to_liquidate'] * finite_liq['market_value_eur'].abs()).sum()
            / total_abs if total_abs > 0 else 0.0
        )
        metrics['wtd_avg_days_to_liquidate'] = round(wtd_days, 1)
        if wtd_days > REDEMPTION_HORIZON:
            breaches.append(_breach(
                'liquidity_impact', float(REDEMPTION_HORIZON), wtd_days, 'days',
                f'Post-trade weighted avg days-to-liquidate {wtd_days:.1f} exceeds '
                f'{REDEMPTION_HORIZON}-day redemption horizon'
            ))

    return breaches, metrics


def _check_aifm_pd(
    pro_forma: pd.DataFrame, nav: float, trade: dict
) -> tuple:
    breaches: list = []
    metrics:  dict = {}

    # [1] Single borrower concentration < 20% NAV
    issuer_exp = _ptc_issuer_exposure(pro_forma, nav)
    metrics['max_borrower_pct'] = float(issuer_exp.max()) if len(issuer_exp) else 0.0
    for issuer, pct in issuer_exp[issuer_exp > 20.0].items():
        breaches.append(_breach(
            'single_borrower_concentration', 20.0, float(pct), '% NAV',
            f'Borrower {issuer}: {pct:.1f}% NAV exceeds 20% single-borrower limit'
        ))

    # [2] HY exposure < 50% NAV
    sub_cls = (
        pro_forma['sub_asset_class']
        if 'sub_asset_class' in pro_forma.columns
        else pd.Series('', index=pro_forma.index)
    )
    rating = (
        pro_forma['rating']
        if 'rating' in pro_forma.columns
        else pd.Series('', index=pro_forma.index)
    )
    hy_mask   = sub_cls.isin(_HY_SUB_CLASSES) | rating.fillna('').isin(_HY_RATINGS)
    hy_exp_pct = pro_forma.loc[hy_mask, 'market_value_eur'].sum() / nav * 100 if nav else 0.0
    metrics['hy_exposure_pct'] = hy_exp_pct
    if hy_exp_pct > 50.0:
        breaches.append(_breach(
            'hy_exposure_limit', 50.0, hy_exp_pct, '% NAV',
            f'HY exposure {hy_exp_pct:.1f}% NAV exceeds 50% limit'
        ))

    # [3] Unrated exposure < 10% NAV
    unrated_mask = (sub_cls == 'Unrated') | rating.fillna('NR').isin({'NR', ''})
    unrated_pct  = pro_forma.loc[unrated_mask, 'market_value_eur'].sum() / nav * 100 if nav else 0.0
    metrics['unrated_exposure_pct'] = unrated_pct
    if unrated_pct > 10.0:
        breaches.append(_breach(
            'unrated_exposure_limit', 10.0, unrated_pct, '% NAV',
            f'Unrated exposure {unrated_pct:.1f}% NAV exceeds 10% limit'
        ))

    return breaches, metrics


def pre_trade_check(
    proposed_trade: dict,
    engine,
    fund_id: str,
    date: str,
    counterparties_df=None,
    bbg=None,
    deriv_bbg_map: dict | None = None,
    currency_bbg_map: dict | None = None,
) -> dict:
    """
    Pre-trade compliance check for UCITS and AIFM funds.

    Loads the current enriched portfolio, applies the proposed trade
    to produce a pro-forma positions DataFrame, then runs fund-type-specific
    compliance checks. Returns a pass/fail result with breach detail and
    all post-trade metrics.

    Parameters
    ----------
    engine : sa.Engine
    fund_id : str
        One of: 'UCITS_Balanced', 'AIFM_HedgeFund', 'AIFM_PrivateDebt'.
    proposed_trade : dict
        Required keys: isin, direction ('buy'|'sell'|'short'),
                       quantity, price_eur, asset_class, sub_asset_class.
        Optional keys: rating, beta, dur_adj_mid, currency, issuer,
                       counterparty, counterparty_type, adv_eur.
    date : str
        Valuation date for loading current positions.

    Returns
    -------
    dict with keys:
        passed             bool
        fund_id            str
        fund_type          str   — 'ucits' | 'aifm_hf' | 'aifm_pd'
        proposed_trade     dict
        breaches           list[dict]  — empty if passed
        post_trade_metrics dict        — all computed values

    Regulatory context
    ------------------
    UCITS checks: UCITSD Articles 50, 52, 83; CSSF SRRI framework.
    AIFM HF:      AIFMD Article 15, EU 231/2013 Articles 6-8.
    AIFM PD:      AIFMD Article 15, internal RMP concentration limits.
    Short selling: EU Regulation 236/2012.
    """
    from src.enrichment import get_risk_ready_df

    _FUND_TYPE = {
        'UCITS_Balanced'   : 'ucits',
        'AIFM_HedgeFund'   : 'aifm_hf',
        'AIFM_PrivateDebt' : 'aifm_pd',
    }
    fund_type = _FUND_TYPE.get(fund_id)
    if fund_type is None:
        raise ValueError(
            f"pre_trade_check: '{fund_id}' not supported. "
            f"Supported fund_ids: {list(_FUND_TYPE)}"
        )

    positions = get_risk_ready_df(engine, fund_id, date)
    nav       = float(positions['market_value_eur'].sum())
    pro_forma = _ptc_apply_trade(positions, proposed_trade)

    if fund_type == 'ucits':
        breaches, metrics = _check_ucits(pro_forma, nav, proposed_trade)
        # Pre-trade baseline metrics for UCITS (excluding government bonds and ETFs, per Article 52).
        if 'sector' in positions.columns:
            pre_conc_universe = positions[
                ((positions['sector'].isna()) | (positions['sector'] != 'Government')) &
                (~positions.get('sub_asset_class', '').isin(['ETF', 'Fund']))
            ]
        else:
            pre_conc_universe = positions[
                ~positions.get('sub_asset_class', '').isin(['ETF', 'Fund'])
            ]
        _pre_iss = _ptc_issuer_exposure(pre_conc_universe, nav)
        _pre_above_5 = _ptc_issuer_exposure(pre_conc_universe, nav)
        _pre_above_5 = _pre_above_5[_pre_above_5 > 5.0]
        pre_metrics = {
            'absolute_var_pct'        : _ptc_portfolio_var(positions, nav),
            'relative_var_multiplier' : _ptc_portfolio_var(positions, nav) / _ptc_reference_var() if _ptc_reference_var() > 0 else 0.0,
            'reference_var_pct'       : _ptc_reference_var(),
            'max_issuer_pct'          : float(_pre_iss.max()) if len(_pre_iss) else 0.0,
            'sum_above_5pct_issuers'  : float(_pre_above_5.sum()),
        }
    elif fund_type == 'aifm_hf':
        breaches, metrics = _check_aifm_hf(
            pro_forma, nav, proposed_trade,
            counterparties_df=counterparties_df,
            bbg=bbg,
            deriv_bbg_map=deriv_bbg_map,
            currency_bbg_map=currency_bbg_map,
            positions_before=positions,
        )
        # Pre-trade baseline metrics for side-by-side comparison in reports.
        _pre_lev = compute_leverage(positions, nav, bbg=bbg,
                                    deriv_bbg_map=deriv_bbg_map,
                                    currency_bbg_map=currency_bbg_map)
        _pre_iss = _ptc_issuer_exposure(positions, nav)
        pre_metrics = {
            'gross_leverage'            : _pre_lev['gross_leverage'],
            'commitment_leverage'       : _pre_lev['commitment_leverage'],
            'gross_exposure'            : _pre_lev['gross_exposure'],
            'commitment_exposure'       : _pre_lev['commitment_exposure'],
            'net_eq'                    : _pre_lev['net_eq'],
            'bonds'                     : _pre_lev['bonds'],
            'fx_exposure'               : _pre_lev['fx_exposure'],
            'deriv_notional_commitment' : _pre_lev['deriv_notional_commitment'],
            'borrowings'                : _pre_lev['borrowings'],
            'max_issuer_pct'            : float(_pre_iss.max()) if len(_pre_iss) else 0.0,
            'absolute_var_pct'          : _ptc_portfolio_var(positions, nav),
        }
    else:
        breaches, metrics = _check_aifm_pd(pro_forma, nav, proposed_trade)
        pre_metrics = {}

    return {
        'passed'            : len(breaches) == 0,
        'fund_id'           : fund_id,
        'fund_type'         : fund_type,
        'proposed_trade'    : proposed_trade,
        'breaches'          : breaches,
        'pre_trade_metrics' : pre_metrics,
        'post_trade_metrics': metrics,
    }


# ================================================================
# Public API
# ================================================================

__all__ = [
    'HISTORICAL_SCENARIOS',
    # VaR
    'var_historical',
    'var_parametric',
    'var_scale',
    # ES
    'es_historical',
    'es_parametric',
    'es_scale',
    # backtesting
    'kupiec_test',
    'christoffersen_test',
    'exception_report',
    'full_backtest_report',
    # stress scenarios
    'stress_equity',
    'stress_rates',
    'stress_credit',
    'stress_fx',
    'stress_combined',
    'stress_historical',
    'stress_property',
    'stress_rental',
    'stress_ltv',
    # liquidity
    'days_to_liquidate',
    'liquidity_buckets',
    'redemption_stress',
    'compute_leverage',
    'investor_concentration',
    'load_investor_register',
    'load_counterparty',
    'liquidity_adjusted_var',
    # attribution
    'compute_pnl_attribution',
    # pre-trade compliance
    'pre_trade_check',
]