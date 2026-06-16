"""
Project-level configuration for notebook runs and analytics.

Valuation Period Parameters
============================
These are specific to the current analysis run. Update to change valuation
or reporting dates.

VALUATION_DATE is intentionally static. Do not make it dynamic.
All analytics are point-in-time by design.
"""

# ================================================================
# Valuation Period Parameters
# ================================================================

# Valuation date (static, intentional)
VALUATION_DATE = '2026-05-13'

# Reporting period (quarterly)
QUARTER = '2026-03-31'


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


# ================================================================
# Regulatory Thresholds
# ================================================================


# Real estate thresholds
LTV_WARNING_THRESHOLD = 0.60        # Loan-to-value warning level
LTV_STRESS_THRESHOLD = 0.75         # LTV stress testing threshold

# Infrastructure thresholds
DSCR_MINIMUM = 1.25                 # Debt service coverage ratio minimum
DSCR_WARNING = 1.50                 # DSCR warning level
