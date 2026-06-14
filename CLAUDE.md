# fund-risk-workflow

## What this project is

`fund-risk-workflow` is a structured finance and risk research project.

It simulates the workflow of a risk analyst working with UCITS and AIFs under Luxembourg / CSSF-style oversight. The project is intentionally built to look and feel like a small risk platform, while remaining honest about its limits:

- it is not a production system
- the valuation date is static
- the data is controlled and partly simulated
- portfolio positions are mostly fixed by design
- valuation engines are simplified
- notebooks remain part of the research workflow

The goal is to show practical understanding of:

- fund data workflows
- risk analytics
- regulatory interpretation
- reporting workflows
- data enrichment
- Python package organisation
- notebook-to-code refactoring

This repository should be understandable for technical reviewers, ManCo stakeholders, and consulting or risk technology hiring managers.

## Core design principle

Keep a clear separation between:

- raw computation
- data access and enrichment
- workflow orchestration
- fund risk monitoring
- regulatory reporting
- investor disclosures
- governance reporting
- notebook rendering

Do not create unnecessary abstraction. This is a structured research project, not a production platform.

## Current architecture direction

Use this structure as the guiding model:

```text
src/
├── computation/
├── pipeline/
├── reporting/
├── data/
├── risk/
└── ui/
```

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

These modules should not perform database writes, file exports, notebook rendering, or regulatory interpretation.

### `src/pipeline/`

Reusable workflows that orchestrate data loading, enrichment, and computation.

Examples:

```text
risk_snapshot.py
```

Pipelines should produce raw or structured outputs. They should not silently impose fund-specific regulatory rules unless that is explicitly in scope.

### `src/reporting/`

Board reports, regulatory reports, and disclosure outputs.

Examples:

```text
board_report.py
annex_iv.py
```

Regulatory interpretation belongs here or in dedicated regulatory workflow modules, not inside raw computation.

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

### `src/risk/`

Legacy compatibility imports, compliance orchestration, and functions that are not yet cleanly moved.

`risk_utils.py` may continue to exist as a compatibility and orchestration layer. Do not move remaining coupled functions unless a ticket explicitly asks for it.

### `src/ui/`

Notebook display helpers, chart helpers, and rendering utilities.

## Current notebook structure direction

Use purpose-based folders:

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

Use `data_workflows/` for technical notebooks that explain:

- database access
- mock Bloomberg / market data
- enrichment
- reference data
- how data feeds the computation layer

## Static valuation date

`VALUATION_DATE` is intentionally static:

```text
2026-05-13
```

Do not make it dynamic.

Do not introduce date-range logic unless a ticket explicitly asks for it.

All analytics are point-in-time by design.

## Position behaviour

Portfolio positions are intentionally stable in the mock dataset, except where a specialised generator explicitly creates a different behaviour, such as PE cash flows.

Do not introduce live portfolio-update logic unless a ticket explicitly asks for it.

## Reference data direction

Reference data should be explicit and fund-level where appropriate.

Target structure:

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

### `fund_registry.json`

Operational list only.

It tells the system which funds exist and should be loaded.

It should not contain detailed fund characteristics.

### `fund_profile.json`

Static fund facts and regulatory classification flags.

