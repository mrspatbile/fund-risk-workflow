Yes — replace the long file with this condensed version. It keeps the schema contract, loader summary, and validation rules without the long examples. Based on the uploaded draft, the main issue is repetition and large per-file examples. 

# Reference Data Schema

## Purpose

This document describes the JSON input structures used under `reference_data/` and the loader rules used by `src.data.reference_data`.

Reference-data files are controlled inputs for the example fund risk workflows. They are loaded into the local database or used by workflow helpers to build reproducible fund, position, investor, market-data, scenario, and regulatory inputs.

## General rules

* JSON files use `schema_version` to identify the structure expected by the loader.
* `schema_version` changes only when the file structure changes.
* `schema_version` is not a valuation date and is not a last-updated date.
* Fund-specific JSON files under `reference_data/funds/<fund_id>/` include top-level `fund_id` for audit and validation.
* `fund_name` belongs in `fund_profile.json`.
* Other fund-specific files should not duplicate `fund_name`.
* List-style files use an object wrapper rather than a bare array.
* Reference-data JSON files should be read through loader functions, not direct `json.load()` calls.

## Loader module

The central loader module is:

`src/data/reference_data.py`

Loaders read reference-data JSON files, handle `schema_version`, validate fund identity where applicable, and return the business content expected by workflow code.

## Loader summary

| Loader                              | File pattern                                                       | Validates `schema_version` | Validates `fund_id` | Returns                                   |
| ----------------------------------- | ------------------------------------------------------------------ | :------------------------: | :-----------------: | ----------------------------------------- |
| `load_rmp`                          | `reference_data/funds/<fund_id>/risk_policy.json`                  |             yes            |         yes         | risk policy dictionary                    |
| `load_fund_profile`                 | `reference_data/funds/<fund_id>/fund_profile.json`                 |             yes            |         yes         | fund profile dictionary                   |
| `load_regulatory_framework`         | `reference_data/regulation/<framework_name>.json`                  |             yes            |          no         | regulatory framework dictionary           |
| `load_reference_portfolios`         | `reference_data/benchmarks/reference_portfolios.json`              |             yes            |          no         | all reference portfolios                  |
| `load_reference_portfolio`          | `reference_data/benchmarks/reference_portfolios.json`              |             yes            |          no         | one reference portfolio                   |
| `load_investor_base`                | `reference_data/funds/<fund_id>/investors.json`                    |             yes            |         yes         | investor base as DataFrame                |
| `load_investor_base_dict`           | `reference_data/funds/<fund_id>/investors.json`                    |             yes            |         yes         | investor base as dictionary               |
| `load_liquidity_calibration_inputs` | `reference_data/funds/<fund_id>/liquidity_calibration_inputs.json` |             yes            |         yes         | liquidity calibration dictionary          |
| `load_investor_type_mapping`        | `reference_data/platform/investor_type_mapping.json`               |             yes            |          no         | investor type mapping                     |
| `load_historical_scenarios`         | `reference_data/scenarios/historical_scenarios.json`               |             yes            |          no         | historical stress scenarios               |
| `load_esg_scores`                   | `reference_data/instruments/esg_scores.json`                       |             yes            |          no         | ESG scores keyed by instrument identifier |
| `load_scenario_file`                | `reference_data/risk_scenarios/<filename>.json`                    |             yes            |          no         | scenario definitions                      |

## Schema summary

