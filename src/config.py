"""
Project-level configuration for fund risk analysis.

Date Semantics
==============
- REFERENCE_DATE: "As of" date for all computations (fund snapshot date)
                  Input parameter that drives all risk calculations
                  Example: 2026-03-31 (Q1 reporting period)
                  Intentionally static. Do not make dynamic.

- COMPUTATION_DATE: Audit trail - when analysis was actually performed
                    Metadata only, does not affect calculations
                    Set to None to use today's date at runtime

- QUARTER: Reporting quarter in YYYY-MM-DD format (quarter end date)
           Usually same as REFERENCE_DATE for quarterly reporting

All computations (VaR, attribution, liquidity, etc.) use REFERENCE_DATE.
All plots and reports show REFERENCE_DATE, not COMPUTATION_DATE.
"""

# ================================================================
# REFERENCE_DATE: Primary date for all computations (STATIC)
# ================================================================
# This is the "as of" date. All risk calculations use this date.
# It is intentionally static and point-in-time by design.
#
# Examples:
# - 2026-03-31 for Q1 Annex IV reporting
# - 2026-06-30 for Q2 reporting
#
# Do NOT make this dynamic. Each reporting period has a fixed reference date.

REFERENCE_DATE = '2026-03-31'

# For backward compatibility (deprecated)
VALUATION_DATE = REFERENCE_DATE

# ================================================================
# COMPUTATION_DATE: Audit trail (metadata, optional)
# ================================================================
# When this analysis was actually performed.
# Does not affect calculations, only used for audit/logging.
#
# Set to None to use today's date at runtime.
# Set to specific date for reproducible runs.

COMPUTATION_DATE = None

# ================================================================
# QUARTER: Reporting period
# ================================================================
# Reporting quarter in YYYY-MM-DD format (quarter end date).
# Usually same as REFERENCE_DATE for quarterly reporting.

QUARTER = REFERENCE_DATE


# ================================================================
# Risk Management Constants
# ================================================================

# # Value-at-Risk (VaR) confidence levels
# VaR_CONFIDENCE_LEVEL = 0.99  # Standard regulatory confidence for VaR/ES

# # VaR holding periods
# VAR_HORIZON_BASEL = 10          # Basel III regulatory horizon (days)
# VAR_HORIZON_UCITS_AIFM = 20    # UCITS and AIFMD standard horizon (days)

# # Expected Shortfall (ES)
# ES_CONFIDENCE_LEVEL = 0.99

# Liquidity bucket display order
LIQUIDITY_BUCKET_ORDER = [
    "1 day",
    "2-7 days",
    "8-30 days",
    "31-90 days",
    "91-365 days",
    "> 1 year",
]


