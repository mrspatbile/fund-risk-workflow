# Architecture Target

## Purpose

This document records the accepted target architecture for `fund-risk-workflow`.

It is not a speculative audit. It should reflect accepted design decisions and implemented or planned refactor direction.

## Source layout

Target source layout:

```text
src/
├── computation/
├── pipeline/
├── reporting/
├── data/
├── risk/
└── ui/
````

## Module responsibilities

### `src/computation/`

Raw calculations only.

Examples:

```text
var.py
stress.py
liquidity.py
leverage.py
attribution.py
```

Rules:

* no database writes
* no file exports
* no notebook rendering
* no regulatory reporting output
* no hidden fund-specific interpretation

### `src/pipeline/`

Reusable workflows that orchestrate data loading, enrichment, and computation.

Examples:

```text
risk_snapshot.py
```

Rules:

* pipelines may call `src.data` and `src.computation`
* pipelines should return structured data
* pipelines should not silently impose fund-specific regulatory rules
* fund-specific rules should be applied in reporting, governance, compliance, or configuration-driven layers

### `src/reporting/`

Board reports, regulatory reports, and disclosure outputs.

Examples:

```text
board_report.py
annex_iv.py
```

Rules:

* regulatory interpretation belongs here or in dedicated regulatory workflow modules
* reporting modules may consume raw metrics from pipelines
* reporting modules may apply limits, thresholds, formatting, and disclosure logic

### `src/data/`

Database access, mock Bloomberg, enrichment, generated data helpers, and reference-data loading helpers.

Examples:

```text
database.py
mock_bloomberg.py
enrichment.py
generate_positions.py
generate_pe_fund.py
generate_infra_fund.py
setup_db.py
```

Rules:

* data modules may read reference data
* data modules may build the SQLite database
* data modules may enrich raw positions
* data modules should not own regulatory interpretation

### `src/risk/`

Legacy compatibility imports, compliance orchestration, and functions that are not yet cleanly moved.

Rules:

* keep backward-compatible imports where useful
* do not move coupled compliance functions without a dedicated ticket
* `risk_utils.py` may remain as a compatibility and orchestration layer

### `src/ui/`

Notebook display helpers, chart helpers, and rendering utilities.

Rules:

* keep rendering separate from computation
* do not place business logic in UI helpers

## Notebook layout

Target notebook layout:

```text
notebooks/
├── fund_risk_monitoring/
├── regulatory_reporting/
├── investor_disclosures/
├── governance_reporting/
└── data_workflows/
```

Do not use:

```text
internal_risk/
exploratory/
```

### Notebook folder meaning

`fund_risk_monitoring/`

Fund-specific monitoring notebooks.

Examples:

```text
aifm_hedge_fund.ipynb
aifm_private_debt.ipynb
aifm_real_estate.ipynb
ucits_balanced.ipynb
aifm_pe_buyout.ipynb
aifm_infra_core.ipynb
```

`regulatory_reporting/`

Regulatory reporting workflows.

Examples:

```text
aifmd_annex_iv.ipynb
ucits_global_exposure.ipynb
emir_controls.ipynb
```

`investor_disclosures/`

Investor-facing disclosure workflows.

Examples:

```text
priips_kid.ipynb
sfdr_disclosure_monitoring.ipynb
```

`governance_reporting/`

Board and committee reporting workflows.

Examples:

```text
board_risk_report.ipynb
risk_committee_pack.ipynb
exception_report.ipynb
```

`data_workflows/`

Technical notebooks explaining the data layer.

Examples:

```text
01_data_layer_workflow.ipynb
```

## Reference data architecture

Target reference-data layout:

```text
reference_data/
├── funds/
│   ├── fund_registry.json
│   └── <fund_id>/
│       ├── fund_profile.json
│       ├── risk_policy.json
│       ├── position_specs.json
│       └── asset_specs.json
├── regulation/
│   ├── ucits_regulatory_framework.json
│   ├── aifmd_annex_iv_framework.json
│   ├── priips_kid_framework.json
│   └── sfdr_disclosure_framework.json
├── instruments/
├── portfolios/
├── counterparties/
└── investors/
```

## Fund registry

`reference_data/funds/fund_registry.json`

Purpose:

* operational list of funds
* tells setup or loaders which funds exist
* should not contain detailed fund characteristics

Example:

```json
{
  "registry_version": "1.0",
  "funds": [
    "AIFM_HedgeFund",
    "AIFM_PrivateDebt",
    "AIFM_RealEstate",
    "AIFM_PE_Buyout",
    "AIFM_Infra_Core",
    "UCITS_Balanced"
  ]
}
```

## Fund profile

`reference_data/funds/<fund_id>/fund_profile.json`

Purpose:

* static fund facts
* regulatory classification flags
* high-level data model classification

Typical fields:

```text
fund_id
fund_name
fund_type
strategy
currency
domicile
regulator
inception_date
target_nav_eur
regulatory_classification
data_model
```

`regulatory_classification` may include:

```text
is_ucits
is_aif
is_annex_iv_reportable
is_priips_kid_required
is_sfdr_article_6
is_sfdr_article_8
is_sfdr_article_9
```

Unknown values should remain `null`.

Do not put regulatory limits in `fund_profile.json`.

## Fund risk policy

`reference_data/funds/<fund_id>/risk_policy.json`

Purpose:

* fund-specific internal risk framework
* monitoring thresholds
* redemption terms
* liquidity profile
* valuation frequency
* modelling choices

Typical fields:

```text
redemption_terms
notice_period_days
lockup_days
liquidity_profile
valuation_frequency
internal leverage limits
internal concentration limits
direct property monitoring flags
covenant monitoring flags
stress scenario choices
VaR usage and parameters where explicitly applicable
```

Unknown values should remain `null` or absent.

Do not create fund-level `regulatory_limits.json`.

Do not duplicate central regulatory rules inside `risk_policy.json`.

## Central regulatory frameworks

Regulatory rules belong in:

```text
reference_data/regulation/
```

### UCITS

File:

```text
reference_data/regulation/ucits_regulatory_framework.json
```

Purpose:

* UCITS global exposure framework
* commitment approach
* absolute VaR
* relative VaR
* 5/10/40 concentration rule
* OTC counterparty limits
* borrowing limits
* eligible asset notes

UCITS regulatory values should be centralised here, not duplicated in the UCITS fund policy.

### AIFMD Annex IV

File:

```text
reference_data/regulation/aifmd_annex_iv_framework.json
```

Purpose:

* AIFMD Annex IV reporting framework
* leverage calculation disclosure
* liquidity profile reporting
* investor concentration disclosure
* unfunded commitment reporting where applicable

Use this wording:

```text
Delegated Regulation (EU) 231/2013 Article 110 and Annex IV reporting template
```

Do not use:

```text
AIFMD Annex VI reporting
```

AIFMD does not prescribe one universal VaR model, confidence level, holding period, lookback window, or concentration limit for all AIFs.

### PRIIPs KID

File:

```text
reference_data/regulation/priips_kid_framework.json
```

Purpose:

* PRIIPs KID framework
* Summary Risk Indicator (SRI)
* performance scenarios
* cost disclosure
* KID scope

Use:

```text
Summary Risk Indicator (SRI)
```

Do not use:

```text
Synthetic Risk Indicator
```

### SFDR

File:

```text
reference_data/regulation/sfdr_disclosure_framework.json
```

Purpose:

* SFDR Article 6 / 8 / 9 classification
* PAI disclosure structure
* pre-contractual disclosure logic
* periodic disclosure logic

Do not reduce SFDR to ESG score.

ESG scores may be raw inputs, but SFDR interpretation requires explicit mapping.

## Fund treatment

### Position-based AIFs

Position-based AIFs may share a risk snapshot pipeline where appropriate.

Examples:

```text
AIFM_HedgeFund
AIFM_PrivateDebt
```

The pipeline should compute raw metrics, not automatically apply fund-specific regulatory interpretation.

### Real estate

`AIFM_RealEstate` is a mixed fund.

It may contain:

```text
direct properties
listed REITs
FX hedge
cash
```

Do not blindly treat the whole fund as a liquid VaR portfolio.

Do not blindly move all holdings into `re_*` tables.

Future treatment should likely separate:

```text
direct property sleeve
listed REIT sleeve
FX hedge sleeve
cash sleeve
```

Direct-property appraisal and real estate risk metrics should be distinguished from daily traded-security metrics.

`AIFM_RealEstate` is accepted as closed-ended for fund-level policy configuration, but the detailed real estate schema remains a future design decision.

### Private equity

Private equity uses a specialised data model.

It should not be forced into a standard liquid VaR-based pipeline.

Accepted closed-ended fund:

```text
AIFM_PE_Buyout
```

### Infrastructure

Infrastructure uses a specialised data model.

It should not be forced into a standard liquid VaR-based pipeline.

Accepted closed-ended fund:

```text
AIFM_Infra_Core
```

### UCITS

UCITS may reuse computation functions.

UCITS regulatory interpretation must remain separate.

UCITS global exposure and related regulatory rules should be centralised in:

```text
reference_data/regulation/ucits_regulatory_framework.json
```

## Risk calculation rule

The repository has reusable calculators.

Risk is not computed automatically for every fund or every asset.

Notebooks and pipelines decide:

* which calculator to call
* for which fund
* for which asset sleeve
* with which assumptions

Do not assume VaR applies to every fund or every asset class.

Do not automatically apply VaR to:

```text
real estate
private equity
infrastructure
private debt
```

## Risk snapshot pipeline target

Future module:

```text
src/pipeline/risk_snapshot.py
```

Future function:

```python
def compute_risk_snapshot(
    engine,
    fund_id: str,
    valuation_date: str = "2026-05-13",
) -> dict:
    ...
