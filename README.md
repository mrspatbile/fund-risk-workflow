# fund-risk-workflow

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Status](https://img.shields.io/badge/Status-Workflow%20implementation-475569)
![Data](https://img.shields.io/badge/Data-Simulated-64748b)
![Domain](https://img.shields.io/badge/Domain-Fund%20Risk-334155)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?logo=sqlite\&logoColor=white)
[![AIFMD II](https://img.shields.io/badge/Reg-AIFMD%20II-orange)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024L0927)
[![UCITS VI](https://img.shields.io/badge/Reg-UCITS%20VI-blue)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024L0927)
[![PRIIPs](https://img.shields.io/badge/Reg-PRIIPs-green)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32014R1286)

`fund-risk-workflow` is a Python and notebook-led repository for selected fund risk workflows using simulated UCITS and AIFM-style fund data.

The repository focuses on how selected risk calculations, fund data, liquidity assumptions and output preparation can be organised across different fund examples. It includes workflows around VaR, backtesting, liquidity monitoring, redemption pressure, leverage checks, LMT mechanics and private asset risk indicators.

This repository is not a production ManCo platform, regulatory reporting engine or complete risk framework. The implementation is workflow-level, with simplified assumptions and mixed notebook/script structure.

---

## Scope

The repository covers selected fund risk examples across liquid and illiquid fund profiles.

| Fund example             | Illiquid | Selected scope                                                   |
| ------------------------ | :------: | ---------------------------------------------------------------- |
| UCITS Balanced           |          | VaR, SRI, PRIIPs KID example, eligibility checks                 |
| AIFM Hedge Fund L/S      |          | VaR, stress, liquidity monitoring, leverage, LMT mechanics       |
| AIFM PE Buyout           |     ✓    | IRR, MOIC, DPI, RVPI, PME, value bridge, selected ESG indicators |
| AIFM Private Debt        |     ✓    | credit risk indicators, covenant headroom, leverage indicators   |
| AIFM Real Estate         |     ✓    | LTV, rental stress, yield-capitalisation NAV                     |
| AIFM Infrastructure Core |     ✓    | DSCR, LTV, concession duration, inflation linkage                |

The hedge fund workflow is the most developed part of the repository. Other fund examples are included as selected methodology and output examples, not as full implementations.

---

## Example outputs

**VaR backtest with breach flags**

![VaR backtest with breach flags](images/hf_var_backtest.png)

The hedge fund workflow includes VaR backtesting with breach flags and test statistics across the simulated portfolio return series.

---

**Liquidity monitoring output**

![Liquidity monitoring output](images/board_report_p4.png)

The liquidity example summarises selected liquidity buckets, redemption pressure and fund-level monitoring indicators.

---

## Risk analytics examples

### Market risk

Included examples:

* VaR
* Expected Shortfall
* VaR backtesting
* P&L attribution examples
* stress scenarios for selected fund profiles

### Liquidity risk

Included examples:

* liquidity profiling
* redemption pressure
* investor concentration
* liquid and illiquid sleeve monitoring
* liquidity-adjusted VaR example
* selected liquidity stress assumptions

### Leverage and constraints

Included examples:

* leverage monitoring
* issuer and sector concentration examples
* UCITS-style eligibility checks
* pre-trade impact examples

These calculations are designed as workflow examples using simulated data. They are not a complete regulatory or production risk-control framework.

---

## Liquidity Management Tools

The repository includes a simplified LMT mechanics example for an AIFM-style fund under a 12-month redemption scenario.

Covered mechanics:

* redemption gate threshold
* deferred redemption backlog
* swing pricing threshold
* anti-dilution style cost adjustment
* suspension trigger example
* liquid and illiquid NAV sleeve decomposition

The LMT workflow is intended to show how redemption pressure, liquid asset coverage and tool triggers can be represented in Python. Thresholds and assumptions are simplified and should not be interpreted as regulatory calibration.

---

## Data and assumptions

The repository uses simulated fund, position and market data.

Market data is represented through a Bloomberg-style local pipeline, with positions and fund data stored in SQLite. The pipeline is intended to support repeatable workflow examples rather than live market-data integration.

Key assumptions:

* fund holdings are simulated
* valuation inputs for private assets are external or simplified
* liquidity buckets are assumption-driven
* LMT thresholds are illustrative
* regulatory references are used as methodology context
* outputs are reporting-oriented examples, not filing-ready reports

---

## Regulatory references

| Reference                                        | Repository use                                                 |
| ------------------------------------------------ | -------------------------------------------------------------- |
| UCITS Directive 2009/65/EC                       | selected UCITS eligibility and investment restriction examples |
| AIFMD 2011/61/EU                                 | AIFM risk management and fund monitoring context               |
| Commission Delegated Regulation (EU) No 231/2013 | AIFMD risk, liquidity and leverage methodology context         |
| Directive (EU) 2024/927                          | AIFMD II / UCITS VI liquidity management tools context         |
| ESMA34-39-897                                    | liquidity stress testing methodology context                   |
| ESMA34-671404336-1364                            | LMT selection and calibration methodology context              |
| PRIIPs Regulation                                | PRIIPs KID and SRI example for UCITS-style workflow            |
| IPEV Valuation Guidelines                        | private asset valuation reference points                       |
| SFDR                                             | selected sustainability indicators in private asset examples   |

The repository uses these references as methodology context. It does not attempt to implement the full regulatory framework.

---

## Output examples

The repository includes generated examples around:

* hedge fund VaR backtesting
* liquidity monitoring
* redemption and LMT mechanics
* selected private asset risk indicators
* UCITS-style risk and eligibility checks
* reporting-oriented fund risk summaries

Some outputs use reporting-style formatting. They should be read as workflow examples, not board-approved reporting packs or regulatory filings.

---

## Stack

* Python 3.13
* SQLite via SQLAlchemy ORM
* scipy
* matplotlib
* openpyxl
* JupyterLab

---

## Status and limitations

This repository is a workflow-level implementation using simulated data.

Current strengths:

* useful fund-risk workflow coverage
* developed hedge fund example
* practical examples across liquid and illiquid fund profiles
* repeatable local data and output generation
* clear links between risk concepts, calculations and outputs

Current limitations:

* notebook-led structure
* mixed script organisation
* simplified fund assumptions
* simulated positions and market data
* limited validation layer
* uneven depth across fund examples
* not designed as a reusable package or production risk system

A more structured package implementation is handled separately in `manco-risk`.

---

## Setup

```bash
git clone https://github.com/mrspatbile/fund-risk-workflow
cd fund-risk-workflow
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 src/setup_db.py
```

