"""
reference_data.py
=================
Reference data loading helpers.

Functions for loading fund-level reference data (profiles, policies, etc.)
from JSON files.

Schema versioning
-----------------
All reference_data JSON files include a "schema_version" key (currently "1.0").
Loaders automatically strip schema_version from returned data, presenting only
the actual fund/regulatory data. This allows future schema evolution without
breaking consumer code.
"""

import json
from pathlib import Path
import pandas as pd


def load_rmp(fund_id: str) -> dict:
    """
    Load Risk Management Policy from JSON file.

    Works from any working directory (notebooks/, src/, project root, etc).

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'AIFM_HedgeFund')

    Returns
    -------
    dict
        Risk Management Policy as a Python dictionary.

    Examples
    --------
    >>> rmp = load_rmp('AIFM_HedgeFund')
    >>> print(rmp.keys())
    """
    # Works from any working directory by using __file__ to find project root
    module_dir = Path(__file__).parent
    ref_data_path = module_dir / '../../../reference_data' / 'funds' / fund_id / 'risk_policy.json'
    with open(ref_data_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_fund_profile(fund_id: str) -> dict:
    """
    Load fund profile (static fund facts and regulatory classification) from JSON file.

    Works from any working directory (notebooks/, src/, project root, etc).

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced', 'AIFM_HedgeFund')

    Returns
    -------
    dict
        Fund profile as a Python dictionary (fund_id, fund_name, fund_type,
        strategy, currency, domicile, regulatory classification, data model, etc).

    Examples
    --------
    >>> profile = load_fund_profile('UCITS_Balanced')
    >>> print(profile['fund_name'])
    """
    module_dir = Path(__file__).parent
    profile_path = module_dir / '../../../reference_data' / 'funds' / fund_id / 'fund_profile.json'
    with open(profile_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def get_fund_name(fund_id: str) -> str:
    """Return the fund display name from fund_profile.json.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced', 'AIFM_HedgeFund')

    Returns
    -------
    str
        Fund display name (e.g., 'UCITS Balanced')

    Raises
    ------
    KeyError
        If fund_profile.json is missing or fund_name field is absent.

    Examples
    --------
    >>> get_fund_name('UCITS_Balanced')
    'UCITS Balanced'
    """
    profile = load_fund_profile(fund_id)

    if "fund_name" not in profile:
        raise KeyError(f"fund_name missing in {fund_id}/fund_profile.json")

    return profile["fund_name"]


def load_regulatory_framework(framework_name: str) -> dict:
    """
    Load regulatory framework configuration from JSON file.

    Works from any working directory (notebooks/, src/, project root, etc).

    Parameters
    ----------
    framework_name : str
        Framework identifier (e.g., 'ucits_regulatory_framework', 'aifmd_annex_iv_framework')

    Returns
    -------
    dict
        Regulatory framework as a Python dictionary.

    Examples
    --------
    >>> ucits_regs = load_regulatory_framework('ucits_regulatory_framework')
    >>> print(ucits_regs['var_framework']['absolute_limit_pct'])
    """
    module_dir = Path(__file__).parent
    reg_path = module_dir / '../../../reference_data/regulation' / f'{framework_name}.json'
    with open(reg_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_reference_portfolios() -> dict:
    """
    Load all reference portfolios from central config.

    Works from any working directory.

    Returns
    -------
    dict
        All reference portfolios keyed by portfolio ID.

    Examples
    --------
    >>> portfolios = load_reference_portfolios()
    >>> portfolio = portfolios['ucits_balanced_60_40']
    """
    module_dir = Path(__file__).parent
    bench_path = module_dir / '../../../reference_data/benchmarks/reference_portfolios.json'
    with open(bench_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_reference_portfolio(reference_portfolio_id: str) -> dict:
    """
    Load a specific reference portfolio by ID.

    Works from any working directory.

    Parameters
    ----------
    reference_portfolio_id : str
        Portfolio identifier (e.g., 'ucits_balanced_60_40')

    Returns
    -------
    dict
        Reference portfolio configuration as a Python dictionary.

    Raises
    ------
    KeyError
        If portfolio ID not found in reference_portfolios.json

    Examples
    --------
    >>> portfolio = load_reference_portfolio('ucits_balanced_60_40')
    >>> print(portfolio['components'])
    """
    portfolios = load_reference_portfolios()
    if reference_portfolio_id not in portfolios:
        raise KeyError(
            f"Reference portfolio '{reference_portfolio_id}' not found. "
            f"Available portfolios: {list(portfolios.keys())}"
        )
    return portfolios[reference_portfolio_id]


def load_investor_base(fund_id: str, nav_eur: float = None) -> pd.DataFrame:
    """
    Load investor base from fund reference data and convert to DataFrame.

    Investor base stored as percentages of NAV; this function converts to EUR amounts.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    nav_eur : float, optional
        Current NAV in EUR. If None, uses target_nav_eur from JSON.

    Returns
    -------
    pd.DataFrame
        Investor base with columns: investor_id, investor_name, investor_type, aum_eur, nav_pct

    Examples
    --------
    >>> investors = load_investor_base('UCITS_Balanced', nav_eur=514800000)
    >>> print(investors.head())
    """
    module_dir = Path(__file__).parent
    inv_path = module_dir / f'../../../reference_data/funds/{fund_id}/investors.json'

    with open(inv_path) as f:
        data = json.load(f)

    nav = nav_eur if nav_eur is not None else data.get('target_nav_eur')

    investors_list = []
    for inv in data['investors']:
        investors_list.append({
            'investor_id': inv['investor_id'],
            'investor_name': inv['investor_name'],
            'investor_type': inv['investor_type'],
            'nav_pct': inv['nav_pct'],
            'aum_eur': inv['nav_pct'] * nav,
        })

    return pd.DataFrame(investors_list)


def load_investor_base_dict(fund_id: str) -> dict:
    """Load investor base as a dictionary (not converted to DataFrame).

    Preserves the original JSON structure with 'investors' list,
    'fund_id', 'description', 'target_nav_eur'.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')

    Returns
    -------
    dict
        Investor base dict with 'fund_id', 'investors', 'target_nav_eur', etc.

    Examples
    --------
    >>> investor_base = load_investor_base_dict('UCITS_Balanced')
    >>> print(investor_base['fund_id'])
    """
    module_dir = Path(__file__).parent
    inv_path = module_dir / f'../../../reference_data/funds/{fund_id}/investors.json'
    with open(inv_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_liquidity_calibration_inputs(fund_id: str) -> dict:
    """Load liquidity calibration inputs from JSON file.

    Contains investor type redemption rates, stress assumptions,
    and LMT parameters for liquidity stress testing.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced', 'AIFM_HedgeFund')

    Returns
    -------
    dict
        Calibration inputs with keys:
        - redemption_schedule_calibration: investor types, weights, rates
        - stress_assumptions: stress window and ADV parameters
        - lmt_calibration: gate, swing, suspension thresholds
        - (optionally) redemption_scenario_policy

    Examples
    --------
    >>> calib = load_liquidity_calibration_inputs('AIFM_HedgeFund')
    >>> print(calib['redemption_schedule_calibration']['sigma'])
    """
    module_dir = Path(__file__).parent
    calib_path = module_dir / f'../../../reference_data/funds/{fund_id}/liquidity_calibration_inputs.json'
    with open(calib_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_investor_type_mapping() -> dict:
    """Load the shared investor type mapping.

    Maps investor registry categories to liquidity calibration categories.

    Returns
    -------
    dict
        Mapping dict with key 'investor_type_mapping' containing:
        registry_type -> calibration_type mappings
    """
    module_dir = Path(__file__).parent
    mapping_path = module_dir / '../../../reference_data/platform/investor_type_mapping.json'
    with open(mapping_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def compute_liquidity_calibration_weights(
    investor_records: list,
    investor_type_mapping: dict,
    calibration_investors: list,
) -> dict:
    """Compute liquidity calibration weights from investor registry.

    Maps investor registry types to calibration types, groups by calibration type,
    and sums nav_pct to produce weights for the liquidity model.

    Parameters
    ----------
    investor_records : list
        List of investor dicts from investor registry, each with:
        - 'investor_type': registry investor category (e.g., 'Pension Plan', 'Retail')
        - 'nav_pct': investor weight as % of NAV (float, should sum to ~1.0)
    investor_type_mapping : dict
        Dict mapping registry investor_type to calibration type.
        Keys: registry types (e.g., 'Pension Plan', 'Platform')
        Values: calibration types (e.g., 'Institutional', 'Retail')
    calibration_investors : list
        List of calibration investor type dicts, each with 'type' key.
        Used to validate that all mapped calibration types exist.

    Returns
    -------
    dict
        Weights by calibration type.
        Key: calibration type (e.g., 'Retail', 'Institutional')
        Value: summed nav_pct for investors of that type

    Raises
    ------
    ValueError
        If any registry investor_type is not in the mapping (no silent defaults).
        If any mapped calibration type is not in calibration_investors.
        If total nav_pct is not close to 1.0.
    """
    # Build set of valid calibration types
    valid_calib_types = {inv['type'] for inv in calibration_investors}

    # Map registry types to calibration types and sum weights
    weights_by_calib_type = {}

    for investor in investor_records:
        registry_type = investor.get('investor_type')
        nav_pct = investor.get('nav_pct', 0.0)

        # Validate: registry type must have a mapping
        if registry_type not in investor_type_mapping:
            raise ValueError(
                f"Investor type '{registry_type}' not found in investor_type_mapping. "
                f"Valid types: {sorted(investor_type_mapping.keys())}"
            )

        # Map to calibration type
        calib_type = investor_type_mapping[registry_type]

        # Validate: calibration type must exist in assumptions
        if calib_type not in valid_calib_types:
            raise ValueError(
                f"Mapped calibration type '{calib_type}' (from registry type '{registry_type}') "
                f"not found in calibration investor types. "
                f"Valid calibration types: {sorted(valid_calib_types)}"
            )

        # Accumulate weight
        weights_by_calib_type[calib_type] = weights_by_calib_type.get(calib_type, 0.0) + nav_pct

    # Validate: total should be close to 1.0
    total_weight = sum(weights_by_calib_type.values())
    if not (0.95 <= total_weight <= 1.05):
        raise ValueError(
            f"Total investor nav_pct = {total_weight:.4f}, expected close to 1.0. "
            f"Weights by type: {weights_by_calib_type}"
        )

    return weights_by_calib_type


def load_investor_and_calibration_data(fund_id: str) -> dict:
    """Load investor bases and calibration inputs for a single fund.

    Normalizes calibration config structure to handle both UCITS and AIF formats.
    UCITS stores config at top level; AIFs nest it under redemption_schedule_calibration.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced', 'AIFM_HedgeFund')

    Returns
    -------
    dict
        Dictionary with keys:
        - 'investor_inputs': investor_base_dict for the fund
        - 'calibration_inputs': raw_calibration for the fund
        - 'calibration_config': normalized_config with keys:
            - 'investors': list of investor types with weights and rates
            - 'stress_months': list of months with deterministic stress rates
            - 'sigma': volatility parameter for stochastic draws
            - 'seed': random seed for reproducibility

    Examples
    --------
    >>> data = load_investor_and_calibration_data('UCITS_Balanced')
    >>> data['calibration_config']['sigma']
    0.3
    """
    # Load investor base
    investor_inputs = load_investor_base_dict(fund_id)

    # Load raw calibration
    raw_calib = load_liquidity_calibration_inputs(fund_id)

    # Normalize calibration config structure
    # AIFs nest under redemption_schedule_calibration; UCITS at top level
    if "redemption_schedule_calibration" in raw_calib:
        calibration_config = raw_calib["redemption_schedule_calibration"]
    else:
        calibration_config = {
            "investors": raw_calib["investors"],
            "stress_months": raw_calib["stress_months"],
            "redemption_concentration": raw_calib["redemption_concentration"],
            "seed": raw_calib["seed"],
        }

    return {
        "investor_inputs": investor_inputs,
        "calibration_inputs": raw_calib,
        "calibration_config": calibration_config,
    }


def get_lmt_parameters(fund_id: str, calibration_inputs: dict) -> dict:
    """Extract LMT (Liquidity Management Tools) parameters from fund calibration inputs.

    Retrieves gate, swing, and suspension thresholds; liquidity percentage;
    and contagion assumptions for LMT trigger analysis.

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    calibration_inputs : dict
        Raw calibration data from load_investor_and_calibration_data().
        For single-fund pattern, pass data['calibration_inputs'].

    Returns
    -------
    dict
        LMT parameters:
        - 'liquid_pct': percentage of NAV that is liquid
        - 'gate_threshold': redemption gate threshold (% of NAV)
        - 'swing_threshold': swing pricing trigger (% of NAV)
        - 'contagion': contagion multiplier (affects future redemption requests)
        - 'consec_gate': consecutive gate months before suspension considered
        - 'backlog_pct': backlog % of liquid NAV threshold for suspension

    Examples
    --------
    >>> data = load_investor_and_calibration_data('UCITS_Balanced')
    >>> lmt = get_lmt_parameters('UCITS_Balanced', data['calibration_inputs'])
    >>> lmt['liquid_pct']
    0.85
    """
    lmt_config = calibration_inputs["lmt_calibration"]

    return {
        "liquid_pct": lmt_config["liquid_pct"],
        "gate_threshold": lmt_config["gate_threshold_pct"],
        "swing_threshold": lmt_config["swing_threshold_pct"],
        "contagion": lmt_config["contagion_multiplier"],
        "consec_gate": lmt_config["consecutive_gate_months"],
        "backlog_pct": lmt_config["backlog_pct"],
    }


def get_stress_testing_params(fund_id: str, calibration_inputs: dict, redemption_scenario: str = "Large") -> dict:
    """Extract stress testing parameters from fund calibration inputs.

    Retrieves redemption stress testing assumptions: notice period, ADV percentage,
    and the specific redemption scenario to test (Base, Large, Stress, Largest investor).

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    calibration_inputs : dict
        Raw calibration data from load_investor_and_calibration_data().
        For single-fund pattern, pass data['calibration_inputs'].
    redemption_scenario : str, optional
        Which redemption scenario to test (default: "Large").
        Options: "Base" (normal), "Large" (25%), "Stress" (all stress rates),
                 "Largest investor" (largest investor + stress)

    Returns
    -------
    dict
        Stress testing parameters:
        - 'pct_adv': percent of average daily volume for liquidity buckets
        - 'notice_days': notice period in days
        - 'redemption_pct': redemption percentage for scenario (inferred from name)
        - 'stress_window_days': window for stress testing

    Examples
    --------
    >>> data = load_investor_and_calibration_data('UCITS_Balanced')
    >>> params = get_stress_testing_params('UCITS_Balanced', data['calibration_inputs'])
    >>> params['notice_days']
    1
    """
    contractual = calibration_inputs["contractual_terms"]
    stress_assumptions = calibration_inputs["stress_assumptions"]

    # Map scenario names to redemption percentages
    scenario_pct_map = {
        "Base": 0.05,
        "Large": 0.25,
        "Stress": 1.0,  # All stress rates (depends on investor composition)
        "Largest investor": 0.25,  # Largest investor redemption
    }

    return {
        "pct_adv": stress_assumptions["pct_adv"],
        "notice_days": contractual["notice_period_days"],
        "redemption_pct": scenario_pct_map[redemption_scenario],
        "stress_window_days": stress_assumptions["stress_window_days"],
        "scenario_name": redemption_scenario,
    }


def merge_computed_weights_into_investors(
    calibration_investors: list,
    computed_weights: dict,
) -> list:
    """Merge computed investor weights into calibration investor assumptions.

    Creates a new investor list with computed weights from the registry
    merged into the calibration investor types.

    Parameters
    ----------
    calibration_investors : list
        List of investor dicts from calibration, each with 'type', 'base_redemption_rate', etc.
    computed_weights : dict
        Dict mapping calibration type to computed weight (from registry).
        E.g., {'Retail': 0.40, 'Institutional': 0.45, 'Family Office': 0.15}

    Returns
    -------
    list
        New list of investor dicts with 'weight' field added from computed_weights.
        E.g., [
            {'type': 'Retail', 'weight': 0.40, 'base_redemption_rate': 0.03, ...},
            {'type': 'Institutional', 'weight': 0.45, 'base_redemption_rate': 0.04, ...},
            ...
        ]

    Raises
    ------
    ValueError
        If any calibration type has no computed weight.
        If computed weights contain a type not in calibration.
    """
    # Validate: computed weights must not have types missing from calibration
    calib_types = {inv['type'] for inv in calibration_investors}
    for computed_type in computed_weights.keys():
        if computed_type not in calib_types:
            raise ValueError(
                f"Computed weight type '{computed_type}' not found in calibration investor types. "
                f"Valid calibration types: {sorted(calib_types)}"
            )

    # Merge weights into calibration investors
    # If a calibration type is missing from computed weights, set weight to 0.0
    # (e.g., if registry has no Family Office investors, weight = 0)
    enriched_investors = []
    for inv in calibration_investors:
        inv_type = inv['type']
        weight = computed_weights.get(inv_type, 0.0)
        enriched = {**inv, 'weight': weight}
        enriched_investors.append(enriched)

    return enriched_investors


def load_historical_scenarios() -> dict:
    """Load historical stress scenarios from JSON file.

    Returns a dict of named historical scenarios (2008, 2011, 2020, 2022)
    with shock parameters for equity, rates, credit, and FX.

    Works from any working directory.

    Returns
    -------
    dict
        Historical scenarios keyed by year (e.g., '2008', '2020').
        Each scenario has:
        - 'name': human-readable scenario label
        - 'description': context and market factors
        - 'delta_equity': equity shock (decimal, e.g., -0.30)
        - 'delta_y': yield shock (decimal, e.g., 0.02)
        - 'delta_spread': credit spread shock (decimal)
        - 'fx_shocks': dict of FX shocks by currency code

    Examples
    --------
    >>> scenarios = load_historical_scenarios()
    >>> print(scenarios['2008']['name'])
    'GFC 2008 (Sep-Dec 2008)'
    >>> scenarios['2020']['delta_equity']
    -0.30
    """
    module_dir = Path(__file__).parent
    scenarios_path = module_dir / '../../../reference_data/scenarios/historical_scenarios.json'
    with open(scenarios_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version (validation happens at data layer)
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_esg_scores() -> dict:
    """
    Load ESG scores for instruments (equities, bonds, PE companies, infrastructure assets).

    Returns a dict keyed by ISIN, Bloomberg ticker, or asset ID (PE/infra),
    with ESG metrics: esg_score, env_score, soc_score, gov_score, controversy_flag,
    carbon_intensity.

    Works from any working directory.

    Returns
    -------
    dict
        ESG scores keyed by instrument identifier (ISIN, company_id, asset_id).

    Examples
    --------
    >>> esg_data = load_esg_scores()
    >>> print(esg_data['US0378331005'])  # Apple ESG scores
    """
    module_dir = Path(__file__).parent
    esg_path = module_dir / '../../../reference_data/instruments/esg_scores.json'
    with open(esg_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def load_scenario_file(filename: str) -> dict:
    """
    Load stress scenario definitions from risk_scenarios JSON files.

    Supports both univariate and historical scenario definitions.

    Works from any working directory.

    Parameters
    ----------
    filename : str
        Base name of scenario file without .json extension.
        Examples: 'ucits_univariate_stress_scenarios', 'scenario_library_2_historical'

    Returns
    -------
    dict
        Scenario definitions (typically with 'scenarios' key containing list or dict).

    Examples
    --------
    >>> univariate = load_scenario_file('ucits_univariate_stress_scenarios')
    >>> historical = load_scenario_file('scenario_library_2_historical')
    """
    module_dir = Path(__file__).parent
    scenario_path = module_dir / f'../../../reference_data/risk_scenarios/{filename}.json'
    with open(scenario_path) as f:
        data = json.load(f)
        # Extract data if wrapped with schema_version
        if isinstance(data, dict) and 'schema_version' in data and len(data) > 1:
            # Remove schema_version and return remaining content
            return {k: v for k, v in data.items() if k != 'schema_version'}
        return data


def build_lmt_parameters(fund_id: str, calibration_inputs: dict, calibration_config: dict) -> dict:
    """Build LMT parameters and redemption schedules for a single fund.

    Extracts and structures calibration data needed for LMT trigger analysis:
    - Computes investor weights from registry using type mapping
    - Merges computed weights into calibration investor assumptions
    - Builds 12-month stochastic redemption schedule
    - Extracts LMT thresholds, contractual terms, stress assumptions

    Works from any working directory.

    Parameters
    ----------
    fund_id : str
        Fund identifier (e.g., 'UCITS_Balanced')
    calibration_inputs : dict
        Raw calibration data for the fund (typically from load_investor_and_calibration_data())
    calibration_config : dict
        Normalized calibration config for the fund (currently without weights)

    Returns
    -------
    dict
        LMT parameters: {'label', 'schedule', 'contractual_terms',
                         'stress_assumptions', 'lmt_thresholds', 'investors_enriched'}

    Examples
    --------
    >>> data = load_investor_and_calibration_data('UCITS_Balanced')
    >>> lmt_params = build_lmt_parameters(
    ...     'UCITS_Balanced',
    ...     data['calibration_inputs'],
    ...     data['calibration_config']
    ... )
    >>> lmt_params['schedule'][:3]  # First 3 months
    """
    from fund_risk_workflow.computation.liquidity_calibration import build_redemption_schedule

    fund_label = get_fund_name(fund_id)

    # Compute investor weights from registry and mapping
    investor_base = load_investor_base_dict(fund_id)
    investor_type_mapping = load_investor_type_mapping()
    calib_investors = calibration_config['investors']

    computed_weights = compute_liquidity_calibration_weights(
        investor_records=investor_base['investors'],
        investor_type_mapping=investor_type_mapping['investor_type_mapping'],
        calibration_investors=calib_investors,
    )

    # Merge computed weights into calibration investor assumptions
    enriched_investors = merge_computed_weights_into_investors(
        calibration_investors=calib_investors,
        computed_weights=computed_weights,
    )

    # Create enriched calibration config with weights
    enriched_calibration_config = {**calibration_config, 'investors': enriched_investors}

    # Build 12-month redemption schedule (stochastic with stress overrides)
    schedule = build_redemption_schedule(enriched_calibration_config, n_months=12)

    # Extract LMT thresholds, contractual terms, stress assumptions
    lmt_config = calibration_inputs["lmt_calibration"]
    contractual = calibration_inputs["contractual_terms"]
    stress_assumptions = calibration_inputs["stress_assumptions"]

    return {
        "label": fund_label,
        "schedule": schedule,
        "contractual_terms": contractual,
        "stress_assumptions": stress_assumptions,
        "lmt_thresholds": lmt_config,
        "investors_enriched": enriched_investors,
    }
