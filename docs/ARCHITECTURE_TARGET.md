# Architecture Target

## Purpose

This repository should present a clean fund risk workflow for technical reviewers, ManCo stakeholders, consulting reviewers, and risk technology hiring managers.

The architecture should separate:

- raw computation
- data access and enrichment
- workflow orchestration
- fund risk monitoring
- regulatory reporting
- investor disclosures
- notebook rendering

---

## Source code structure

```text
src/
├── computation/
├── pipeline/
├── reporting/
├── data/
├── risk/
└── ui/
```

## Responsibilities

### `src/computation/`

Raw calculations only.

Current examples:

```text
var.py
stress.py
liquidity.py
leverage.py
attribution.py
```

Rules:

- no database access
- no file output
- no notebook display
- no regulatory report formatting
- deterministic functions where possible

### `src/pipeline/`

Reusable workflows.

Examples:

```text
risk_snapshot.py
backtest.py
pre_trade.py
```

Rules:

- orchestrates data loading, enrichment, and computation
- returns structured objects or dictionaries
- does not render notebooks
- does not generate final regulatory documents unless the ticket explicitly requires it

### `src/reporting/`

Reports, regulatory outputs, and disclosures.

Examples:

```text
board_report.py
annex_iv.py
ucits_monitoring.py
priips_kid.py
sfdr.py
```

Rules:

- applies interpretation and formatting
- can call `src.pipeline`
- should not contain low-level computation logic

### `src/data/`

Database, enrichment, mock Bloomberg, and data generation.

Examples:

```text
database.py
enrichment.py
mock_bloomberg.py
generate_*.py
```

### `src/risk/`

Legacy compatibility and coupled risk workflows.

This package may keep:

- backward-compatible imports
- pre-trade compliance orchestration
- functions not yet safely moved
- DB/file-coupled risk workflows

### `src/ui/`

Notebook rendering, chart helpers, and display utilities.

---

## Notebook structure

```text
notebooks/
├── fund_risk_monitoring/
├── regulatory_reporting/
├── investor_disclosures/
├── governance_reporting/
└── data_workflows/
```

### `fund_risk_monitoring/`

Fund-level risk monitoring notebooks.

Examples:

```text
aifm_hedge_fund_risk_monitoring.ipynb
aifm_private_debt_risk_monitoring.ipynb
aifm_real_estate_risk_monitoring.ipynb
aifm_infrastructure_risk_monitoring.ipynb
aifm_private_equity_risk_monitoring.ipynb
ucits_risk_monitoring.ipynb
```

### `regulatory_reporting/`

Regulatory workflows.

Examples:

```text
aifmd_annex_iv_reporting.ipynb
ucits_global_exposure_monitoring.ipynb
regulatory_reporting_controls.ipynb
```

### `investor_disclosures/`

Investor and public disclosure workflows.

Examples:

```text
sfdr_disclosure_monitoring.ipynb
priips_kid_generation.ipynb
investor_disclosure_controls.ipynb
```

### `governance_reporting/`

Board and senior management reporting.

Example:

```text
board_risk_report.ipynb
```

### `data_workflows/`

Technical data workflow notebooks.

Example:

```text
01_database_and_bloomberg.ipynb
```

Purpose:

- database creation and access
- SQL examples
- query helper functions
- enrichment workflow
- Bloomberg/mock Bloomberg interface
- data flow into computation modules

---

## Regulatory treatment

### AIFMD

AIFMD does not impose one universal VaR confidence level, holding period, lookback window, or VaR limit for all AIFs.

For AIFs, methodology choices must be:

- adequate
- defined
- documented
- supported by fund strategy, risk profile, liquidity profile, and complexity

Market practice may be documented, but should not be presented as a universal statutory AIFMD rule.

### UCITS

UCITS has specific regulatory logic for global exposure, commitment approach, absolute VaR, relative VaR, and related limits.

UCITS should not blindly copy AIF hedge fund assumptions.

### PRIIPs

PRIIPs belongs to investor disclosure and KID methodology.

It should cover:

- summary risk indicator
- performance scenarios
- costs
- KID-ready outputs

### SFDR

SFDR is a regulatory disclosure framework.

Do not reduce SFDR to a generic ESG score.

SFDR work should distinguish:

- Article 6 / 8 / 9 classification
- sustainability risks
- principal adverse impacts
- pre-contractual disclosures
- website disclosures
- periodic disclosures

### EMIR

EMIR should be treated separately from AIFMD, UCITS, PRIIPs, and SFDR.

It is relevant where funds use derivatives and should be handled as derivatives regulatory reporting and controls.

---

## Key design rule

Use shared computation where possible.

Keep regulatory interpretation fund-specific.