| File pattern                                                       | Purpose                                        | Required top-level keys                                  | Loader                                                  |
| ------------------------------------------------------------------ | ---------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------- |
| `reference_data/platform/fund_registry.json`                       | Platform fund list                             | `schema_version`, `funds`                                | no dedicated loader                                     |
| `reference_data/platform/fund_file_map.json`                       | Fund source-file mapping                       | `schema_version`, fund ID mappings                       | no dedicated loader                                     |
| `reference_data/platform/investor_type_mapping.json`               | Investor type normalization                    | `schema_version`, `investor_type_mapping`                | `load_investor_type_mapping`                            |
| `reference_data/regulation/*.json`                                 | Regulatory framework configuration             | `schema_version`, framework-specific keys                | `load_regulatory_framework`                             |
| `reference_data/funds/<fund_id>/fund_profile.json`                 | Static fund profile                            | `schema_version`, `fund_id`, `fund_name`, profile fields | `load_fund_profile`                                     |
| `reference_data/funds/<fund_id>/risk_policy.json`                  | Fund-specific risk policy                      | `schema_version`, `fund_id`, policy fields               | `load_rmp`                                              |
| `reference_data/funds/<fund_id>/investors.json`                    | Fund investor records                          | `schema_version`, `fund_id`, `investors`                 | `load_investor_base`, `load_investor_base_dict`         |
| `reference_data/funds/<fund_id>/liquidity_calibration_inputs.json` | Liquidity calibration inputs                   | `schema_version`, `fund_id`, calibration fields          | `load_liquidity_calibration_inputs`                     |
| `reference_data/funds/<fund_id>/counterparties.json`               | Counterparty exposure assumptions              | `schema_version`, `fund_id`, `counterparties`            | `load_counterparty`                                     |
| `reference_data/funds/<fund_id>/position_specs.json`               | Position specifications for generated holdings | `schema_version`, `fund_id`, `position_specs`            | `_load_specs`                                           |
| `reference_data/instruments/esg_scores.json`                       | ESG metrics by instrument identifier           | `schema_version`, instrument score mappings              | `load_esg_scores`                                       |
| `reference_data/instruments/ticker_map.json`                       | Ticker mapping for simulated market data       | `schema_version`, ticker mappings                        | no dedicated loader                                     |
| `reference_data/benchmarks/reference_portfolios.json`              | Reference benchmark portfolios                 | `schema_version`, portfolio mappings                     | `load_reference_portfolios`, `load_reference_portfolio` |
| `reference_data/portfolios/pe_companies.json`                      | Private equity portfolio company master data   | `schema_version`, `companies`                            | generation utility                                      |
| `reference_data/portfolios/infra_assets.json`                      | Infrastructure asset master data               | `schema_version`, `assets`                               | generation utility                                      |
| `reference_data/scenarios/historical_scenarios.json`               | Historical stress scenarios                    | `schema_version`, scenario mappings                      | `load_historical_scenarios`                             |
| `reference_data/risk_scenarios/*.json`                             | Risk scenario definitions                      | `schema_version`, `scenarios`                            | `load_scenario_file`                                    |

## Fund-specific file rules

Fund-specific files are stored under:

`reference_data/funds/<fund_id>/`

Rules:

* `fund_profile.json` contains `fund_id` and `fund_name`.
* Other fund-specific files include top-level `fund_id` but do not duplicate `fund_name`.
* List-style fund files use an object wrapper rather than a bare array.
* Row-level records should not repeat `fund_id` or `fund_name`.
* If downstream code needs `fund_id` or `fund_name`, the loader or generation step should add those fields programmatically.

Example object wrapper:

```json
{
  "schema_version": "1.0",
  "fund_id": "AIFM_HedgeFund",
  "counterparties": [
    {
      "counterparty": "Goldman Sachs",
      "type": "Prime Broker",
      "exposure_pct": 0.12,
      "collateral_cover": 0.80
    }
  ]
}
```

## Platform files

Platform files under `reference_data/platform/` define shared configuration used across the example fund platform.

Rules:

* Platform files should not include `fund_name`.
* Platform files should not include cosmetic metadata dates.
* Fund IDs may appear where the file maps fund IDs to files, settings, or platform membership.

## Regulation files

Regulation files under `reference_data/regulation/` store central regulatory configuration and prescribed values.

Rules:

* Regulation files should not include fund-specific policy thresholds.
* Fund-specific thresholds belong in `risk_policy.json`.
* Regulation files should not include `fund_name`.

## Instrument, portfolio, benchmark, and scenario files

These files define shared reference inputs that are not owned by a single fund.

Rules:

* Do not add top-level `fund_id` unless the file is fund-specific.
* Use `schema_version` for structure control.
* Keep historical dates, maturities, inception dates, investment dates, exit dates, concession dates, and scenario dates as business data where they are part of the sample dataset.

## Validation rules

### Implemented

Current loaders implement these validation rules:

* `schema_version` is recognized and handled by loaders.
* Fund-specific loaders validate that top-level `fund_id` matches the requested fund ID where applicable.
* Loader functions return clean business content to callers, without requiring caller code to handle schema metadata directly.

### Not yet implemented

The following validation checks are not yet fully implemented:

* Per-file business key validation, such as checking that `risk_policy.json` contains required policy sections.
* Nested object validation, such as checking the internal structure of `var_framework` or `liquidity_monitoring`.
* Cross-file reference validation, such as checking that scenario names referenced in `risk_policy.json` exist in scenario definition files.

## Files without dedicated loaders

These files currently do not have dedicated loader functions:

| File                                         | Current access pattern                   |
| -------------------------------------------- | ---------------------------------------- |
| `reference_data/platform/fund_registry.json` | used by setup or utility code            |
| `reference_data/platform/fund_file_map.json` | used by setup or utility code            |
| `reference_data/instruments/ticker_map.json` | used by market-data simulation utilities |

If these files become part of repeated workflows, dedicated loaders should be added.

## Out of scope

This document covers reference-data JSON files and reference-data loaders.

Database tables, columns, keys, and relationships should be documented separately in:

`docs/schemas/database_schema.md`
