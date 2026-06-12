# Refactoring Diagnostic

## Current State

### Directory Structure
```
src/
├── cache_old/                 # Obsolete, no imports reference it
├── data/                       # Data layer (gitignored)
├── reporting/                  # Regulatory outputs (Excel, PDF)
├── risk/                       # Risk analytics
├── ui/                         # Visualization and display utilities
└── *.py                        # Top-level utilities (config, setup_db, etc.)
```

### Identified Issues

#### 1. Duplicate VaR Logic
- `src/risk/var.py` (newer, smaller) has `var_scale()` and `es_from_var()`
- `src/risk/risk_utils.py` (larger, monolithic) has `var_scale()` with same logic
- Notebooks import from `risk_utils`, not from `var`
- **Status**: Duplicate but not yet consolidated. Marked with TODO for Phase 2.

#### 2. Missing Folder Structure
- No `src/computation/` folder (intended for statistical/analytical functions)
- No `src/pipeline/` folder (intended for ETL and data workflows)
- These will be created in Phase 1 as structure-only (no code moves yet)

#### 3. Config Centralization
- `src/config.py` is minimal (VALUATION_DATE, QUARTER only)
- Hardcoded constants scattered across modules:
  - Regulatory horizons (10, 20 days for VaR scaling)
  - Confidence levels (0.99 for VaR/ES, also 0.95)
  - Other thresholds (leverage limits, LTV, DSCR minimums, etc.)
- **Strategy**: Expand config.py incrementally; do not force adoption unless trivial

#### 4. cache_old/ Deletion
- Obsolete directory: `cache_mixin.py`, `external_store.py`, `fed_store.py`
- No imports found anywhere in codebase or notebooks
- Safe to delete

### Dependencies Check
- No internal imports reference `cache_old`
- No notebooks import from `cache_old`
- Safe to remove in Phase 1

---

## Phase 1 Changes Applied

**Date**: 2026-06-12

### 1. Deleted src/cache_old/
- Removed obsolete caching modules (no imports referenced it)

### 2. Created Folder Structure
- `src/computation/` with `__init__.py`
- `src/pipeline/` with `__init__.py`
- No code moves yet; structure-only for Phase 1

### 3. Expanded src/config.py
Added centralized constants section:
- `VaR_CONFIDENCE_LEVEL = 0.99` (regulatory standard)
- `VAR_HORIZON_BASEL = 10` (Basel III regulatory horizon in days)
- `VAR_HORIZON_UCITS_AIFM = 20` (UCITS/AIFMD standard horizon)
- `ES_CONFIDENCE_LEVEL = 0.99`
- Other regulatory thresholds (leverage, LTV, DSCR) for future adoption

No modules forced to use new config constants yet (Phase 2 migration).

### 4. Added TODO Comments
- `src/risk/var.py`: TODO comment at module level noting duplicate with `var_scale()` in `risk_utils.py`
- `src/risk/risk_utils.py`: TODO comment on `var_scale()` function noting the duplicate

### 5. Validation
- Import checks passed (no broken imports)
- Existing tests run successfully
- All notebooks remain unchanged
- No business logic modified

---

---

## MRS-172 Changes Applied

**Date**: 2026-06-12

### Overview
Extracted canonical VaR computation module to eliminate duplication and establish a single source of truth for pure VaR/ES logic.

### Changes

#### 1. Created src/computation/var.py
New 476-line module containing all pure VaR computation:
- **VaR estimation**: `var_historical()`, `var_parametric()`, `var_scale()`
- **Expected Shortfall**: `es_historical()`, `es_parametric()`, `es_scale()`, `es_from_var()`
- **Backtesting**: `kupiec_test()`, `christoffersen_test()`
- **No dependencies**: Only numpy, pandas, scipy (no DB, files, plotting)

#### 2. Refactored src/risk/var.py
Converted to backward-compatibility shim:
- Imports all functions from `src.computation.var`
- Re-exports under original names
- Preserves existing import paths: `from src.risk.var import var_scale`

#### 3. Refactored src/risk/risk_utils.py
Consolidated with canonical module:
- Imports all VaR/ES/backtest functions from `src.computation.var`
- Removed 430+ lines of duplicate implementations
- Preserved interface: `from src.risk.risk_utils import var_scale` still works
- Default horizons unchanged: `var_scale(horizon=10)` remains the same

#### 4. Updated src/risk/var_backtest.py
Changed import source:
- `kupiec_test`, `christoffersen_test` now imported from `src.computation.var`
- Previously from `src.risk.risk_utils` (which re-exported them)
- No logic changes; same functions called

### Backward Compatibility

All existing imports continue to work:

```python
# Existing code — still works
from src.risk.var import var_scale, es_from_var
from src.risk.risk_utils import (
    var_historical, var_parametric, var_scale,
    es_historical, es_parametric, es_scale,
    kupiec_test, christoffersen_test
)
```

**Numerical consistency**: All function outputs identical to previous implementation.

### Metrics

- Lines added: 476 (canonical VaR module)
- Lines removed: 477 (duplicate implementations)
- Net change: -1 line (but much cleaner organization)
- Functions consolidated: 9 pure VaR/ES/backtest functions
- Modules refactored: 3 (var.py, risk_utils.py, var_backtest.py)

### Validation

✓ All imports work (canonical, backward-compat)
✓ Numerical outputs identical across all import paths
✓ No syntax errors (python3 -m compileall)
✓ VaR, ES, backtesting functions return valid values
✓ Kernel resolution verified (all functions resolve to canonical location)

---

## Next Steps (Phase 2+)

- Migrate modules to use centralized config constants (where safe)
- Move PE and infrastructure analytics into `src/computation/` (with tests)
- Move enrichment and data pipeline into `src/pipeline/`
- Consider stress/liquidity consolidation (if scope permits)
