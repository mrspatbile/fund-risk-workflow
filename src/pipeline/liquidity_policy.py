"""Liquidity policy workflow — build and export suggested monitoring blocks.

Creates fund-specific liquidity monitoring policy recommendations from
calibration data, redemption scenarios, and stress test results.
"""

import json
from pathlib import Path


def build_fund_liquidity_policy(
    fund_id: str,
    calibration_inputs: dict,
    scenarios_result: dict,
    nav_eur: float,
) -> dict:
    """Build a liquidity monitoring policy block for a fund.

    Creates a structured policy recommendation based on fund calibration,
    investor scenarios, and NAV.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    calibration_inputs : dict
        Raw calibration data from load_investor_and_calibration_data().
        Requires: contractual_terms, stress_assumptions
    scenarios_result : dict
        Output from compute_redemption_scenarios() with:
        - 'redemption_scenarios': list of scenario dicts
        - 'largest_investor_name', 'largest_investor_pct'
    nav_eur : float
        Fund NAV in EUR

    Returns
    -------
    dict
        Liquidity monitoring policy block with:
        - pct_adv, stress_window_days, notice_period_days
        - redemption_scenarios, largest_investor_name/pct
        - _note: summary of calibration
    """
    from src.ui.liquidity_calibration_display import suggest_liquidity_policy_block

    # Extract contractual terms (required)
    contractual = calibration_inputs['contractual_terms']
    notice_days = contractual['notice_period_days']

    # Extract stress assumptions (required)
    stress_assumptions = calibration_inputs['stress_assumptions']
    stress_window = stress_assumptions['stress_window_days']

    # Build policy block
    policy = suggest_liquidity_policy_block(
        fund_id,
        scenarios_result,
        nav_eur,
        notice_period_days=notice_days,
        stress_window_days=stress_window,
    )

    return policy


def export_liquidity_policy(
    fund_id: str,
    policy: dict,
    output_dir: str | None = None,
) -> str:
    """Export liquidity monitoring policy to JSON file.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    policy : dict
        Policy block from build_fund_liquidity_policy()
    output_dir : str, optional
        Directory to save policy file. If None, uses reference_data/funds/{fund_id}/

    Returns
    -------
    str
        Path to exported file
    """
    if output_dir is None:
        module_dir = Path(__file__).parent
        output_dir = module_dir / f'../../reference_data/funds/{fund_id}'
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'suggested_liquidity_policy.json'

    with open(output_file, 'w') as f:
        json.dump(policy, f, indent=2)

    return str(output_file)
