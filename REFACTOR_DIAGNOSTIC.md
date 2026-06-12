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

## Next Steps (Phase 2+)

- Consolidate VaR logic (keep one `var_scale`, import it in the other)
- Migrate modules to use centralized config constants (where safe)
- Move PE and infrastructure analytics into `src/computation/` (structure-only for now)
- Move enrichment and data pipeline into `src/pipeline/`
