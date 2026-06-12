"""
var.py
======
General Value-at-Risk utilities and helpers.

Functions
---------
    var_scale: Scale 1-day VaR to multi-day horizon
    es_from_var: Approximate ES from VaR (rough heuristic)

TODO (Phase 2)
--------------
DUPLICATE LOGIC: var_scale() exists in both var.py and risk_utils.py.
Consolidate to single location (TBD) and import in the other.
Notebooks currently import from risk_utils.var_scale(), not from var.var_scale().
"""

import numpy as np


def var_scale(var_1d: float, horizon: int = 20, method: str = 'sqrt') -> float:
    """
    Scale 1-day VaR to multi-day horizon.

    Assumes returns are i.i.d. (independent and identically distributed).
    Uses square-root-of-time scaling: VaR_T = VaR_1 × √T

    Parameters
    ----------
    var_1d : float
        1-day VaR (decimal, e.g., 0.02 for 2%)
    horizon : int, default 20
        Holding period in days
    method : str, default 'sqrt'
        Scaling method ('sqrt' only, for now)

    Returns
    -------
    float
        Multi-day VaR
    """
    if method == 'sqrt':
        return var_1d * np.sqrt(horizon)
    else:
        raise ValueError(f"Unknown scaling method: {method}")


def es_from_var(var_estimate: float, confidence: float = 0.99) -> float:
    """
    Rough approximation of Expected Shortfall from VaR.

    For normal distribution: ES ≈ VaR × (1 + φ(q) / (1 - confidence))
    where φ is the standard normal PDF and q is the quantile.

    This is a heuristic; for accurate ES, use historical quantile directly.

    Parameters
    ----------
    var_estimate : float
        VaR estimate (decimal)
    confidence : float, default 0.99
        Confidence level (0-1)

    Returns
    -------
    float
        Approximate ES
    """
    alpha = 1 - confidence
    if alpha <= 0 or alpha >= 1:
        raise ValueError("confidence must be in (0, 1)")

    # Normal approximation
    from scipy import stats
    q = stats.norm.ppf(alpha)
    phi_q = stats.norm.pdf(q)
    es_adjustment = phi_q / alpha
    return var_estimate * (1 + es_adjustment)
