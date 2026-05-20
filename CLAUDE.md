# manco-risk-mngmt

## What this project is

A personal research and investigation project simulating the workflow of a risk analyst operating under Luxembourg regulatory oversight, specifically UCITS and AIFM frameworks supervised by the CSSF. The goal is deep familiarity with the regulations, the difficulties of implementing them in practice.

This is not a production system. It is a structured investigation -- intentionally built to look and feel like a real risk platform, but with the honest constraint that valuations resources are restricted, some data sources are simulated and the `VALUATION_DATE` is static 13/05/2026, and there is no change in the portfolio positions, except for the PE fund.

## What has been built so far

- Fund examples: UCITS balanced, AIFM hedge fund long/short, PE, RE, private debt, infrastructure core
- Risk metrics: VaR (historical, parametric, Monte Carlo), ES, VaR backtest (Kupiec, Christoffersen), P&L attribution
- Stress scenarios: equity, rates, credit, FX, combined, historical, property, rental, LTV; infrastructure NAV stress (discount rate + inflation shock)
- Liquidity profiling in buckets, redemption stress, investor concentration, liquidity-adjusted VaR
- Pre-trade compliance check (`pre_trade_check` in `risk_utils.py`): UCITS, AIFM HF, and AIFM Private Debt flavours -- checks VaR impact, issuer concentration, leverage, and eligibility before execution
- Leverage classification per AIFMD Article 7 (gross and commitment method) via `leverage_config.py`
- ESG evaluation using mock 3rd party data
- Position enrichment pipeline: Bloomberg sensitivities (beta, duration, convexity) for liquid assets; fund-admin embedded data for illiquid assets (loans, direct properties)
- PE analytics: XIRR, fund IRR, MOIC/DPI/RVPI multiples, value bridge, Long-Nickels PME benchmark comparison
- Infrastructure analytics (`infra_utils.py`): DSCR/LTV covenant profiles with breach and waiver tracking, sector concentration, inflation linkage, weighted concession duration, cashflow coverage, IRR/MOIC/DPI/RVPI multiples, yield-capitalisation NAV stress
- Regulatory output layer: Annex VI stress test Excel export (`annex_vi_export.py`, CSSF submission format) and monthly Board Risk Report PDF (`board_report.py`, AIFMD Article 15 internal governance)
- SQLite database (`data/risk_management.db`) via SQLAlchemy -- central store for all fund data, including dedicated infra schema (infra_funds, infra_assets, infra_nav_history, infra_valuation_report, infra_debt, infra_covenants)
- Data layer that simulates Bloomberg/3rd party feeds for illiquids and uses real yfinance data for listed assets; prices cached in `data/yf_cache/`
- Reference data directory (`reference_data/`): position specs per fund, ticker map, ESG scores, PE companies, infra assets, fund master -- all moved out of src during MRS-82 refactor
- Daily export simulation: `generate_daily_export.py` extracts single-date position slices mimicking a fund administrator file
- Idempotent DB setup script (`setup_db.py`) and end-to-end pipeline validation script (`validate_pipeline.py`)
- Shared dark-theme matplotlib style (`plot_style.py`) used across all notebooks
- Unit tests in `tests/` mirroring `src/`

## What is coming next (in order)

1. **Newer regulatory topics** -- AIFMD II Annex IV expanded fields, CSSF-facing dashboards.
2. **Additional fund types or analytics** -- to be decided via Linear.

## Project structure

