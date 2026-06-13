# Refactor Log

This file records implemented refactor changes only.

## MRS-171: Refactor Phase 1 foundation cleanup

### Changed
- Removed obsolete `src/cache_old/`.
- Created `src/computation/`.
- Created `src/pipeline/`.
- Expanded `src/config.py` with central risk and regulatory constants.
- Added TODO notes for duplicated VaR logic.

### Validation
- Imports passed.
- Existing tests passed.
- Notebooks were unchanged.
- No business logic was changed.

---

## MRS-172: Extract canonical VaR computation module

### Changed
- Created `src/computation/var.py`.
- Refactored `src/risk/var.py` as a backward-compatible shim.
- Refactored `src/risk/risk_utils.py` to import VaR, ES, and backtesting functions from `src.computation.var`.
- Updated `src/risk/var_backtest.py` to use the canonical VaR module.

### Canonical module
`src/computation/var.py`

### Backward-compatible imports preserved
- `src.risk.var`
- `src.risk.risk_utils`

### Validation
- Imports passed.
- Numerical smoke checks passed.
- `python3 -m compileall src` passed.

---

## MRS-173: Extract stress and liquidity computation modules

### Changed
- Created `src/computation/stress.py`.
- Created `src/computation/liquidity.py`.
- Refactored `src/risk/risk_utils.py` to re-export stress and liquidity functions from the canonical modules.

### Canonical modules
- `src/computation/stress.py`
- `src/computation/liquidity.py`

### Backward-compatible imports preserved
- `src.risk.risk_utils`

### Validation
- Imports passed.
- Relevant `tests/test_risk_utils.py` coverage confirmed.
- `python3 -m compileall src` passed.
- Relevant tests passed.

---

## MRS-174: Extract leverage computation module

### Changed
- Created `src/computation/leverage.py`.
- Refactored `src/risk/risk_utils.py` to re-export `compute_leverage`.

### Canonical module
`src/computation/leverage.py`

### Backward-compatible imports preserved
- `src.risk.risk_utils.compute_leverage`

### Validation
- Imports passed.
- Numerical smoke checks passed.
- `python3 -m compileall src` passed.

---

## MRS-175: Extract P&L attribution computation module

### Changed
- Created `src/computation/attribution.py`.
- Refactored `src/risk/risk_utils.py` to re-export `compute_pnl_attribution`.

### Canonical module
`src/computation/attribution.py`

### Backward-compatible imports preserved
- `src.risk.risk_utils.compute_pnl_attribution`

### Validation
- Imports passed.
- Relevant tests passed.
- `python3 -m compileall src` passed.

---

## MRS-178: Add Claude refactor playbook

### Changed
- Added `docs/CLAUDE_REFACTOR_PLAYBOOK.md`.

### Purpose
Provides reusable project rules for Claude sessions, including architecture direction, regulatory distinctions, notebook structure, work rules, and validation expectations.

---

## MRS-179: Add Bloomberg tickers for cash positions

### Changed
- Added Bloomberg-style currency tickers for cash positions in reference data.
- Updated `reference_data/ticker_map.json`.

### Example
- `Cash EUR` now maps to `EUR Curncy`.

### Purpose
Avoid blank tickers for cash positions while preserving `asset_class = Cash`.

### Validation
- JSON files valid.
- Mock Bloomberg handles currency tickers.
- Enrichment keeps non-applicable fields as `NaN`.
