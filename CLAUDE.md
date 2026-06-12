# fund-risk-workflow

## What this project is

A personal research and investigation project simulating the workflow of a risk analyst operating under Luxembourg regulatory oversight, specifically UCITS and AIFM frameworks supervised by the CSSF. The goal is deep familiarity with the regulations, the difficulties of implementing them in practice.

This is not a production system. It is a structured investigation. It is intentionally built to look and feel like a real risk platform, but with the honest constraint that valuations resources are restricted, some data sources are simulated and the `VALUATION_DATE` is static 13/05/2026, and there is no change in the portfolio positions, except for the PE fund.

## What has been built so far

- Fund examples: UCITS balanced, AIFM hedge fund long/short, PE, RE, private debt, infrastructure core
- Risk metrics: VaR (historical, parametric, Monte Carlo), ES, VaR backtest (Kupiec, Christoffersen), P&L attribution
- Stress scenarios: equity, rates, credit, FX, combined, historical, property, rental, LTV; infrastructure NAV stress (discount rate + inflation shock)
- Liquidity profiling in buckets, redemption stress, investor concentration, liquidity-adjusted VaR
- Pre-trade compliance check (`pre_trade_check` in `risk_utils.py`): UCITS, AIFM HF, and AIFM Private Debt flavours -- checks VaR impact, issuer concentration, leverage, and eligibility before execution; with worked pass/fail examples in the HF and UCITS notebooks
- Leverage classification per AIFMD Article 7 (gross and commitment method) via `leverage_config.py`
- ESG evaluation: `esg_utils.py` covers listed assets via mock Bloomberg data and private assets (PE, infra) via independent appraiser data; `build_private_esg_df` assembles SFDR PAI-ready DataFrames for PE and infra funds; ESG scores in `esg_scores.json` cover all issuers, portfolio companies, and infrastructure assets
- Position enrichment pipeline: Bloomberg sensitivities (beta, duration, convexity) for liquid assets; fund-admin embedded data for illiquid assets (loans, direct properties)
- PE analytics: XIRR, fund IRR, MOIC/DPI/RVPI multiples, value bridge, Long-Nickels PME benchmark comparison
- Infrastructure analytics (`infra_utils.py`): DSCR/LTV covenant profiles with breach and waiver tracking, sector concentration, inflation linkage, weighted concession duration, cashflow coverage, IRR/MOIC/DPI/RVPI multiples, yield-capitalisation NAV stress
- Regulatory output layer:
  - Annex VI stress test Excel export (`annex_vi_export.py`, CSSF submission format, HF/PD/RE)
  - Annex IV transparency report (`annex_iv.py`, AIFMD Article 110, all five AIFM funds): fund identity, exposures, VaR, gross/commitment leverage, liquidity profile, AIFMD II expanded fields (LMTs, unfunded commitments); Excel export in CSSF format
  - Monthly Board Risk Report PDF (`board_report.py`, AIFMD Article 15 internal governance)
- SQLite database (`data/risk_management.db`) via SQLAlchemy -- central store for all fund data, including dedicated infra schema (infra_funds, infra_assets, infra_nav_history, infra_valuation_report, infra_debt, infra_covenants)
- Data layer that simulates Bloomberg/3rd party feeds for illiquids and uses real yfinance data for listed assets; prices cached in `data/yf_cache/`
- Reference data directory (`reference_data/`): position specs per fund, ticker map, ESG scores (listed + PE + infra), PE companies, infra assets, fund master
- Daily export simulation: `generate_daily_export.py` extracts single-date position slices mimicking a fund administrator file
- Idempotent DB setup script (`setup_db.py`) and end-to-end pipeline validation script (`validate_pipeline.py`)
- Shared dark-theme matplotlib style (`plot_style.py`) used across all notebooks
- Unit tests in `tests/` mirroring `src/`

## Project structure