```
src/
  database.py              # SQLAlchemy DB: create schema, load positions, query helpers
                           #   includes infra schema (infra_funds, infra_assets, infra_nav_history,
                           #   infra_valuation_report, infra_debt, infra_covenants)
  enrichment.py            # Position enrichment pipeline (Bloomberg + fund-admin data)
  esg_utils.py             # ESG scoring from mock 3rd-party data
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
  annex_vi_export.py       # Annex VI stress test Excel export -- CSSF submission format
                           #   (HF, PD, RE; cross-fund summary + per-fund sheets)
  board_report.py          # Monthly Board Risk Report PDF -- AIFMD Article 15 internal governance
                           #   (executive summary, VaR, stress, liquidity, breach log)
  setup_db.py              # Idempotent DB setup (--force to rebuild from scratch)
  validate_pipeline.py     # End-to-end pipeline validation

reference_data/            # Static reference data (moved out of src in MRS-82)
  fund_master.json         # Fund IDs, names, types
  fund_file_map.json       # Fund ID → position Excel filename mapping
  ticker_map.json          # Internal ticker → yfinance ticker + asset class
  esg_scores.json          # Mock 3rd-party ESG scores per issuer
  pe_companies.json        # PE fund portfolio companies (entry/exit data)
  infra_assets.json        # Infrastructure assets master (sector, country, concession dates)
  position_specs/          # Per-fund position definitions (UCITS_Balanced, AIFM_HedgeFund, etc.)

tests/
  One test file per src module. test_setup_db.py is marked @pytest.mark.skip
  by default -- it is an integration test that rebuilds the live DB and must
  be run manually.

notebooks/
  ucits_balanced.ipynb     # UCITS Balanced -- VaR limits, SRRI, eligibility checks
  aifm_hedge_fund.ipynb    # AIFM Hedge Fund -- leverage, stress, liquidity, Annex IV
  aifm_pe_buyout.ipynb     # AIFM PE Buyout -- IRR, multiples, NAV, liquidity profile, PME
  aifm_private_debt.ipynb  # AIFM Private Debt -- credit risk, leverage, Annex IV
  aifm_real_estate.ipynb   # AIFM Real Estate -- LTV, rental stress, direct property
  aifm_infra_fund.ipynb    # AIFM Infra Core -- DSCR/LTV, duration, stress, covenant history
  board_risk_report.ipynb  # Board Risk Report -- drives board_report.py
  data_pipeline.ipynb      # Daily data validation workflow (pricing, new instruments)

data/                      # Gitignored -- not in version control
  risk_management.db       # SQLite database
  fund_positions_*.xlsx    # Full 250-day position histories per fund
  daily_exports/           # Single-date position slices per fund per date
  yf_cache/                # Cached yfinance price and info files
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
- AIFMD II (Directive 2024/927/EU) -- expanded Annex IV requirements
- Delegated Regulation EU 231/2013 -- leverage calculation methodology (gross and commitment)
- ESMA technical guidance v1.7 (July 2024) -- Annex IV reporting
- ESMA/2020/1498 -- stress testing guidance (Annex VI)
- CSSF Regulation 10-04 (organisational and prudential requirements for dual ManCos)
- CSSF Regulation 22-05 (sustainability requirements, amends 10-04)
- IPEV Valuation Guidelines -- PE and infrastructure fair value methodology (yield capitalisation)
- AIFMD Article 15 -- liquidity management (infra: closed-ended, no redemption obligation)
- AIFMD Article 19 -- independent valuation (infra: appraiser inputs boundary respected)
- EU 231/2013 Articles 46-49 -- risk management for AIFMs
- Risk metrics: VaR, ES, liquidity classification, leverage, ESG, backtest, P&L attribution, PME, DSCR, LTV, MOIC/DPI/RVPI, inflation sensitivity
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

The developer has a finance background and works at the intersection of finance and technology. Code quality matters here: clean design, good package structure and disciplined progression through Linear issues with references in commits. When making changes, always explain the business logic so it can be verified for regulatory correctness. Do not over-explain technical basics, but never skip the reasoning behind implementation choices.

## Things to never do without explicit permission

- Refactor across multiple files in one go
- Change data structures or schemas
- Delete or rename anything
- Touch `.venv/` or any environment config
- Create new Linear tickets (suggest them, let me decide)

## Tone

This is a research and learning project. When I ask why something is done a certain way, in the code or in the regulation, take the time to explain it properly. That is part of the value.
