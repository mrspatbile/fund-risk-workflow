### 2. Investor Base Model – Redemption Schedule

The redemption schedule is derived from a fund-level **investor register** and calibration inputs. Each investor type has an AUM share and separate redemption assumptions for normal and stressed conditions.

| Notation | Meaning |
|---|---|
| $w_i$ | AUM share of investor type $i$ ($\sum_i w_i = 1$) |
| $\mu_i^{\text{norm}}$ | Monthly redemption rate under normal conditions |
| $\mu_i^{\text{stress}}$ | Monthly redemption rate under stress conditions |
| $\kappa$ | Concentration parameter controlling dispersion around the normal rate |

#### Normal months – beta-distributed draws

For months not designated as stress months, each investor type draws from a beta distribution centred on its normal redemption rate. The beta distribution is used because:

- It keeps redemption rates strictly bounded between 0 and 1
- The concentration parameter $\kappa$ controls dispersion symmetrically around the mean
- Higher $\kappa$ produces more concentrated (stable) monthly draws
- Lower $\kappa$ produces more dispersed (volatile) draws

The beta parameters are derived from the normal rate and concentration:

$$\alpha_i = \mu_i^{\text{norm}} \cdot \kappa$$

$$\beta_i = (1 - \mu_i^{\text{norm}}) \cdot \kappa$$

With this parametrisation:

$$X_{i,t} \sim \text{Beta}(\alpha_i, \beta_i), \quad \mathbb{E}[X_{i,t}] = \mu_i^{\text{norm}}$$

The aggregate monthly redemption rate is the AUM-weighted sum across investor types:

$$r_t = \sum_{i=1}^{N} w_i \cdot X_{i,t}$$

#### Stress months – deterministic override

For designated stress months $t \in \mathcal{S}$, the model uses the stressed redemption rate directly:

$$r_t = \sum_{i=1}^{N} w_i \cdot \mu_i^{\text{stress}}$$

This represents a deterministic stress scenario rather than a random draw. The stress months and stressed rates are fund-level calibration inputs.

#### Reference rates

The normal and stressed reference rates are the weighted averages:

$$r^{\text{norm,wt}} = \sum_i w_i \cdot \mu_i^{\text{norm}}$$

$$r^{\text{stress,wt}} = \sum_i w_i \cdot \mu_i^{\text{stress}}$$

These provide a benchmark for the simulated redemption path.