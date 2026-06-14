
# Notebook Alignment Playbook

## Notebook Editing Safety Rules

Markdown cleanup must not damage executable notebook content.

Claude must treat code cells as protected unless the task explicitly says otherwise.

### Hard Rules

When the task is markdown cleanup:

- Do not delete code cells.
- Do not merge code cells.
- Do not split code cells.
- Do not reorder code cells.
- Do not edit code cell source.
- Do not clear outputs unless explicitly asked.
- Do not rerun the notebook unless explicitly asked.
- Do not change imports, constants, function calls, filenames, export IDs, or calculation logic.
- Do not remove cells that look unused without asking first.

### Required Before Editing

Before changing a notebook, Claude must record:

- total number of cells
- number of markdown cells
- number of code cells

### Required After Editing

After changing markdown, Claude must confirm:

- total number of cells is unchanged
- number of code cells is unchanged
- code cell sources are unchanged
- only markdown cell sources changed

### Recommended Validation

For markdown-only work, compare code cells before and after editing.

Suggested check:

```python
import json
from pathlib import Path

path = Path("notebooks/fund_risk_monitoring/aifm_hedge_fund.ipynb")

before = json.loads(path.read_text())
before_code = [
    "".join(cell.get("source", []))
    for cell in before["cells"]
    if cell.get("cell_type") == "code"
]

# After editing, reload:
after = json.loads(path.read_text())
after_code = [
    "".join(cell.get("source", []))
    for cell in after["cells"]
    if cell.get("cell_type") == "code"
]

assert before_code == after_code, "Code cells changed during markdown-only edit"


## Purpose

This playbook defines how to align the remaining notebooks with the cleaner AIFM Hedge Fund notebook style.

The objective is not to make every notebook follow the same risk structure. Each fund type keeps its own risk story, methodology, and regulatory treatment.

The alignment is about:

- cleaner markdown
- shorter section introductions
- clearer workflow narrative
- consistent output presentation
- reusable output-gallery logic
- less repeated regulatory explanation
- hyperlinks to supporting docs where detail would make the notebook too long

## Reference Notebook

Use `notebooks/fund_risk_monitoring/aifm_hedge_fund.ipynb` as the reference for:

- tone
- markdown density
- output naming
- visual discipline
- export-gallery workflow
- separation between notebook explanation and reusable code

Do not use it as a universal risk template.

Other notebooks should not copy hedge fund-specific VaR, leverage, liquidity, pre-trade, or Annex IV logic unless that logic genuinely applies to the fund type.

---

# 1. Markdown Cell Text

## Goal

Make each notebook read as a professional workflow, not as a regulatory explainer, methodology defence, or training document.

The reader should understand:

1. what fund or workflow is being reviewed
2. what data is being used
3. what risk or reporting output is produced
4. how the output should be interpreted
5. where supporting detail can be found

## Editing Rule

For each markdown cell, keep only the text needed to support the next output.

A good markdown cell should usually answer:

- what is being measured
- which data input or fund parameter drives it
- what the output is used for

Avoid long explanations of concepts that are already visible in the code, table, chart, or linked documentation.

## Tone

Use a confident, practical tone.

Prefer:

> The table below summarises the fund-level risk parameters used in the monitoring workflow.

Avoid:

> This table is important because risk parameters are required to ensure that the fund is monitored in line with its regulatory and internal risk management requirements.

Prefer:

> The calculation uses the fund's RMP parameters and current portfolio snapshot.

Avoid:

> In a production environment, an asset manager would normally rely on third-party systems and internal policies to ensure this type of calculation is correctly implemented.

## Regulatory Text

Keep regulatory context where it changes the interpretation of the output.

Remove repeated or defensive wording such as:

- AIFMD does not prescribe...
- UCITS does...
- CSSF expects...
- in production...
- third-party systems...
- this is only illustrative...
- this would normally be done by...

One short regulatory framing note near the relevant section is enough.

## Hyperlinks Instead of Long Explanations

If a markdown cell starts explaining data architecture, reference-data structure, regulatory framework, or implementation details in depth, shorten it and add a link to the relevant documentation or notebook.

Use short links such as:

```markdown
For details on the data architecture, see the [Data Layer Workflow](../data_workflows/01_data_layer_workflow.ipynb).
````

or:

```markdown
For the accepted reference-data structure, see [Architecture Target](../../docs/ARCHITECTURE_TARGET.md).
```

Do not turn the notebook into a copy of the documentation.

## What to Keep in the Notebook

Keep:

* fund context
* risk parameters used in calculations
* short methodology notes
* formulas that directly support outputs
* interpretation of tables and plots
* limitations that affect the result
* links to supporting docs

Remove or shorten:

* long regulatory summaries
* repeated caveats
* generic textbook definitions
* implementation background already covered elsewhere
* explanations aimed at a naive reader
* vendor/system comparisons unless directly relevant

## Fund-Specific Rule

Do not standardise the risk story across fund types.

Examples:

* Hedge fund: market risk, VaR, ES, backtesting, leverage, liquidity, stress, pre-trade controls.
* Private debt: credit quality, covenant headroom, maturity, yield, borrower concentration, liquidity.
* Real estate: LTV, valuation stress, rental stress, occupancy, property sleeve, listed REIT sleeve where relevant.
* Private equity: IRR, MOIC, DPI, RVPI, unfunded commitments, capital calls, valuation bridge.
* Infrastructure: DSCR, LTV, concession duration, inflation linkage, cash-flow stress.
* UCITS: UCITS-specific eligibility, issuer limits, global exposure, VaR or commitment approach where applicable, PRIIPs/SRI where relevant.

Align style. Do not force the same calculations.

## Review Checklist for Markdown Cells

For each markdown cell, check:

* Is this text needed for the next output?
* Can this be said in one or two sentences?
* Is this regulatory text repeated elsewhere?
* Does this sound like justification rather than workflow narration?
* Would a risk manager or reviewer understand the output without a long explanation?
* Should this detail be moved to a doc and linked instead?
* Does the wording preserve fund-specific treatment?

## Claude Rule

When editing markdown cells:

* edit markdown only
* do not edit code cells
* do not change calculations
* do not change outputs
* do not add new regulatory assumptions
* do not make one fund look like another fund
* keep hyperlinks short and relevant
* preserve formulas where they directly support the output
* report which markdown sections were shortened


