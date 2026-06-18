# Redemption Framework Audit & Harmonization Report

## Current Situation

### 1. Two Separate Redemption Frameworks

#### A. RMP Redemption Scenarios (`risk_policy.json`)
**Location:** `reference_data/funds/{FUND}/risk_policy.json`

**Current structure:**
```json
"redemption_scenarios": [
  {"name": "Base", "redemption_pct": 0.05},
  {"name": "Large", "redemption_pct": 0.15},
  {"name": "Stress", "redemption_pct": 0.25},
  {"name": "Largest investor", "redemption_pct": "largest_investor"}
]
```

**Characteristics:**
- Simple point-in-time scenarios
- **No investor-type breakdown** (Retail, Institutional, Family Office)
- No model parameters (beta distribution, concentration)
- Used in notebook Section 4 (one-off stress test)

#### B. Calibration Config (`liquidity_calibration_inputs.json`)
**Location:** `reference_data/funds/{FUND}/liquidity_calibration_inputs.json`

**Current structure:**
```json
"investors": [
  {
    "type": "Retail",
    "weight": 0.40,
    "base_redemption_rate": 0.030,
    "stress_redemption_rate": 0.120
  },
  {
    "type": "Institutional",
    "weight": 0.45,
    "base_redemption_rate": 0.040,
    "stress_redemption_rate": 0.180
  },
  {
    "type": "Family Office",
    "weight": 0.15,
    "base_redemption_rate": 0.020,
    "stress_redemption_rate": 0.100
  }
]
```

**Characteristics:**
- Investor-type breakdown with weights
- Static base/stress rates per investor type
- **No beta distribution parameters**
- Used in notebook Sections 5-6 (dynamic monthly path modeling)

---

## Issues Identified

### Issue 1: RMP Lacks Investor-Type Breakdown
**Problem:** The RMP scenarios (5%, 15%, 25%) are atomic values with no explanation of *who* redeems under stress.

**Why this matters:** 
- Regulatory documentation should justify the stress scenarios
- Without investor-type breakdown, it's unclear why 15% is "Large" vs. why another fund might use 20%
- The scenarios appear arbitrary

### Issue 2: Calibration Config Has Static Rates Instead of Beta Parameters
**Problem:** The calibration uses fixed `base_redemption_rate` and `stress_redemption_rate` per investor type, but the notebook actually **models redemptions using a beta distribution** (not these fixed rates).

**Evidence from notebook:**
```python
# Section 9-10: Beta distribution is used
"redemption_concentration": 6.0,  # Alpha/beta parametrization
"seed": 42
```

The beta distribution parameters (`redemption_concentration = 6.0`) define the *shape* of the redemption distribution, not the fixed rates.

**Why this matters:**
- The fixed rates in calibration config are **not actually used** in the dynamic modeling
- This creates confusion: which parameters are authoritative?
- The beta model is more flexible (can model tail risk, fat tails) than fixed rates

### Issue 3: No Alignment Between Two Frameworks
**Problem:** RMP scenarios and calibration assumptions are independent.

**Example:** 
- RMP says "Stress = 25% redemption"
- Calibration says weighted average stress = (0.40 × 0.12) + (0.45 × 0.18) + (0.15 × 0.10) = **13.9%**
- These don't match, so unclear which is "correct"

**Why this matters:**
- Board reporting may cite RMP scenarios (25%)
- Risk monitoring may cite calibration averages (13.9%)
- Regulatory reporting may cite either
- Inconsistency creates audit/governance risk

---

## Questions & Doubts

### Q1: What should be the source of truth for redemption stress levels?

**Current state:**
- RMP has 5%, 15%, 25%
- Calibration investor-weighted average is ~4%, ~14%, ~13.9%

**Question:** Should we:
- Use RMP as primary (simpler, clearer for board)?
- Use calibration as primary (richer, investor-based)?
- Create a third canonical framework that feeds both?

### Q2: Should beta distribution parameters be explicit in calibration config?

**Current state:**
- Calibration config has `"redemption_concentration": 6.0` (beta alpha/beta parametrization)
- But also has static `base_redemption_rate` and `stress_redemption_rate` (not used in model)

**Question:** Should we:
- Add explicit beta parameters (e.g., `beta_alpha`, `beta_beta`, or `concentration`)?
- Remove the static rates (since they're not used)?
- Document which parameters are actually used vs. legacy?

### Q3: Should RMP include investor-type breakdown?

**Current state:**
- RMP is simple (one value per scenario)
- Calibration has investor types

**Question:** Should RMP:
- Stay simple (one aggregated value per scenario)?
- Include investor-type breakdown for transparency?
- Include both (aggregated + breakdown)?

### Q4: How should dynamic modeling (beta) and point-in-time stress (RMP) relate?

**Current state:**
- RMP scenarios are arbitrary stress levels
- Dynamic model uses beta distribution + weighted investor types
- No clear link between them

**Question:**
- Should point-in-time stress scenarios be *derived* from beta distribution percentiles?
  - E.g., "Base = 25th percentile of monthly redemption dist., Large = 75th, Stress = 99th"?
- Or should they remain independent (policy-driven) stress tests?

### Q5: What is the intended purpose of each framework?

**Current assumptions (from notebook structure):**
- RMP: One-off regulatory/board-level stress tests (Section 4)
- Calibration: Investor-behavior-based dynamic modeling (Sections 5-6)

**Question:** Is this correct? Should they serve different purposes, or should one subsume the other?

---

## Proposed Direction (For Discussion)

### Option 1: RMP as Primary, Calibration Derived
- RMP defines the canonical stress scenarios (5%, 15%, 25%)
- Calibration config derives investor-type breakdown from RMP
  - E.g., if RMP = 15%, distribute proportionally by investor-type stress rates
- Beta distribution parameters explicitly stated in calibration
- Both use same data source (RMP)

**Pros:** Simpler, single source of truth, clearer governance  
**Cons:** Loses investor-type detail in RMP

### Option 2: Calibration as Primary, RMP Derived
- Calibration config is the source of truth
- RMP scenarios computed as aggregates from calibration
  - E.g., Base = weighted average of investor base rates (4%)
  - Large, Stress = percentiles or weighted averages
- Beta distribution parameters explicit in calibration
- RMP becomes a summary, not independent

**Pros:** Richer, investor-based, easier to justify  
**Cons:** RMP scenarios may not align with historical policy

### Option 3: Unified Redemption Framework File
- Create `reference_data/regulation/redemption_framework.json`
  - Contains investor types, stress scenarios, beta parameters
  - One authoritative source
- Both RMP and calibration reference this
- No duplication

**Pros:** Single source of truth, no duplication  
**Cons:** Requires refactoring, may break existing workflows

---

## Recommendations for Next Steps

1. **Clarify intent:** Should RMP and calibration serve different purposes, or be unified?
2. **Document beta parametrization:** Make it explicit which parameters are used (concentration, alpha, beta, mean, variance)
3. **Align scenarios:** Ensure point-in-time stress scenarios map to beta distribution assumptions
4. **Remove unused fields:** If `base_redemption_rate` and `stress_redemption_rate` aren't used in the model, either use them or remove them
5. **Add validation:** Cross-check RMP scenarios against calibration assumptions in notebook or data-loading code

---

## Files Involved

- `reference_data/funds/{FUND}/risk_policy.json` - RMP redemption scenarios
- `reference_data/funds/{FUND}/liquidity_calibration_inputs.json` - Calibration assumptions
- `notebooks/liquidity_management/liquidity_management.ipynb` - Where both are used
- `src/data/reference_data.py` - Loading functions
- `src/computation/liquidity.py` - Beta distribution model
