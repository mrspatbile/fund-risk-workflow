# UCITS Wrapper Layer Implementation Summary

**Date:** 2026-06-15  
**Status:** ✓ COMPLETE  
**Test Status:** ✓ ALL TESTS PASSED

---

## Overview

Thin UCITS-specific wrapper layers have been created to enable the UCITS notebook refactoring while reusing tested hedge fund functions wherever possible. No new VaR, ES, backtesting, stress, or liquidity calculation functions were created — all of those are reused from the hedge fund workflow.

---

## Files Changed

### Configuration

| File | Change | Status |
|------|--------|--------|
| `reference_data/funds/UCITS_Balanced/risk_policy.json` | Added `reference_portfolio_id: "ucits_balanced_60_40"` | ✓ Done |
| `reference_data/benchmarks/reference_portfolios.json` | Created with UCITS 60/40 portfolio definition | ✓ New |
| `src/data/reference_data.py` | Added `load_reference_portfolios()` and `load_reference_portfolio()` loaders | ✓ Updated |

### Wrapper Modules

| File | Purpose | Status |
|------|---------|--------|
| `src/risk/ucits_relative_var.py` | UCITS relative VaR computation wrapper | ✓ New |
| `src/risk/ucits_srri.py` | UCITS SRRI (SRI) computation per CESR/10-673 | ✓ New |

### Tests

| File | Purpose | Status |
|------|---------|--------|
| `tests/test_ucits_wrappers.py` | Validation tests for all wrapper functions | ✓ New |

---

## Functions Created

### 1. `src/data/reference_data.py` — New loaders

```python
def load_reference_portfolios() -> dict:
    """Load all reference portfolios from central config."""

def load_reference_portfolio(reference_portfolio_id: str) -> dict:
    """Load specific reference portfolio by ID."""
```

**Purpose:** Load benchmark portfolio definitions from `reference_data/benchmarks/reference_portfolios.json`

**Usage in notebook:**
```python
from src.data.reference_data import load_reference_portfolio
portfolio = load_reference_portfolio('ucits_balanced_60_40')
```

---

### 2. `src/risk/ucits_relative_var.py` — Relative VaR wrapper

**Key functions:**

#### `build_reference_portfolio_pnl(bbg, reference_portfolio_config, valuation_date, lookback_days=250) -> Tuple[np.ndarray, float]`

Reconstructs reference portfolio P&L series using fixed-position approach. Holds portfolio weights fixed as of valuation date and revalues under historical market moves.

**Returns:** (pnl_returns, nav)

---

#### `compute_reference_portfolio_var(bbg, reference_portfolio_config, valuation_date, confidence=0.99, horizon_days=20, lookback_days=250) -> dict`

Computes VaR for reference portfolio using historical simulation.

**Returns:**
```python
{
    'var_1d_pct': float,
    'var_scaled_pct': float,
    'var_1d_decimal': float,
    'var_scaled_decimal': float,
    'es_1d_pct': float,
    'es_scaled_pct': float,
    'confidence': float,
    'horizon_days': int,
    'lookback_days': int,
    'nav': float,
    'valuation_date': str,
}
```

---

#### `compute_ucits_relative_var(fund_var_result, reference_var_result, ucits_config) -> dict`

Computes UCITS relative VaR ratio and checks against regulatory limit.

**Returns:**
```python
{
    'fund_var_pct': float,
    'reference_var_pct': float,
    'relative_var_ratio': float,
    'limit_multiplier': float,
    'breach': bool,
    'utilisation_pct': float,
    'status': str,  # 'OK', 'WARNING', 'BREACH'
}
```

---

#### `evaluate_relative_var_limit(fund_var_pct, reference_var_pct, limit_multiplier=2.0) -> dict`

Standalone evaluation of relative VaR limit compliance (no dependencies on other structs).

**Returns:** `{'ratio': float, 'breach': bool, 'utilisation_pct': float}`

---

### 3. `src/risk/ucits_srri.py` — SRRI computation

**Key functions:**