```

Purpose:

* compute raw point-in-time metrics
* return structured results
* support reporting and notebooks later

Should include where appropriate:

```text
fund_id
fund label
strategy
NAV
MTD / YTD performance
VaR
Expected Shortfall
rolling VaR
stress metrics
leverage metrics
liquidity buckets
net liquidity
```

Should not:

* apply fund-specific regulatory interpretation
* apply all limits automatically
* force all fund types into the same model
* edit notebooks as part of the pipeline ticket

## Reporting and disclosure separation

Regulatory reporting:

```text
AIFMD Annex IV
UCITS global exposure monitoring
EMIR controls
regulatory reporting controls
```

Investor disclosures:

```text
PRIIPs KID
SFDR disclosures
investor reporting packs
```

Governance reporting:

```text
board risk reports
risk committee packs
exception reports
```

## Validation expectations

For code changes:

```text
python3 -m compileall src
```

Run relevant tests.

For documentation-only changes:

```text
git diff --stat
```

For notebook-related changes:

* confirm notebooks were changed only if the ticket allowed it
* avoid changing notebook outputs unless needed
* keep notebook refactors ticket-scoped

## Current issue order

Accepted issue order:

```text
MRS-178  Add Claude refactor playbook - done
MRS-179  Reorganize reference data and document the data workflow - done
MRS-194  Add fund-level reference data and risk policy configuration
MRS-180  Create risk snapshot pipeline for position-based AIFs
MRS-181  Refactor board report to use risk snapshot pipeline
MRS-182  Reorganize notebooks into purpose-based folders
MRS-183  Align hedge fund risk monitoring notebook with canonical modules
MRS-184  Align private debt risk monitoring notebook with canonical flow
MRS-185  Align real estate risk monitoring notebook with canonical flow
MRS-186  Review UCITS notebook for UCITS-specific risk logic
MRS-187  Review private equity notebook for alternative asset workflow
MRS-188  Review infrastructure notebook for alternative asset workflow
MRS-189  Create AIFMD Annex IV reporting notebook for all AIFs
MRS-190  Create UCITS global exposure monitoring notebook
MRS-191  Create SFDR disclosure monitoring notebook
MRS-192  Create PRIIPs KID generation notebook for retail-distributed funds
MRS-193  Add project architecture README for reviewers
```

## Non-goals

Do not:

* force all funds into one model
* create unused abstractions
* hide regulatory assumptions in computation modules
* duplicate regulatory rules per fund
* make `VALUATION_DATE` dynamic
* introduce production-only patterns from other projects

