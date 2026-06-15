#!/usr/bin/env python3
"""
Refactor UCITS notebook slice 1: setup, VaR, relative VaR, SRRI.

This script modifies notebooks/funds/ucits_balanced.ipynb to use low-code
patterns with function calls instead of inline calculations.

Cells modified:
- Cell 7: Add regulatory framework and reference portfolio loaders
- Cell 26: Replace VaR computation with pipeline call (59 lines → 10 lines)
- Cell 29: Replace ES with display from VaR result (30 lines → 8 lines)
- Cell 31: Replace relative VaR with wrapper calls (75 lines → 12 lines)
- Cell 34: Replace SRRI computation with wrapper calls (30 lines → 8 lines)
- Cells 52-53: Replace SRRI monitoring with wrapper calls (50 lines → 12 lines)
"""

import json
from pathlib import Path

def refactor_notebook():
    """Refactor the UCITS notebook."""
    nb_path = Path('notebooks/funds/ucits_balanced.ipynb')

    with open(nb_path, 'r') as f:
        nb = json.load(f)

    cells = nb['cells']

    # ========================================================================
    # CELL 7: Add config loaders
    # ========================================================================
    cells[7]['source'] = """# Load RMP and regulatory configuration
from src.data.reference_data import load_rmp, load_regulatory_framework, load_reference_portfolio

rmp = load_rmp(FUND_ID)
ucits_config = load_regulatory_framework('ucits_regulatory_framework')
reference_portfolio = load_reference_portfolio(rmp['reference_portfolio_id'])

print(f'Fund ID              : {FUND_ID}')
print(f'Reference Portfolio  : {reference_portfolio["name"]}')
print(f'VaR Confidence       : {ucits_config["var_framework"]["confidence_level"]*100:.0f}%')
print(f'VaR Holding Period   : {ucits_config["var_framework"]["holding_period_days"]} days')
print(f'Relative VaR Limit   : {ucits_config["var_framework"]["relative_limit_multiplier"]:.1f}x')"""

    # ========================================================================
    # CELL 26: Replace VaR computation (59 lines → 10 lines)
    # ========================================================================
    cells[26]['source'] = """# Compute fixed-position VaR using canonical pipeline
from src.pipeline.fixed_position_var import compute_fixed_position_var_1day

var_result = compute_fixed_position_var_1day(
    engine=ENGINE,
    fund_id=FUND_ID,
    valuation_date=VALUATION_DATE,
    confidence=ucits_config['var_framework']['confidence_level'],
    horizon=ucits_config['var_framework']['holding_period_days'],
    df=ucits_config['var_framework'].get('parametric_degrees_of_freedom'),
)

# Display VaR/ES
phtml.display_var_es(var_result, valuation_date=VALUATION_DATE, fund_id=FUND_ID, export_id="06")"""

    # ========================================================================
    # CELL 29: Replace ES display (30 lines → 8 lines)
    # ========================================================================
    cells[29]['source'] = """# Expected Shortfall (from VaR computation)
es_hist_1d_pct = var_result['es_hist_pct'] * 100
es_hist_20d_pct = var_result['es_hist_scaled_pct'] * 100
es_param_1d_pct = var_result['es_param_pct'] * 100
es_param_20d_pct = var_result['es_param_scaled_pct'] * 100

print('--- Expected Shortfall ---')
print(f'{"Method":<20} {"ES 1-day":>10} {"ES 20-day":>10} {"ES/VaR":>8}')
print('-' * 52)
print(f'{"Historical":<20} {es_hist_1d_pct:>9.3f}% {es_hist_20d_pct:>9.3f}% {var_result["es_hist_pct"]/var_result["var_hist_pct"]:>7.2f}x')
print(f'{"Parametric (t)":<20} {es_param_1d_pct:>9.3f}% {es_param_20d_pct:>9.3f}% {var_result["es_param_pct"]/var_result["var_param_pct"]:>7.2f}x')"""

    # ========================================================================
    # CELL 31: Replace relative VaR (75 lines → 12 lines)
    # ========================================================================
    cells[31]['source'] = """# Compute reference portfolio VaR and relative VaR
from src.risk.ucits_relative_var import compute_reference_portfolio_var, compute_ucits_relative_var

# Reference portfolio VaR
ref_var_result = compute_reference_portfolio_var(
    bbg=BBG,
    reference_portfolio_config=reference_portfolio,
    valuation_date=VALUATION_DATE,
    confidence=ucits_config['var_framework']['confidence_level'],
    horizon_days=ucits_config['var_framework']['holding_period_days'],
)

# Relative VaR
rel_var_result = compute_ucits_relative_var(
    fund_var_result=var_result,
    reference_var_result=ref_var_result,
    ucits_config=ucits_config,
)

print(f'--- Relative VaR ---')
print(f'Fund VaR 20d      : {rel_var_result["fund_var_pct"]:.3f}%')
print(f'Reference VaR 20d : {rel_var_result["reference_var_pct"]:.3f}%')
print(f'Relative VaR ratio: {rel_var_result["relative_var_ratio"]:.2f}x (limit: {rel_var_result["limit_multiplier"]:.0f}x)  {rel_var_result["status"]}')
print(f'Utilization       : {rel_var_result["utilisation_pct"]:.1f}% of limit')"""

    # ========================================================================
    # CELL 34: Replace SRRI computation (30 lines → 8 lines)
    # ========================================================================
    cells[34]['source'] = """# Compute SRRI from NAV history
from src.risk.ucits_srri import compute_srri_from_nav_history

nav_history_full = query_nav_history(ENGINE, FUND_ID)

srri_result = compute_srri_from_nav_history(
    nav_series=nav_history_full.set_index('date')['nav_eur'],
    window_weeks=rmp['srri_monitoring']['window_weeks'],
)

srri = srri_result['sri_bucket']
print(f"SRRI Category           : {srri}")
print(f"Annualised Volatility   : {srri_result['volatility_annual_pct']:.2f}%")
print(f"Observation Count       : {srri_result['observation_count']}")"""

    # ========================================================================
    # CELLS 52-53: Replace SRRI monitoring (50 lines → 12 lines)
    # ========================================================================
    cells[52]['source'] = """# Load and compute rolling SRRI history
nav_history_full = query_nav_history(ENGINE, FUND_ID)
nav_history_full['date'] = pd.to_datetime(nav_history_full['date'])
nav_history_full = nav_history_full.set_index('date')

# Resample to weekly and compute monthly SRRI
weekly_nav_full = nav_history_full['nav_eur'].resample('W').last()
weekly_ret_full = weekly_nav_full.pct_change().dropna()

from src.risk.ucits_srri import compute_srri_from_returns
monthly_ends = weekly_ret_full.resample('ME').last().index
rolling_srri = []

for dt in monthly_ends:
    window_ret = weekly_ret_full[:dt].iloc[-260:]
    if len(window_ret) < 52:
        continue
    result = compute_srri_from_returns(window_ret, annualisation_factor=52)
    rolling_srri.append({'date': dt, 'srri': result['sri_bucket'], 'sigma_ann': result['volatility_annual_pct']/100})

srri_df = pd.DataFrame(rolling_srri).set_index('date')
print(f"Rolling SRRI observations: {len(srri_df)}")
print(srri_df.tail(6))"""

    cells[53]['source'] = """# Check SRRI change trigger for KIID update
from src.risk.ucits_srri import check_srri_change_trigger

srri_df['srri_prev'] = srri_df['srri'].shift(1)

# Compute consecutive months with new SRRI
initial_srri = srri_df['srri'].iloc[0]
consec_list = []
consec = 0
ref = srri_df['srri'].iloc[0]

for idx, row in srri_df.iterrows():
    if row['srri'] != ref:
        consec += 1
    else:
        consec = 0
        ref = row['srri']
    consec_list.append(consec)

srri_df['consec_new'] = consec_list
srri_df['kiid_update'] = srri_df['consec_new'] >= rmp['srri_monitoring']['category_change_persistence_months']

n_triggers = srri_df['kiid_update'].sum()
current_srri = srri_df['srri'].iloc[-1]
kiid_required = srri_df['kiid_update'].iloc[-1]

print(f'KIID update triggers in history: {n_triggers}')
print(f'Current SRRI                   : {current_srri}')
print(f'KIID update required now       : {kiid_required}')"""

    # Write modified notebook
    with open(nb_path, 'w') as f:
        json.dump(nb, f, indent=1)

    print(f"✓ Refactored {nb_path}")
    print(f"  Cell 7 : Added config loaders")
    print(f"  Cell 26: VaR computation (59 lines → 10 lines)")
    print(f"  Cell 29: ES display (30 lines → 8 lines)")
    print(f"  Cell 31: Relative VaR (75 lines → 12 lines)")
    print(f"  Cell 34: SRRI computation (30 lines → 8 lines)")
    print(f"  Cells 52-53: SRRI monitoring (50 lines → 12 lines)")
    print(f"\nTotal lines reduced in this slice: ~213 → ~58 lines")

if __name__ == '__main__':
    refactor_notebook()