Examples:

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
is_ucits
is_aif
is_annex_iv_reportable
is_priips_kid_required
is_sfdr_article_6
is_sfdr_article_8
is_sfdr_article_9
```

### `risk_policy.json`

Fund-specific internal risk framework and monitoring choices.

Examples:

```text
redemption_terms
notice_period_days
lockup_days
liquidity_profile
valuation_frequency
internal leverage limits
internal concentration limits
LTV or covenant monitoring thresholds
stress scenario choices
VaR usage and parameters where explicitly applicable
```

### `reference_data/regulation/`

Central regulatory framework files.

Do not create fund-level `regulatory_limits.json`.

Regulatory rules should be centralised by framework and triggered by fund-level flags.

## Regulatory distinction

Do not treat all funds the same.

### AIFMD

AIFMD does not prescribe one universal VaR limit, confidence level, holding period, lookback window, or concentration limit for all AIFs.

For AIFs, methodology choices must be adequate, defined, documented, and supported by the fund strategy, risk profile, liquidity profile, and complexity.

AIFMD Annex IV is a reporting framework. It should be treated as a ManCo / AIFM-level reporting process covering all relevant AIFs.

Use:

```text
reference_data/regulation/aifmd_annex_iv_framework.json
```

for central Annex IV reporting structure and reporting-field logic.

Use this wording for Annex IV references:

```text
Delegated Regulation (EU) 231/2013 Article 110 and Annex IV reporting template
```

Do not use “AIFMD Annex VI reporting”.

### UCITS

UCITS is different.

UCITS global exposure, commitment approach, absolute VaR, relative VaR, and related limits or model assumptions must be treated as UCITS-specific regulatory logic.

Use:

```text
reference_data/regulation/ucits_regulatory_framework.json
```

for central UCITS rules and parameters.

Do not duplicate UCITS regulatory limits inside a fund-level `risk_policy.json`.

### PRIIPs

PRIIPs is a disclosure framework.

It relates to KID production, Summary Risk Indicator (SRI), performance scenarios, and costs.

Do not mix PRIIPs logic into AIFMD risk management logic.

Use:

```text
reference_data/regulation/priips_kid_framework.json
```

for central PRIIPs KID / SRI logic.

### SFDR

SFDR is a regulatory disclosure framework.

It should not be reduced to an ESG score.

Current ESG indicators should be treated as raw ESG or sustainability-risk indicators unless explicitly mapped to SFDR concepts such as:

- Article 6
- Article 8
- Article 9
- PAIs
- pre-contractual disclosures
- website disclosures
- periodic disclosures

Use:

```text
reference_data/regulation/sfdr_disclosure_framework.json
```

for central SFDR disclosure logic.

### EMIR

EMIR is relevant where funds use derivatives.

It should be handled as a dedicated derivatives regulatory reporting and controls workflow covering:

- derivatives reporting checks
- counterparty classification checks
- clearing obligation checks where applicable
- risk mitigation controls for non-cleared OTC derivatives
- collateral / margin workflow checks where applicable
- reconciliation and data quality checks

Do not mix EMIR logic into generic VaR, AIFMD Annex IV, UCITS global exposure, PRIIPs, or SFDR logic.

## Risk calculation rule

The repository has reusable calculators.

Risk is not computed automatically for every fund or every asset.

Notebooks and pipelines decide:

- which calculator to call
- for which fund
- for which asset sleeve
- with which assumptions

Do not assume that VaR applies to every fund or every asset class.

Do not automatically apply VaR to:

- real estate
- private equity
- infrastructure
- private debt

For mixed funds, separate the sleeves before interpreting the risk metrics.

For real estate, distinguish:

```text
direct properties
listed REITs
FX hedge
cash
```

Direct properties should not be treated as daily traded securities merely because the current mock data contains daily position snapshots.

Listed REITs, FX, and cash may still be treated as position-style holdings where appropriate.

## Fund treatment

Position-based AIFs may share a risk snapshot pipeline where appropriate.

Examples:

```text
AIFM_HedgeFund
AIFM_PrivateDebt
```

`AIFM_RealEstate` is currently a mixed fund and should not be blindly treated as a pure liquid position-based fund. It may eventually need a sleeve-based workflow.

UCITS may reuse computation functions, but UCITS regulatory interpretation must remain separate.

Private equity and infrastructure have different data models and should not be forced into a standard VaR-based pipeline.

The following funds are treated as closed-ended for fund-level policy configuration:

```text
AIFM_PE_Buyout
AIFM_Infra_Core
AIFM_RealEstate
```

## Reporting and disclosure distinction

Regulatory reporting includes:

```text
AIFMD Annex IV
UCITS global exposure monitoring
EMIR derivatives reporting and controls
regulatory reporting controls
```

Investor disclosures include:

```text
PRIIPs KID
SFDR disclosures
investor reporting packs
```

Governance reporting includes:

```text
board risk reports
risk committee packs
exception reports
```

AIFMD Annex IV reporting should be treated as a ManCo / AIFM-level process covering all relevant AIFs, not as a hedge fund notebook output.

SFDR disclosure monitoring should be cross-fund.

PRIIPs KID generation should cover only funds distributed to retail investors.

## How we work together

Do not make changes without checking with the user first.

Preferred flow for every task:

1. Read the relevant Linear issue before touching anything.
2. Explain your understanding of the task and proposed approach.
3. Wait for go-ahead before writing or changing code.
4. Make changes one logical step at a time.
5. After each step, explain what changed and why.
6. At the end, list changed files, validation performed, risks, and open questions.

The user manages commits manually in VS Code.

Do not commit.

Do not push.

Do not stage files unless explicitly asked.

Do not provide git commands unless explicitly asked.

Do not add Claude or any AI tool as co-author.

## Things to never do without explicit permission

- refactor across multiple files in one go
- change data structures or schemas
- delete or rename anything
- touch `.venv/`
- touch environment configuration
- create new Linear tickets
- edit notebooks unless the ticket says so
- change business logic unless the ticket says so
- change numerical outputs unless the ticket says so
- create empty modules
- move old notebook logic blindly into production code

## Validation expectations

For code changes, run:

```text
python3 -m compileall src
```

Run relevant tests where available.

For notebook-related work, confirm no notebooks were modified unless the ticket explicitly allowed it.

For documentation-only work, show:

```text
git diff --stat
```

## Code style

- PEP 8 throughout.
- Type hints on public functions and methods.
- Docstrings on public classes and functions.
- State non-obvious conventions in docstrings, especially percent vs decimal and annualised vs daily.
- No new dependencies without flagging first.
- Prefer readable names and explicit function signatures.

## Current Linear issues

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

## Scope boundary

This project is a structured learning and research environment.

There is a separate project, `quant-risk-engine`, focused on production-grade OOP design, QuantLib integration, and regulatory capital calculations.

Do not import architectural patterns from that project unless explicitly requested.

If something works and is clear, it is good enough here.