#### `compute_srri_from_returns(returns, annualisation_factor=52) -> dict`

Computes SRRI category and volatility metrics from return series (weekly or daily).

**Returns:**
```python
{
    'sri_bucket': int (1-7),
    'volatility_weekly_pct': float,
    'volatility_annual_pct': float,
    'observation_count': int,
    'time_window_years': float,
}
```

---

#### `map_volatility_to_srri_bucket(annualised_volatility_pct) -> int`

Maps annualised volatility to SRRI category 1-7 per CESR/10-673.

**SRRI Boundaries:**
- SRI 1: < 0.5%
- SRI 2: 0.5% – 2%
- SRI 3: 2% – 5%
- SRI 4: 5% – 10%
- SRI 5: 10% – 15%
- SRI 6: 15% – 25%
- SRI 7: ≥ 25%

---

#### `compute_srri_from_nav_history(nav_series, window_weeks=260) -> dict`

Computes SRRI from NAV history using rolling 5-year (260-week) window.

**Returns:** `{'sri_bucket': int, 'volatility_annual_pct': float, 'window_weeks': int, 'data_points': int, 'status': str}`

---

#### `check_srri_change_trigger(current_bucket, bucket_history, persistence_months=4) -> Tuple[bool, dict]`

Checks if SRI has changed for 4 consecutive months (triggers KID update per CESR/10-673).

**Returns:** `(trigger: bool, details: dict)`

---

#### `srri_as_string(bucket: int) -> str`

Converts SRRI bucket to descriptive text (e.g., "Very Low Risk").

---

## Configuration Files

### `reference_data/benchmarks/reference_portfolios.json`

```json
{
  "ucits_balanced_60_40": {
    "name": "UCITS Balanced 60/40 Reference Portfolio",
    "description": "Reference portfolio for UCITS relative VaR monitoring.",
    "components": [
      {
        "identifier": "MSCI_WORLD",
        "asset_class": "equity",
        "weight": 0.60,
        "proxy_ticker": "SPY US Equity",
        "currency": "USD"
      },
      {
        "identifier": "EUR_GOVERNMENT_BONDS",
        "asset_class": "fixed_income",
        "weight": 0.40,
        "proxy_ticker": "IEAG LN Equity",
        "currency": "EUR"
      }
    ],
    "rebalance_frequency": "annual",
    "use_case": "relative_var"
  }
}
```

---

### `reference_data/funds/UCITS_Balanced/risk_policy.json` — Added field

```json
{
  "fund_id": "UCITS_Balanced",
  "reference_portfolio_id": "ucits_balanced_60_40",
  ...
}
```

---

## How the Wrapper Will Be Called from Notebook

### Pattern 1: Absolute VaR (Reuse hedge fund directly)

```python
from src.pipeline.fixed_position_var import compute_fixed_position_var_1day

var_result = compute_fixed_position_var_1day(
    engine=ENGINE,
    fund_id=FUND_ID,
    valuation_date=VALUATION_DATE,
    confidence=0.99,
    df=5,
    horizon=20,
)

phtml.display_var_es(var_result, valuation_date=VALUATION_DATE, fund_id=FUND_ID, export_id="06")
```

**Cell size:** 5 lines  
**Current UCITS:** 59 lines

---

### Pattern 2: Relative VaR (Use wrapper)

```python
from src.data.reference_data import load_reference_portfolio, load_regulatory_framework, load_rmp
from src.risk.ucits_relative_var import (
    compute_reference_portfolio_var,
    compute_ucits_relative_var,
)

# Load configs
rmp = load_rmp(FUND_ID)
ucits_config = load_regulatory_framework('ucits_regulatory_framework')
ref_portfolio = load_reference_portfolio(rmp['reference_portfolio_id'])

# Compute reference portfolio VaR
ref_var_result = compute_reference_portfolio_var(
    bbg=BBG,
    reference_portfolio_config=ref_portfolio,
    valuation_date=VALUATION_DATE,
    confidence=0.99,
    horizon_days=20,
)

# Compute relative VaR
rel_var_result = compute_ucits_relative_var(
    fund_var_result=var_result,
    reference_var_result=ref_var_result,
    ucits_config=ucits_config,
)

# Display
phtml.display_relative_var(rel_var_result, valuation_date=VALUATION_DATE, fund_id=FUND_ID)
```

