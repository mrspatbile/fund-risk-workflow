# manco-risk-mngmt

## What this project is

A personal research and investigation project simulating the workflow of a risk analyst operating under Luxembourg regulatory oversight, specifically UCITS and AIFM frameworks supervised by the CSSF. The goal is deep familiarity with the regulations, the difficulties of implementing them in practice.

This is not a production system. It is a structured investigation -- intentionally built to look and feel like a real risk platform, but with the honest constraint that valuations resources are restricted, some data sources are simulated and the valuate_date is static  13/05/2026, and ther ei snot change in the portolio positiosn, except for the PE fund.

## What has been built so far

- Fund examples: UCITS balanced, AIFM hedge fund long/short, PE, RE, private debt
- Risk metrics: VaR (historical, parametric), ES, mock Monte Carlo
- Liquidity profiling in buckets
- ESG evaluation using mock 3rd party data
- VaR backtest
- P&L attribution
- Data layer that simulates Bloomberg/3rd party feeds for illiquids and uses real yfinance data for listed assets
- Unit tests in `tests/` mirroring `src/`
- Notebooks for output review and regulatory concept exploration

## What is coming next (in order)

1. **Data refactor** -- move hardcoded data out of src files (fund positions, yfinance/BBG mapping, ESG info, mock 3rd party company entry/exit data) into a proper data layer. This is not yet a Linear ticket but should be the next one created.
2. **Pre-trade authorization and limits** -- there is already a Linear ticket for this.
3. **Newer regulatory topics** -- will reuse the new data architecture once it is in place.
4. **Dashboards** -- for internal consumption (board and risk committee) and for the regulatory supervisor (CSSF-facing).

## Project structure

```
src/          # Main source modules
tests/        # Unit tests mirroring src/
notebooks/    # Exploratory output and regulatory concept walkthroughs
.venv/        # Python virtual environment -- do not touch
```

## Stack

- Python (primary language)
- yfinance for real market data
- Simulated data layer mimicking Bloomberg and illiquid 3rd party feeds
- Notebooks (Jupyter) for exploration
- GitHub for version control
- Linear for issue tracking
- Claude code

## Regulatory scope

- UCITS regulation and Luxembourg implementation via CSSF
- AIFM regulation and Luxembourg implementation via CSSF
- Risk metrics: VaR, ES, liquidity classification, ESG, backtest, P&L attribution
- Known limitation: no real valuation engine, simulations are intentionally simplified, there is a separate project where the focus in to implemnt valuation in OOP paradigm.

## How we work together

**Do not make changes without checking with me first.**

The preferred flow for every task:
1. Read the relevant Linear issue before touching anything
2. Explain your understanding of the task and your proposed approach
3. Wait for my go-ahead before writing or changing any code
4. Make changes one logical step at a time -- not everything at once
5. After each step, explain what you did and why

The developer has a finance background and works at the intersection of finance and technology. Code quality matters here: clean design, good package structure and disciplined progression through Linear issues with references in commits. When making changes, always explain the business logic so it can be verified for regulatory correctness. Do not over-explain technical basics, but never skip the reasoning behind implementation choices.

## Things to never do without explicit permission

- Refactor across multiple files in one go
- Change data structures or schemas
- Delete or rename anything
- Touch `.venv/` or any environment config
- Create new Linear tickets (suggest them, let me decide)

## Tone

This is a research and learning project. When I ask why something is done a certain way, in the code or in the regulation, take the time to explain it properly. That is part of the value.