# manco-risk-mngmt

![Python](https://img.shields.io/badge/Python-3.13-blue)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?logo=sqlite&logoColor=white)
[![AIFMD II](https://img.shields.io/badge/Reg-AIFMD%20II-orange)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024L0927)
[![UCITS](https://img.shields.io/badge/Reg-UCITS%20VI-blue)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024L0927)
[![PRIIPs](https://img.shields.io/badge/Reg-PRIIPs-green)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32014R1286)

Risk and regulatory analytics repository covering selected UCITS and AIFMD II requirements across liquid and illiquid fund strategies. The repository translates fund risk concepts into Python workflows for liquidity stress testing, leverage monitoring, LMT simulation, Annex IV-style outputs and board risk reporting.

Market data is simulated through a Bloomberg-style pipeline, with positions and fund data stored in SQLite. 

---

## Fund Coverage

| Fund | Illiquid | Scope |
|---|:---:|---|
| UCITS Balanced |  | VaR, SRI, PRIIPs KID, eligibility, pre-trade |
| AIFM Hedge Fund L/S | | Leverage, stress, liquidity stress, LMT, Annex IV, pre-trade |
| AIFM PE Buyout | ✓ | IRR, MOIC/DPI/RVPI, Long-Nickels PME, value bridge, ESG|
| AIFM Private Debt | ✓ | Credit risk, covenant headroom, leverage, Annex IV, ESG|
| AIFM Real Estate | ✓ | LTV, rental stress, yield-capitalisation NAV|
| AIFM Infrastructure Core | ✓ | DSCR/LTV, concession duration, inflation linkage|

---

## Example Outputs


<!-- **Board Risk Report — executive summary page**

![Board risk report executive summary](images/board_report_p1.png)

*Monthly board-ready PDF generated via `board_report.py`. AIFMD Article 15 internal governance format. Covers VaR, stress, liquidity and breach log.* -->

<!-- --- -->



**VaR backtest — breach flags and test statistics**

![VaR backtest with breach flags](images/hf_var_backtest.png)

*Kupiec and Christoffersen tests across the hedge fund portfolio. Breach dates flagged on the return series.*

---
**Liquidity monitoring dashboard**

![Board risk liquidity overview](images/board_report_p4.png)

---
## Risk Analytics

**Market risk**: VaR, Expected Shortfall, VaR backtest, P&L attribution.

**Liquidity risk**: liquidity profiling, redemption stress testing 
per ESMA/2020/1498, investor concentration, liquidity-adjusted VaR.

**Pre-trade compliance**: VaR impact, issuer and sector concentration, leverage limits, UCITS eligibility (Articles 50, 52).

---

## Liquidity Management Tools (AIFMD II)

LMT trigger simulation covering gate, swing pricing and suspension across a 
12-month redemption scenario. Models selected elements of the liquidity risk and LMT framework under AIFMD II Directive 2024/927/EU, Delegated Regulation EU 2026/466, 
and ESMA34-671404336-1364.

- **Gate**: caps monthly redemptions at a threshold percentage of NAV, defers 
  excess into a running backlog
- **Swing pricing**: dilution levy applied when gross redemptions exceed the swing 
  threshold, protecting remaining investors from transaction cost dilution
- **Suspension**: triggers when consecutive gate breaches and backlog as a 
  percentage of liquid NAV both exceed defined thresholds
- **NAV sleeve decomposition**: liquid sleeve depletes from outflows, illiquid 
  sleeve remains fixed, modelling the structural convergence risk toward the 
  illiquid floor
- **Output**: month-by-month DataFrame with gate, swing and suspension flags, backlog evolution and NAV composition

LMT thresholds are calibrated against redemption stress test output per ESMA/2020/1498.

---


## Regulatory Scope

| Regulation | Coverage |
|---|---|
| UCITS Directive 2009/65/EC | Luxembourg: Law of 17 December 2010 |
| AIFMD 2011/61/EU | Luxembourg: Law of 12 July 2013 |
| AIFMD II 2024/927/EU | Luxembourg: Law of 3 March 2026 — LMT framework, expanded Annex IV |
| EU 231/2013 | Leverage calculation Annex II, risk management Articles 46-49 |
| Delegated Regulation EU 2026/466 | LMT characteristics RTS |
| ESMA technical guidance v1.7 (July 2024) | Annex IV field definitions |
| ESMA/2020/1498 | Liquidity stress testing guidelines |
| ESMA34-671404336-1364 (March 2026) | LMT selection and calibration |
| CSSF Regulation 10-04 | Organisational requirements for ManCos |
| CSSF Regulation 22-05 | Sustainability requirements |
| IPEV Valuation Guidelines | PE and infrastructure fair value |
| SFDR | PAI indicators for private asset funds |

---

## Reporting Outputs

- **Annex IV** — AIFMD Article 110, all five AIFM funds, including AIFMD II expanded fields
- **Annex VI stress report** (ESMA/2020/1498) — cross-fund summary and per-fund sheets
- **Board Risk Report** — PDF, AIFMD Article 15 internal governance

---

## Stack

Python 3.13 · SQLite via SQLAlchemy ORM · scipy · matplotlib · openpyxl · JupyterLab

---

## Status and Limitations

Working prototype. Core analytics, reporting outputs, and LMT simulation are functional. 
The repository focuses on selected UCITS and AIFMD risk concepts and does not cover the full regulatory framework. Datasets, valuation inputs and fund assumptions are simulated for demonstration purposes.
Valuation inputs for private assets are treated as external inputs and consumed by the risk analytics and reporting workflows.

## Setup

```bash
git clone https://github.com/mrspatbile/manco-risk-mngmt
cd manco-risk-mngmt
python -m venv .venv
source .venv/bin/activate
pip install -e .
python src/setup_db.py
```