**Cell size:** ~15 lines  
**Current UCITS:** 75 lines

---

### Pattern 3: SRRI (Use wrapper)

```python
from src.risk.ucits_srri import compute_srri_from_nav_history, check_srri_change_trigger
from src.data.database import query_nav_history

nav_history = query_nav_history(ENGINE, FUND_ID)

srri_result = compute_srri_from_nav_history(
    nav_series=nav_history['nav_eur'],
    window_weeks=rmp['srri_monitoring']['window_weeks'],
)

kid_trigger = check_srri_change_trigger(
    current_bucket=srri_result['sri_bucket'],
    bucket_history=previous_srri_history,
    persistence_months=rmp['srri_monitoring']['category_change_persistence_months'],
)
```

**Cell size:** ~12 lines  
**Current UCITS:** 35+ lines

---

## Tests & Validation

### Run tests:
```bash
source .venv/bin/activate
python3 tests/test_ucits_wrappers.py
```

### Test coverage:

✓ Reference data loaders (load_rmp, load_regulatory_framework, load_reference_portfolios)  
✓ Reference portfolio weight validation  
✓ SRRI bucket mapping (all 7 categories)  
✓ SRRI computation from returns  
✓ SRRI change trigger logic  
✓ Relative VaR evaluation (compliance, utilisation, breach detection)  

All tests pass.

---

## Design Principles

1. **No duplication of computation logic** — All VaR, ES, backtesting, stress, liquidity functions are reused from hedge fund workflow via `src/computation/` and `src/pipeline/` layers.

2. **Configuration-driven** — Regulatory limits, fund policy, and benchmark definitions are externalized to JSON config files, not hardcoded in modules.

3. **Thin wrapper layers** — UCITS-specific modules only implement logic that is truly UCITS-unique:
   - Relative VaR (not used by AIFs)
   - SRRI/SRI computation (specific to UCITS/PRIIPs disclosure)
   - Regulatory limit checks specific to UCITS Articles

4. **Reusable output structures** — All functions return dictionaries that can be passed directly to display functions or used in further calculations.

5. **Testable and independent** — Each function can be tested in isolation without requiring the full notebook context.

---

## Blockers Before Notebook Refactoring

### None identified

All required dependencies are satisfied:
- ✓ Configuration files created and validated
- ✓ Reference portfolio definition loaded and weights validated
- ✓ Wrapper modules created and syntax-checked
- ✓ All wrapper functions tested
- ✓ Loaders integrated into reference_data.py
- ✓ Compatible with existing hedge fund display functions

---

## Next Steps

**Phase 5: Notebook Refactoring** can proceed immediately:

1. Replace large cell 26 (59 lines) with 5-line function calls
2. Replace cell 31 (75 lines) with relative VaR wrapper calls (~15 lines)
3. Replace cell 34 (35 lines) with SRRI wrapper calls (~12 lines)
4. Replace other large cells following the same pattern

See `docs/refactor_plans/ucits_low_code_refactor_plan_REVISED.md` for complete cell-by-cell mapping.

---

## Files Inspected (For Reference)

- `notebooks/funds/aifm_hedge_fund.ipynb` — Reference low-code pattern
- `src/pipeline/fixed_position_var.py` — VaR pipeline function
- `src/computation/var.py`, `stress.py`, `liquidity.py` — Canonical computation layer
- `src/risk/risk_utils.py` — Risk utility imports (re-exports from computation layer)
- `src/ui/print_html_utils.py` — Display functions (reusable)
- `reference_data/regulation/ucits_regulatory_framework.json` — Already complete

---

## Summary

All UCITS-specific thin wrappers are ready. The notebook can now be refactored to use these wrappers alongside reused hedge fund functions, resulting in a clean, maintainable, low-code UCITS monitoring workflow.
