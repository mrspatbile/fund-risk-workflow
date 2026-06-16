# UCITS Balanced Fund Notes

This note collects supporting fund context, methodology notes, and interpretation guidance for the `UCITS_Balanced` notebook.

## Fund Information

`UCITS_Balanced` is a simulated UCITS fund with equity, fixed income, FX, cash, and derivative exposures.

The fund is modelled as a daily-dealing balanced UCITS strategy. The workflow focuses on liquid position-based risk monitoring, UCITS global exposure, issuer and counterparty limits, eligibility checks, stress testing, backtesting, pre-trade compliance, liquidity, investor-base monitoring, P&L attribution, and ESG indicators.

The monitoring workflow is UCITS-specific. It should not be interpreted as an AIFMD Annex IV or AIF-style risk framework.

Key fund characteristics used in the notebook:

* Fund ID: `UCITS_Balanced`
* Strategy: balanced UCITS
* Asset types: equities, fixed income, FX, cash, derivatives
* Structure: daily-dealing UCITS
* Base currency: EUR
* Main monitoring indicators: global exposure, absolute VaR, relative VaR, issuer concentration, counterparty exposure, eligible assets, borrowing, stress testing, VaR backtesting, pre-trade compliance, liquidity, investor-base monitoring, P&L attribution, and ESG indicators

## UCITS Monitoring Framework

The notebook separates UCITS regulatory requirements from fund-level configuration.

UCITS regulatory limits should be sourced from UCITS-specific regulation or central UCITS regulatory configuration where implemented. Fund-level Risk Management Policy parameters define practical setup, benchmark selection, reporting assumptions, and internal monitoring thresholds.

The RMP should not be interpreted as overriding UCITS regulatory limits.

## Global Exposure and VaR

UCITS global exposure can be measured using either the commitment approach or a VaR approach, depending on the fund profile and regulatory setup.

This notebook uses VaR-based monitoring for the simulated balanced UCITS fund.

Absolute VaR measures potential loss over a defined confidence level and holding period. In the notebook, the UCITS absolute VaR limit is presented as a 99% confidence, 20-day VaR limit of 20% of NAV.

The notebook also computes a 1-day VaR and scales it to 20 days using the square-root-of-time convention:

```text
20-day VaR = 1-day VaR × sqrt(20)
```

This scaling is a modelling convention. It should be interpreted together with the underlying assumptions, the reconstructed P&L series used, and model-validation outputs.

## Historical and Parametric VaR

The notebook compares two VaR methods:

* historical simulation
* parametric Student-t VaR

Historical simulation uses reconstructed historical P&L for the portfolio being measured. Positions are held fixed as of the risk date and revalued under historical market moves from the estimation window.

This means historical VaR is based on hypothetical P&L for the risk-date portfolio, not on realised historical fund returns.

Parametric VaR uses the reconstructed P&L distribution and fits a Student-t approximation using the sample mean, standard deviation, and degrees of freedom.

Both methods are useful for model comparison. The regulatory interpretation should follow the method documented for the fund and implemented in the UCITS risk framework.

## Expected Shortfall

Expected Shortfall measures the average loss in scenarios beyond the VaR threshold.

In this notebook, ES is shown as a supplementary tail-risk indicator. It helps interpret the severity of losses beyond the VaR quantile.

ES is not treated as a UCITS regulatory limit in this workflow unless explicitly mapped to a fund rule or regulatory configuration.

## Relative VaR

Relative VaR compares the fund VaR with the VaR of a reference portfolio.

```text
Relative VaR = fund VaR / reference portfolio VaR
```

Where applicable, the UCITS relative VaR limit requires the fund VaR to remain within the permitted multiple of the reference portfolio VaR.

For this simulated UCITS Balanced fund, the reference portfolio is a 60/40 allocation made up of 60% MSCI World and 40% EUR government bonds. The reference portfolio is documented in the fund's risk management policy.

The reference portfolio should be interpreted as a model input for the simulated workflow, not as proof of regulatory approval.

## Issuer Concentration and Eligibility

UCITS issuer concentration checks monitor compliance with UCITS diversification rules.