```
src/
  database.py              # SQLAlchemy DB: create schema, load positions, query helpers
                           #   includes infra schema (infra_funds, infra_assets, infra_nav_history,
                           #   infra_valuation_report, infra_debt, infra_covenants)
  enrichment.py            # Position enrichment pipeline (Bloomberg + fund-admin data)
  esg_utils.py             # ESG scoring: build_esg_df (listed assets via mock Bloomberg),
                           #   build_private_esg_df (PE and infra via appraiser data),
                           #   esg_portfolio_summary (works on both)
  generate_positions.py    # Generates 250-day Excel position histories for liquid funds
  generate_pe_fund.py      # Generates synthetic PE fund data (companies, cash flows, NAV)
  generate_infra_fund.py   # Generates AIFM_Infra_Core fund: 8 assets, valuation reports,
                           #   covenant history, debt tranches, cash flows
  generate_daily_export.py # Extracts single-date slices (mimics fund admin daily file)
  leverage_config.py       # AIFMD Article 7 leverage classification map
  mock_bloomberg.py        # MockBloomberg class -- mirrors blpapi interface, uses yf_cache
  pe_utils.py              # PE analytics: XIRR, IRR, multiples, value bridge, Long-Nickels PME
  infra_utils.py           # Infrastructure analytics: DSCR/LTV profiles, inflation sensitivity,
                           #   duration profile, sector concentration, NAV stress, IRR/multiples
  plot_style.py            # Shared matplotlib dark theme for all notebooks
  risk_utils.py            # VaR, ES, backtests, stress scenarios, liquidity metrics,
                           #   pre_trade_check (UCITS / AIFM HF / AIFM PD)
  annex_iv.py              # Annex IV transparency report -- AIFMD Article 110 / EU 231/2013
                           #   all five AIFM funds; build_annex_iv() + export_annex_iv_excel()
                           #   AIFMD II expanded fields: LMTs and unfunded commitments (PE/infra)
  annex_vi_export.py       # Annex VI stress test Excel export -- CSSF submission format
                           #   (HF, PD, RE; cross-fund summary + per-fund sheets)
  board_report.py          # Monthly Board Risk Report PDF -- AIFMD Article 15 internal governance
                           #   (executive summary, VaR, stress, liquidity, breach log)
  setup_db.py              # Idempotent DB setup (--force to rebuild from scratch)
  validate_pipeline.py     # End-to-end pipeline validation

reference_data/            # Static reference data
  fund_master.json         # Fund IDs, names, types
  fund_file_map.json       # Fund ID → position Excel filename mapping
  ticker_map.json          # Internal ticker → yfinance ticker + asset class
  esg_scores.json          # Mock 3rd-party ESG scores: listed issuers (by ISIN),
                           #   PE portfolio companies (PE_001–PE_008),
                           #   infrastructure assets (INFRA_001–INFRA_008)
  pe_companies.json        # PE fund portfolio companies (entry/exit data)
  infra_assets.json        # Infrastructure assets master (sector, country, concession dates)
  position_specs/          # Per-fund position definitions (UCITS_Balanced, AIFM_HedgeFund, etc.)

tests/
  One test file per src module. test_setup_db.py is marked @pytest.mark.skip
  by default -- it is an integration test that rebuilds the live DB and must
  be run manually.

notebooks/
  ucits_balanced.ipynb     # UCITS Balanced -- VaR limits, SRRI, eligibility, pre-trade check
  aifm_hedge_fund.ipynb    # AIFM Hedge Fund -- leverage, stress, liquidity, pre-trade check, Annex IV
  aifm_pe_buyout.ipynb     # AIFM PE Buyout -- IRR, multiples, NAV, PME, ESG, Annex IV
  aifm_private_debt.ipynb  # AIFM Private Debt -- credit risk, leverage, ESG, Annex IV
  aifm_real_estate.ipynb   # AIFM Real Estate -- LTV, rental stress, direct property, ESG, Annex IV
  aifm_infra_ fund.ipynb   # AIFM Infra Core -- DSCR/LTV, duration, stress, ESG, Annex IV
  board_risk_report.ipynb  # Board Risk Report -- drives board_report.py
  data_pipeline.ipynb      # Daily data validation workflow (pricing, new instruments)

data/                      # Gitignored -- not in version control
  risk_management.db       # SQLite database
  fund_positions_*.xlsx    # Full 250-day position histories per fund
  daily_exports/           # Single-date position slices per fund per date
  yf_cache/                # Cached yfinance price and info files
  annex_iv_report_*.xlsx   # Annex IV outputs (quarterly, per reporting period)
  annex_vi_report_*.xlsx   # Annex VI outputs
  board_risk_report_*.pdf  # Board report PDFs

pyproject.toml             # Package metadata (Python 3.13, setuptools)
.venv/                     # Python virtual environment -- do not touch
```

