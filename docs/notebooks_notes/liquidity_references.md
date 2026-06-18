# Liquidity workflow notes

This note supports the liquidity management notebook. It explains the calibration inputs used to build the dynamic redemption path and how those inputs differ from the RMP redemption shocks.

## 1. RMP redemption shocks and calibration inputs

The liquidity notebook uses two different redemption inputs.

| Input                 | Purpose                             | Used in                                               |
| --------------------- | ----------------------------------- | ----------------------------------------------------- |
| RMP redemption shocks | Point-in-time policy shocks         | Static redemption stress checks at the valuation date |
| Calibration inputs    | Investor-type behaviour assumptions | Monthly redemption path simulation                    |

The RMP shocks are policy scenario values. They are applied directly as point-in-time redemption shocks.

The calibration inputs are modelling assumptions. They are used to estimate how redemption pressure may evolve over several months, based on the composition of the investor base.

## 2. Investor base model

The redemption path is derived from the fund investor register and calibration inputs. Each investor type has an AUM share and separate redemption assumptions for normal and stressed conditions.

| Notation                | Meaning                                                                 |
| ----------------------- | ----------------------------------------------------------------------- |
| $w_i$                   | AUM share of investor type $i$, with $\sum_i w_i = 1$                   |
| $\mu_i^{\text{norm}}$   | Monthly redemption rate for investor type $i$ under normal conditions   |
| $\mu_i^{\text{stress}}$ | Monthly redemption rate for investor type $i$ under stressed conditions |
| $\kappa$                | Concentration parameter controlling dispersion around the normal rate   |

The aggregate redemption rate is the AUM-weighted sum of investor-type redemption rates.

## 3. Normal months

For months not designated as stress months, each investor type draws from a beta distribution centred on its normal redemption rate.

The beta distribution is used because it keeps simulated redemption rates between 0 and 1 and allows the dispersion around the normal rate to be controlled through $\kappa$.

The beta parameters are:

$$
\alpha_i = \mu_i^{\text{norm}} \cdot \kappa
$$

$$
\beta_i = (1 - \mu_i^{\text{norm}}) \cdot \kappa
$$

The simulated redemption rate for investor type $i$ in month $t$ is:

$$
X_{i,t} \sim \text{Beta}(\alpha_i, \beta_i)
$$

with:

$$
\mathbb{E}[X_{i,t}] = \mu_i^{\text{norm}}
$$

The aggregate monthly redemption rate is:

$$
r_t = \sum_{i=1}^{N} w_i \cdot X_{i,t}
$$

## 4. Stress months

For designated stress months, the model uses the stressed redemption rate for each investor type directly.

For stress months $t \in \mathcal{S}$:

$$
r_t = \sum_{i=1}^{N} w_i \cdot \mu_i^{\text{stress}}
$$

This creates a deterministic stress month within the dynamic path. The stress months and stressed rates are calibration inputs.

## 5. Reference rates

The normal and stressed weighted reference rates are:

$$
r^{\text{norm,wt}} = \sum_i w_i \cdot \mu_i^{\text{norm}}
$$

$$
r^{\text{stress,wt}} = \sum_i w_i \cdot \mu_i^{\text{stress}}
$$

These rates provide benchmarks for the simulated redemption path.

## 6. Relation to the notebook

The dynamic redemption path is not a monthly extension of the RMP redemption shocks.

RMP redemption shocks are point-in-time policy scenarios. Calibration inputs define investor-type behaviour used in the dynamic path simulation.

The path is then used to assess how liquidity coverage, deferred redemptions and LMT triggers evolve over time.
