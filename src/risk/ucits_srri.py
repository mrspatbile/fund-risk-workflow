"""
ucits_srri.py
============
UCITS Summary Risk Indicator (SRI) computation per CESR/10-673.

The SRRI is computed from 5 years of weekly NAV returns and mapped to a 1-7
category per the CESR/10-673 guidelines. The category is displayed on the KIID
and used for PRIIPs disclosure.

Key principles:
- 260 weekly observations (5 years)
- Annualised volatility computed as: sigma_weekly * sqrt(52)
- 7 volatility buckets (1-7) with fixed boundaries
- KID update triggered if SRI changes for 4 consecutive months
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


# CESR/10-673 SRI bucket boundaries (annualised volatility %)
SRRI_BOUNDARIES = {
    1: (0.0, 0.5),
    2: (0.5, 2.0),
    3: (2.0, 5.0),
    4: (5.0, 10.0),
    5: (10.0, 15.0),
    6: (15.0, 25.0),
    7: (25.0, np.inf),
}


def compute_srri_from_returns(
    returns: pd.Series,
    annualisation_factor: int = 52,
) -> dict:
    """
    Compute SRRI category and volatility metrics from return series.

    Parameters
    ----------
    returns : pd.Series
        Weekly returns (decimal, e.g., 0.01 for 1%)
    annualisation_factor : int, default 52
        Number of periods per year (52 for weekly, 252 for daily)

    Returns
    -------
    dict
        {
            'sri_bucket': int (1-7),
            'volatility_weekly_pct': float,
            'volatility_annual_pct': float,
            'observation_count': int,
            'time_window_years': float,
        }
    """
    if returns.empty:
        raise ValueError("Returns series cannot be empty")

    volatility_weekly = returns.std()
    volatility_annual = volatility_weekly * np.sqrt(annualisation_factor)
    sri_bucket = map_volatility_to_srri_bucket(volatility_annual * 100)

    time_window_years = len(returns) / annualisation_factor

    return {
        'sri_bucket': sri_bucket,
        'volatility_weekly_pct': volatility_weekly * 100,
        'volatility_annual_pct': volatility_annual * 100,
        'observation_count': len(returns),
        'time_window_years': time_window_years,
    }


def map_volatility_to_srri_bucket(annualised_volatility_pct: float) -> int:
    """
    Map annualised volatility to SRRI category per CESR/10-673.

    SRRI boundaries:
        1: < 0.5%
        2: 0.5% - 2%
        3: 2% - 5%
        4: 5% - 10%
        5: 10% - 15%
        6: 15% - 25%
        7: >= 25%

    Parameters
    ----------
    annualised_volatility_pct : float
        Annualised volatility as percentage (e.g., 12.5 for 12.5%)

    Returns
    -------
    int
        SRRI category 1-7
    """
    for bucket, (lower, upper) in SRRI_BOUNDARIES.items():
        if lower <= annualised_volatility_pct < upper:
            return bucket

    # Fallback (should not reach here if boundaries are complete)
    return 7


def compute_srri_from_nav_history(
    nav_series: pd.Series,
    window_weeks: int = 260,
) -> dict:
    """
    Compute SRRI from NAV history using a rolling 5-year window.

    Parameters
    ----------
    nav_series : pd.Series
        Daily or weekly NAV values, indexed by date
    window_weeks : int, default 260
        Window size in weeks (standard is 260 for 5 years)

    Returns
    -------
    dict
        {
            'sri_bucket': int,
            'volatility_annual_pct': float,
            'window_weeks': int,
            'data_points': int,
            'status': str,  # 'OK' if sufficient data, 'INSUFFICIENT_DATA' otherwise
        }

    Raises
    ------
    ValueError
        If nav_series is empty or all NaN
    """
    if nav_series.empty or nav_series.isna().all():
        raise ValueError("NAV series cannot be empty or all NaN")

    # Ensure index is datetime
    if not isinstance(nav_series.index, pd.DatetimeIndex):
        nav_series.index = pd.to_datetime(nav_series.index)

    # Resample to weekly (last value of each week)
    nav_weekly = nav_series.resample('W').last()

    # Get trailing window
    if len(nav_weekly) < window_weeks:
        status = 'INSUFFICIENT_DATA'
        actual_window = len(nav_weekly)
    else:
        status = 'OK'
        actual_window = window_weeks
        nav_weekly = nav_weekly.iloc[-actual_window:]

    # Compute returns
    returns_weekly = nav_weekly.pct_change().dropna()

    # Compute SRRI
    result = compute_srri_from_returns(returns_weekly, annualisation_factor=52)
    result['window_weeks'] = actual_window
    result['status'] = status

    return result


def check_srri_change_trigger(
    current_bucket: int,
    bucket_history: pd.Series,
    persistence_months: int = 4,
) -> Tuple[bool, dict]:
    """
    Check if SRRI has changed for persistence_months consecutive months.

    Per CESR/10-673, a KID update is triggered if the SRI changes category for
    4 consecutive months.

    Parameters
    ----------
    current_bucket : int
        Current SRRI bucket (1-7)
    bucket_history : pd.Series
        Historical SRRI buckets, indexed by month-end dates
    persistence_months : int, default 4
        Number of consecutive months required to trigger update

    Returns
    -------
    tuple
        (trigger: bool, details: dict)
        Details includes: months_at_current, consecutive_months_different, status

    Raises
    ------
    ValueError
        If bucket_history is empty
    """
    if bucket_history.empty:
        raise ValueError("bucket_history cannot be empty")

    # Count consecutive months at current level vs initial level
    initial_bucket = bucket_history.iloc[0]
    consecutive_at_current = 0

    for bucket in bucket_history.iloc[-persistence_months:]:
        if bucket == current_bucket:
            consecutive_at_current += 1
        else:
            break

    # Check if we have persistence_months of the new bucket
    # (meaning the bucket CHANGED and stayed changed for persistence_months)
    changed = current_bucket != initial_bucket
    trigger = changed and consecutive_at_current >= persistence_months

    return trigger, {
        'initial_bucket': initial_bucket,
        'current_bucket': current_bucket,
        'changed': changed,
        'consecutive_months_at_current': consecutive_at_current,
        'persistence_threshold_months': persistence_months,
        'trigger': trigger,
    }


def srri_as_string(bucket: int) -> str:
    """Convert SRRI bucket number to descriptive string."""
    descriptions = {
        1: 'Very Low Risk',
        2: 'Low Risk',
        3: 'Low to Medium Risk',
        4: 'Medium Risk',
        5: 'Medium to High Risk',
        6: 'High Risk',
        7: 'Very High Risk',
    }
    return descriptions.get(bucket, f'Category {bucket}')
