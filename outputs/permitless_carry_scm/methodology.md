# Synthetic control: Texas 2021 and Florida 2023

**Date:** 2026-04-30
**Script:** [`scripts/run_scm_permitless_carry.py`](../../scripts/run_scm_permitless_carry.py)
**Output folder:** `outputs/permitless_carry_scm/`

This is a sanity check on the Callaway-Sant'Anna ATT(g, t) results in
[`outputs/permitless_carry_cs/methodology.md`](../permitless_carry_cs/methodology.md).
The CS21 result, averaged across nine adoption cohorts and 25 treated
states, said **firearm suicide ATT ≈ +0.6 per 100k** with clean
pre-trends in two of four specifications. SCM looks at the two largest
single-state cohorts individually so we can see, transparently, what the
counterfactual looks like for one place at a time.

## Headline numbers

Per-state, per-outcome treatment effects measured as the post-period
average of (treated − synthetic counterfactual). The placebo p-value
comes from a permutation test: refit SCM on every donor state as if it
were the treated unit and ask how many of those placebos produce an
absolute post-period effect ≥ the actual one. Two-sided test, no
distributional assumption.

### Texas, adoption 2021 (post-window 2021–2023, 3 years)

| Outcome | Post-period effect | Placebo p | Pre-period RMSE |
|---|---|---|---|
| Firearm suicide rate     | **+0.47** per 100k | 0.40 | 0.19 |
| Firearm homicide rate    | −0.35 per 100k | 0.50 | 0.18 |
| Total homicide rate      | −0.22 per 100k | 0.80 | 0.21 |
| Motor vehicle theft (placebo) | −37 per 100k | 0.90 | 14 |

### Florida, adoption 2023 (post-window 2023, 1 year only)

| Outcome | Post-period effect | Placebo p | Pre-period RMSE |
|---|---|---|---|
| Firearm suicide rate     | −0.04 per 100k | 1.00 | 0.26 |
| Firearm homicide rate    | −0.38 per 100k | 0.46 | 0.43 |
| Total homicide rate      | −0.48 per 100k | 0.64 | 0.71 |
| Motor vehicle theft (placebo) | −262 per 100k | 0.000 | 111 |

### What this says

- **The Texas firearm-suicide effect is in the right direction (+0.47)
  but not significant under the SCM placebo test.** With only three
  post-treatment years and a donor pool of 10 states, individual-state
  power is genuinely limited. The CS21 panel's +0.6 estimate gets its
  power from pooling across cohorts; one cohort by itself can't
  distinguish from the donor-state noise.
- **The Texas placebo (motor vehicle theft) is correctly insignificant
  (p = 0.90).** That's a good sanity check on this design — unlike the
  CS21 panel where the property-crime trend gap loaded on every
  cohort, the synthetic counterfactual built from shall-issue donor
  states tracks Texas's pre-period MVT well enough that the post-period
  divergence is unremarkable.
- **Florida should not be interpreted.** Only one post-treatment year
  (2023). The MVT placebo p = 0.000 likely reflects something
  Florida-specific in 2023 (hurricane displacement on insurance claims,
  population flux from out-of-state migration, etc.) rather than the
  carry policy. Treat FL 2023 as a baseline-fit sanity check and revisit
  in 2026 when 2024–2025 outcomes are available.

**Honest read:** SCM cannot, on its own, confirm or refute the
firearm-suicide signal from the CS21 panel. It does add one important
piece of evidence: the Texas effect, taken alone, is consistent in
direction but not large relative to what other shall-issue states do
year-to-year. The pooled-cohort CS21 result remains the strongest
piece of evidence we have produced; SCM is a cautionary footnote
to it.

## Sample and method details

### Donor pool (audit-style strict rule, fixed across time)

For each treated state and adoption year *g*, the donor pool is the set
of states that:

- Never adopted permitless carry within 1999–2023.
- Are shall-issue (`mayissue == 0`) AND require a permit
  (`permitconcealed == 1`) for **every year** in the panel window
  [max(g − 12, 1999), 2023]. (Pool must be fixed across time as SCM
  requires.)

For TX 2021 the pool is 10 states: CO, MI, MN, NC, NM, NV, OR, PA, VA, WA.
For FL 2023 the pool is 11 states: CO, MI, MN, NC, NM, NV, OR, PA, VA, WA, WI.
WI gains eligibility for FL 2023 because its shall-issue switch happened
in 2011, and the FL window starts 2011 (= 2023 − 12).

### Weights

We solve

> w* = argmin ||y_pre − Y_pre · w||² subject to w ≥ 0 and Σ w = 1

via SLSQP from `scipy.optimize`, using five Dirichlet-random initial
points plus the uniform start to escape local optima. We do **not**
match on covariates (only on the pre-period outcome itself); this is
the simplest SCM and is the standard starting point.

### Permutation inference

For every donor state *d* in the pool we refit SCM treating *d* as
"treated" with the remaining donors as the new pool, and compute its
post-period (treated − synthetic) effect. The p-value is the share of
donors whose absolute placebo effect is ≥ the actual treated state's
absolute effect. With ~10 donors the smallest possible p-value is
≈ 1/10 = 0.10 (so a p of 0.10 is the equivalent of "ranks first";
p = 0.40 is "fourth out of ten").

## Recommended next steps

The Texas 2021 result is suggestive but underpowered. Two things would
help:

1. **Wait for more post-data.** The 2024 firearm suicide / homicide
   numbers from the v2 file aren't out yet (file ends 2023). Once
   2024 (and ideally 2025) are added, the TX post-window grows from
   3 years to 5 years and the SCM placebo test gains real power.
2. **Augmented synthetic control (ASC; Ben-Michael, Feller, Rothstein,
   2021)** for the TX case. Adds a regression-based bias correction
   on top of the SCM weights and tends to materially reduce the
   placebo p-value when pre-period fit is good.

## Outputs

| Path | What |
|---|---|
| `TX_2021/weights.csv` | Donor weights per outcome for Texas |
| `TX_2021/trajectories.csv` | Year-by-year actual, synthetic, and effect |
| `TX_2021/placebo.csv` | Permutation-test p-values per outcome |
| `TX_2021/figures/{outcome}.svg` | One SVG figure per outcome |
| `FL_2023/...` | Same files for Florida |