## Stack

- Python 3.13 (primary language)
- SQLite via SQLAlchemy (central data store)
- yfinance for real market data (prices cached locally)
- scipy (statistical distributions for parametric VaR and ES)
- matplotlib (charts via shared `plot_style.py`)
- openpyxl (Excel read/write for position files)
- Simulated data layer mimicking Bloomberg and illiquid 3rd party feeds
- Notebooks (Jupyter / JupyterLab) for exploration
- GitHub for version control
- Linear for issue tracking
- Claude Code

## Regulatory scope

- UCITS Directive (2009/65/EC) and Luxembourg implementation via CSSF
- AIFMD (Directive 2011/61/EU) and Luxembourg implementation via CSSF (Law of 12 July 2013)
- AIFMD II (Directive 2024/927/EU) -- LMT disclosures (suspension, side pockets, capital call facility) and expanded Annex IV fields implemented in annex_iv.py for PE and infra funds
- Delegated Regulation EU 231/2013 -- leverage calculation methodology (gross and commitment); Articles 46-49 risk management; Article 7 project finance treatment for PE/infra debt
- ESMA technical guidance v1.7 (July 2024) -- Annex IV reporting field definitions
- ESMA/2020/1498 -- stress testing guidance (Annex VI)
- CSSF Regulation 10-04 (organisational and prudential requirements for dual ManCos)
- CSSF Regulation 22-05 (sustainability requirements, amends 10-04)
- IPEV Valuation Guidelines -- PE and infrastructure fair value methodology (yield capitalisation)
- AIFMD Article 15 -- liquidity management (infra: closed-ended, no redemption obligation)
- AIFMD Article 19 -- independent valuation (infra: appraiser inputs boundary respected)
- SFDR PAI indicators -- private asset ESG disclosure context (PE and infra via independent appraiser data)
- Risk metrics: VaR, ES, liquidity classification, leverage, ESG, backtest, P&L attribution, PME, DSCR, LTV, MOIC/DPI/TVPI, inflation sensitivity
- Known limitation: no real valuation engine, simulations are intentionally simplified; there is a separate project focused on implementing valuation in an OOP paradigm.

## How we work together

**Do not make changes without checking with me first.**

The preferred flow for every task:
1. Read the relevant Linear issue before touching anything
2. Explain your understanding of the task and your proposed approach
3. Wait for my go-ahead before writing or changing any code
4. Make changes one logical step at a time -- not everything at once
5. After each step, explain what you did and why
6. After each step, when I consider code done, I will ask you for a commit msg - I will commit myself. The message you pass to me should include the commands: git add and git commit -m
The commit message must include the Linear issue ID in the format:
`[LIN-123] short description`. Ask me for the ID if you do not have it.

The developer has a finance background and works at the intersection of finance and technology. Code quality matters here: clean design, good package structure and disciplined progression through Linear issues with references in commits. When making changes, always explain the business logic so it can be verified for regulatory correctness. Do not over-explain technical basics, but never skip the reasoning behind implementation choices.

## Things to never do without explicit permission

- Refactor across multiple files in one go
- Change data structures or schemas
- Delete or rename anything
- Touch `.venv/` or any environment config
- Create new Linear tickets (suggest them, let me decide)

## Tone

This is a research and learning project. When I ask why something is done a certain way, in the code or in the regulation, take the time to explain it properly. That is part of the value.

## Hard constraints — never override

- `VALUATION_DATE` is intentionally static at 13/05/2026. Do not change it,
  do not suggest making it dynamic, do not add date-range logic. All analytics
  are point-in-time by design.
- Portfolio positions do not change across funds, except for the PE fund.
  Do not suggest or introduce position-update logic elsewhere.

## Code style

- PEP 8 throughout.
- Type hints on all public functions and methods.
- Docstrings on all public classes and functions. Where a parameter has a
  non-obvious convention (percent vs decimal, annualised vs daily), state it
  explicitly in the docstring.
- No new dependencies without flagging first.

## Scope boundary

This project is a structured learning and research environment. There is a
separate project, quant-risk-engine, that focuses on production-grade OOP
design, QuantLib integration, and regulatory capital calculations. Do not
suggest production patterns, refactors, or architectural changes imported
from that context. If something works and is clear, it is good enough here.