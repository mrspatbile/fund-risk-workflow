"""Liquidity calibration and redemption scenario computation.

Handles:
- Redemption schedule generation from investor base assumptions
- Redemption scenario calibration (Base, Large, Stress)
- Largest investor scenario extraction
- LMT trigger analysis coordination
"""

import numpy as np
import pandas as pd


def build_redemption_schedule(
    calibration_config: dict,
    n_months: int = 12,
) -> list:
    """Generate monthly redemption schedule from investor base parameters.

    For normal months: AUM-weighted lognormal draw per investor type,
    where E[draw] = base_redemption_rate by lognormal parametrisation.
    For stress months: AUM-weighted stress rates (deterministic override).

    Parameters
    ----------
    calibration_config : dict
        Dict with keys:
        - 'investors': list of dicts with 'weight', 'base_redemption_rate', 'stress_redemption_rate'
        - 'stress_months': set or list of month numbers (1-indexed) to use stress rates
        - 'sigma': dispersion parameter for lognormal draws
        - 'seed': random seed for reproducibility

    n_months : int, default 12
        Number of periods to simulate.

    Returns
    -------
    list
        Monthly redemption rates as fractions of NAV (n_months floats).
    """
    rng = np.random.default_rng(calibration_config['seed'])
    sigma = calibration_config['sigma']
    stress_months = set(calibration_config['stress_months'])
    investors = calibration_config['investors']

    schedule = []
    for m in range(1, n_months + 1):
        rate = 0.0
        for inv in investors:
            w = inv['weight']
            if m in stress_months:
                rate += w * inv['stress_redemption_rate']
            else:
                # Lognormal with mean = base_redemption_rate
                # Parametrised: mu = log(base_rate) - sigma^2/2
                base_rate = inv['base_redemption_rate']
                mu = np.log(base_rate) - 0.5 * sigma ** 2
                rate += w * float(rng.lognormal(mean=mu, sigma=sigma))
        schedule.append(float(np.clip(rate, 0.0, 1.0)))

    return schedule


def compute_weighted_reference_rates(calibration_config: dict) -> tuple:
    """Compute expected aggregate redemption rates under normal and stress conditions.

    Parameters
    ----------
    calibration_config : dict
        Investor calibration config (same as for build_redemption_schedule).

    Returns
    -------
    tuple
        (weighted_normal_rate, weighted_stress_rate) as floats.
    """
    investors = calibration_config['investors']

    normal_rate = sum(inv['weight'] * inv['base_redemption_rate'] for inv in investors)
    stress_rate = sum(inv['weight'] * inv['stress_redemption_rate'] for inv in investors)

    return normal_rate, stress_rate


def compute_redemption_scenarios(
    investor_base: dict,
    calibration_config: dict,
) -> dict:
    """Compute redemption scenarios (Base, Large, Stress) and extract largest investor.

    Parameters
    ----------
    investor_base : dict
        Investor register dict with 'investors' list. Each investor has 'nav_pct'.

    calibration_config : dict
        Calibration config with investors (type, weight, rates) and stress_months.

    Returns
    -------
    dict
        Dict with keys:
        - 'redemption_scenarios': list of dicts with 'name' and 'redemption_pct'
        - 'largest_investor_pct': float, largest single investor as % of NAV
        - 'largest_investor_name': str
        - 'weighted_normal_rate': float
        - 'weighted_stress_rate': float
    """
    # Get weighted rates from calibration
    normal_rate, stress_rate = compute_weighted_reference_rates(calibration_config)

    # Find largest investor from investor base (exclude "Remaining" aggregates)
    investors_list = investor_base.get('investors', [])
    if investors_list:
        # Filter out aggregate "Remaining" entries
        actual_investors = [
            inv for inv in investors_list
            if not ('REM' in inv.get('investor_id', '') or
                    'remaining' in inv.get('investor_name', '').lower())
        ]
        if actual_investors:
            largest = max(actual_investors, key=lambda x: x.get('nav_pct', 0))
        else:
            # Fallback: if all are aggregates, use the largest
            largest = max(investors_list, key=lambda x: x.get('nav_pct', 0))
        largest_investor_pct = largest.get('nav_pct', 0)
        largest_investor_name = largest.get('investor_name', 'Unknown')
    else:
        largest_investor_pct = 0.0
        largest_investor_name = 'Unknown'

    # Calibrate scenarios
    # Base: use weighted normal rate
    # Large: heuristic — 1.5x normal (moderate escalation)
    # Stress: use weighted stress rate
    scenarios = [
        {'name': 'Base', 'redemption_pct': normal_rate},
        {'name': 'Large', 'redemption_pct': min(1.5 * normal_rate, 0.40)},  # cap at 40%
        {'name': 'Stress', 'redemption_pct': stress_rate},
        {'name': 'Largest investor', 'redemption_pct': largest_investor_pct},
    ]

    return {
        'redemption_scenarios': scenarios,
        'largest_investor_pct': largest_investor_pct,
        'largest_investor_name': largest_investor_name,
        'weighted_normal_rate': normal_rate,
        'weighted_stress_rate': stress_rate,
    }


def summarize_investor_base_by_type(investor_base: dict) -> pd.DataFrame:
    """Summarize investor base by investor type.

    Parameters
    ----------
    investor_base : dict
        Investor register with 'investors' list.

    Returns
    -------
    pd.DataFrame
        Summary with columns: investor_type, count, aum_pct, aum_eur.
    """
    if not investor_base.get('investors'):
        return pd.DataFrame()

    df = pd.DataFrame(investor_base['investors'])
    nav_eur = investor_base.get('target_nav_eur', 1.0)

    summary = (
        df.groupby('investor_type', as_index=False)
        .agg({
            'investor_id': 'count',
            'nav_pct': 'sum',
        })
        .rename(columns={'investor_id': 'count', 'nav_pct': 'aum_pct'})
    )
    summary['aum_eur'] = summary['aum_pct'] * nav_eur
    summary = summary[['investor_type', 'count', 'aum_pct', 'aum_eur']]

    return summary


def format_scenario_for_display(scenario: dict) -> str:
    """Format a redemption scenario dict for display.

    Converts {'name': 'Base', 'redemption_pct': 0.10} to 'Base (10%)'.
    Special case: 'Largest investor' scenarios show actual % from investor register.

    Parameters
    ----------
    scenario : dict
        Dict with 'name' and 'redemption_pct' keys.

    Returns
    -------
    str
        Formatted scenario string.
    """
    name = scenario.get('name', '')
    pct = scenario.get('redemption_pct')

    if isinstance(pct, (int, float)):
        return f"{name} ({int(pct * 100)}%)"
    else:
        return name
