"""
Project-level configuration for notebook runs.

These are valuation period parameters specific to the current analysis run.
Update these to run analysis for a different valuation date or reporting period.

Hard constraint (per CLAUDE.md):
    VALUATION_DATE is intentionally static. Do not make it dynamic.
    All analytics are point-in-time by design.
"""

# Valuation date (static, intentional)
VALUATION_DATE = '2026-05-13'

# Reporting period (quarterly)
QUARTER = '2026-03-31'
