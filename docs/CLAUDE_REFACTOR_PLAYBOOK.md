# Claude Refactor Playbook

## Project context

This repository is `fund-risk-workflow`.

The goal is to make the project clean, professional, and understandable for technical reviewers, ManCo stakeholders, and consulting or risk technology managers.

The repo should show clear separation between:

* raw computation
* data access and enrichment
* workflow orchestration
* fund risk monitoring
* regulatory reporting
* investor disclosures
* notebook rendering

The refactor must remain practical. Do not create unnecessary layers, empty modules, or broad abstractions that are not used.

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

`src/computation/` contains raw calculations only.

Examples:

```text
var.py
stress.py
liquidity.py
leverage.py
attribution.py
```

`src/pipeline/` contains reusable workflows that orchestrate data loading, enrichment, and computation.

`src/reporting/` contains board reports, regulatory reports, and disclosure outputs.

`src/data/` contains database access, mock Bloomberg, enrichment, generated data helpers, and reference-data loading helpers.

`src/risk/` may retain legacy compatibility imports, compliance orchestration, and functions that are not yet cleanly moved.

`src/ui/` contains notebook display helpers, charts, and rendering utilities.

## Reference data direction

Reference data should be explicit and fund-level where appropriate.

Use this target structure:

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
└── portfolios/
```

`fund_registry.json` is operational only. It tells the system which funds exist and should be loaded.

`fund_profile.json` contains static fund facts and regulatory classification flags.

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

`risk_policy.json` contains the fund’s own internal risk framework, monitoring thresholds, valuation terms, redemption terms, liquidity profile, and modelling choices.

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

Do not create fund-level `regulatory_limits.json`.

Regulatory rules should be centralised by framework in `reference_data/regulation/`.

Fund-level files should contain regulatory flags that trigger the relevant central framework.

## Notebook structure direction

Use purpose-based notebook folders:

```text
notebooks/
├── fund_risk_monitoring/
├── regulatory_reporting/
├── investor_disclosures/
├── governance_reporting/
└── data_workflows/
```

Do not use `internal_risk/`.

Do not use `exploratory/`.

Use `data_workflows/` for technical notebooks that explain database access, Bloomberg/mock Bloomberg, enrichment, reference data, and how data feeds the computation layer.

## Regulatory distinction

Do not treat all funds the same.

AIFMD does not prescribe one universal VaR limit, confidence level, holding period, or lookback window for all AIFs. For AIFs, methodology choices must be adequate, defined, documented, and supported by the fund strategy, risk profile, liquidity profile, and complexity. Market practice can be documented, but it must not be presented as a universal statutory AIFMD rule.

AIFMD Annex IV is a reporting framework. Treat it as a ManCo / AIFM-level reporting process covering all relevant AIFs.

Use `reference_data/regulation/aifmd_annex_iv_framework.json` for central Annex IV reporting structure and reporting-field logic.

UCITS is different. UCITS global exposure, commitment approach, absolute VaR, relative VaR, and related limits or model assumptions must be treated as UCITS-specific regulatory logic.

Use `reference_data/regulation/ucits_regulatory_framework.json` for central UCITS rules and parameters.

PRIIPs is a disclosure framework. It relates to KID production, Summary Risk Indicator, performance scenarios, and costs. Do not mix PRIIPs logic into AIFMD risk management logic.

Use `reference_data/regulation/priips_kid_framework.json` for central PRIIPs KID / SRI logic.

SFDR is a regulatory disclosure framework. It should not be reduced to an ESG score. Current ESG indicators should be treated as raw ESG or sustainability-risk indicators unless explicitly mapped to SFDR concepts such as Article 6, Article 8, Article 9, PAIs, pre-contractual disclosures, website disclosures, or periodic disclosures.

Use `reference_data/regulation/sfdr_disclosure_framework.json` for central SFDR disclosure logic.

EMIR is relevant where funds use derivatives. It should be handled as a derivatives regulatory reporting and controls workflow, covering items such as:

* derivatives reporting checks
* counterparty classification checks
* clearing obligation checks where applicable
* risk mitigation controls for non-cleared OTC derivatives
* collateral / margin workflow checks where applicable
* reconciliation and data quality checks

Do not mix EMIR logic into generic VaR, AIFMD Annex IV, UCITS global exposure, PRIIPs, or SFDR logic. EMIR may use shared derivative exposure data, but regulatory interpretation should live in a dedicated reporting or controls workflow.

## Risk calculation rule

The repository has reusable calculators.

Risk is not computed automatically for every fund or every asset.

Notebooks and pipelines decide which calculator to call, for which fund, for which sleeve, and with which assumptions.

Do not assume VaR applies to every fund or every asset class.

Do not automatically apply VaR to real estate, private equity, infrastructure, or private debt.

For mixed funds, separate the sleeves before interpreting the risk metrics.

Example for real estate:

```text
direct properties
listed REITs
FX hedges
cash
```

Direct properties should not be treated as daily traded securities merely because the current mock data contains daily position snapshots.

Listed REITs, FX, and cash may still be treated as position-style holdings where appropriate.

## Hedge fund notebook reference rule

The hedge fund notebook may be used as a reference for:

* notebook layout
* clean output structure
* rendering style
* use of canonical computation modules
* section flow for position-based risk monitoring

Do not copy hedge fund-specific limits, assumptions, or regulatory treatment into UCITS, PE, infrastructure, private debt, or real estate notebooks.

Shared workflow and fund-specific rules must be separated.

## Fund treatment

Position-based AIFs may share a risk snapshot pipeline where appropriate.

Examples:

```text
aifm_hedge_fund
aifm_private_debt
```

`aifm_real_estate` is currently a mixed fund and should not be blindly treated as a pure liquid position-based fund. It may eventually need a sleeve-based workflow.

UCITS may reuse computation functions, but UCITS regulatory interpretation must remain separate.

Private equity and infrastructure have different data models and should not be forced into a standard VaR-based pipeline.

## Reporting and disclosure distinction

Regulatory reporting includes items such as:

```text
AIFMD Annex IV
UCITS global exposure monitoring
EMIR derivatives reporting and controls
regulatory reporting controls
```

Investor disclosures include items such as:

```text
PRIIPs KID
SFDR disclosures
investor reporting packs
```

Governance reporting includes items such as:

```text
board risk reports
risk committee packs
exception reports
```

AIFMD Annex IV reporting should be treated as a ManCo / AIFM-level process covering all relevant AIFs, not as a hedge fund notebook output.

SFDR disclosure monitoring should be cross-fund.

PRIIPs KID generation should cover only funds distributed to retail investors.

EMIR regulatory controls should be treated separately from AIFMD, UCITS, PRIIPs, and SFDR.

## Work rules

For every ticket:

1. Do not edit notebooks unless the ticket explicitly says to edit notebooks.
2. Do not change business logic unless the ticket explicitly says to change business logic.
3. Do not change numerical outputs unless the ticket explicitly says to do so.
4. Do not rename `reporting/` to `output/`.
5. Do not create empty modules.
6. Do not create large architecture changes without clear use.
7. Preserve backward-compatible imports where possible.
8. Keep each change small and ticket-scoped.
9. Show validation output before saying the ticket is complete.
10. Do not commit.
11. Do not push.
12. Do not stage files unless explicitly asked.
13. Do not add Claude or any AI tool as co-author.
14. Do not suggest long commit messages.
15. Do not provide git add commands unless explicitly asked.
16. At the end, list changed files, validation performed, risks, and open questions.

The user will handle commits manually in VS Code.

## Validation expectations

For code changes, run:

```text
python3 -m compileall src
```

Run relevant tests where available.

When moving functions, compare old and new import paths with small deterministic examples.

For notebook-related work, confirm no notebooks were modified unless the ticket explicitly allowed it.

For documentation-only work, show `git diff --stat`.

## Preferred implementation style

Prefer:

* small modules
* readable names
* explicit function signatures
* clear comments where methodology assumptions exist
* raw metrics separated from regulatory interpretation
* simple pipelines that are actually used
* fund-level configuration where rules are fund-specific
* central regulatory configuration where rules come from regulation

Avoid:

* cosmetic folder moves without benefit
* broad rewrites
* hidden regulatory assumptions
* forcing all fund types into the same model
* moving old notebook logic blindly into production code
* creating generic abstractions that make the repo harder to understand
* duplicating regulatory limits in each fund folder

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

## Commit Rule

Never commit.

Never push.

Never stage files.

Never provide git add commands unless explicitly requested.

Never add Claude or any AI tool as co-author.

The user manages commits manually through VS Code.