The notebook includes checks such as single-issuer exposure, the 5/10/40 rule, eligible assets, borrowing, and counterparty exposure.

Eligibility checks help ensure that proposed or existing exposures fit within the permitted UCITS investment universe. For this notebook, direct real estate, loans, CLOs, and private equity are treated as ineligible assets for the UCITS portfolio.

ETF exposure may require look-through analysis in a fuller implementation. If the simplified check applies concentration rules at ETF level, the result should be interpreted as a simplified control rather than a complete UCITS look-through assessment.

## Counterparty Risk

Counterparty exposure is monitored for OTC derivatives and related collateral arrangements.

The notebook presents UCITS counterparty exposure limits for credit institutions and other counterparties. The relevant exposure is the net uncollateralised amount after recognised netting and collateral treatment.

Collateral data is simulated. In a fuller workflow, counterparty exposure would be based on daily collateral reconciliation, margin calls, netting agreements, and counterparty classification.

## Pre-Trade Compliance

The pre-trade compliance check tests whether a proposed transaction creates or worsens a breach.

The notebook checks the proposed trade against UCITS-style controls, including:

* absolute VaR
* relative VaR
* issuer concentration
* eligible assets
* OTC derivative counterparty exposure
* borrowing limit

The output should be interpreted as a simulated pre-trade control. A full production implementation would require instrument eligibility data, issuer look-through, derivative exposure conversion, collateral treatment, and rule-specific exceptions.

## Stress Testing

The notebook applies stress scenarios to the UCITS portfolio to assess sensitivity to market moves and portfolio risk factors.

Stress testing can include:

* equity market shock
* interest-rate shock
* credit-spread shock
* FX shock
* combined stress
* historical scenarios

Stress testing supports portfolio monitoring and model review. It complements VaR because it can show losses under specific scenarios that may not be visible from the VaR number alone.

## VaR Backtesting

VaR backtesting compares predicted VaR with subsequent daily P&L.

The notebook applies backtesting over a rolling observation window and reports breach counts and statistical tests.

The main interpretation points are:

* too many breaches can indicate that the model underestimates risk
* clustered breaches can indicate that the model does not capture changing market conditions
* backtesting supports internal model validation and monitoring

Backtesting output should be interpreted alongside model assumptions, data quality, portfolio changes, and market conditions during the observation period.

## Liquidity and Investor-Base Monitoring

The UCITS fund is daily dealing, so liquidity monitoring should consider the ability to meet subscriptions and redemptions under normal and stressed conditions.

Investor concentration is relevant because a concentrated investor base can affect daily liquidity management. A large subscription or redemption may require cash-buffer usage, portfolio trading, or escalation to the management company.

This should be interpreted as UCITS investor-base and liquidity monitoring, not as AIF-style Annex IV investor concentration reporting.

## P&L Attribution

P&L attribution explains daily portfolio return drivers by risk factor.

In the notebook, attribution decomposes daily P&L into:

* market beta
* rates
* FX
* residual or unexplained P&L

The output is used as an internal model review and governance tool. It is not treated as a direct UCITS regulatory deliverable.

Residual P&L captures the portion of returns not explained by the selected market, rates, and FX factors.

## ESG Risk Indicators

The notebook computes portfolio-level ESG indicators using NAV-weighted averages.

Metrics may include:

* weighted average ESG score
* percentage of NAV below the internal ESG threshold
* controversy flags
* carbon intensity

ESG data for liquid instruments is sourced through the market-data workflow where available. Instruments without a Bloomberg ticker may use fund administrator data.

ESG scores should be treated as sustainability-risk or disclosure indicators unless they are explicitly mapped to SFDR concepts such as Article 6, Article 8, Article 9, PAIs, pre-contractual disclosures, website disclosures, or periodic disclosures.

## Interpretation Boundaries

This notebook is a simulated UCITS monitoring workflow.

The outputs are designed to show how UCITS-style risk monitoring can be structured in code. They should not be read as legal advice, regulatory approval, or a complete production compliance engine.

Where the notebook simplifies look-through, collateral, issuer grouping, eligibility, or derivative exposure conversion, the output should be treated as a simplified monitoring result.
