# Roth-Sant'Anna honest pre-trend bounds for firearm suicide

**Date:** 2026-04-30
**Script:** [`scripts/run_roth_sa_bounds.py`](../../scripts/run_roth_sa_bounds.py)
**Output folder:** `outputs/roth_sa_bounds/`

The two CS21 analyses in this project both produced firearm-suicide
estimates with problematic pre-trends:

- [Permitless carry](../permitless_carry_cs/methodology.md): some
  specifications had pre-trend z-statistics around −1 to −3.5. The two
  cleanest specs (broad/RA and strict/OR) had pre-trend z's that did
  not formally reject zero.
- [Civil-petition red flag](../red_flag_cs/methodology.md): all four
  specifications had pre-trend z's between +4 and +5, consistent with
  an "Ashenfelter dip" — adopting states had rising firearm suicide
  rates BEFORE adoption, which is plausibly the political story that
  produced the law.

Roth & Sant'Anna (2019) and Rambachan & Roth (2023) propose a
sensitivity-analysis framework that lets the reader / reviewer decide
how much pre-trend extrapolation they think is plausible. This
document reports those bounds for each of the four CS21 specifications
× both policies.

## What the bounds say

Because each policy was estimated under four specifications (`OR /
RA × broad / strict`), there are eight separate bound analyses. We
focus on the **first full post-treatment year (event-time e = +1)**
because that's the headline coefficient most readers want.

The sensitivity parameter **M** has the following interpretation:

- **M = 0:** strict parallel-trends assumption. Same CI as the original
  CS21 estimate.
- **M = 1:** assume post-treatment trend deviation is at most as large
  as the linear extrapolation of the observed pre-period trend. A
  natural "neutral" choice — the worst the post-treatment trend could
  do is "look like more of the same".
- **M = 2:** assume post-treatment trend deviation could be up to
  *twice* the magnitude of the observed pre-period trend. A
  conservative, "I don't trust the pre-trend at all" choice.

### Permitless carry, firearm suicide (sign: positive)

| Spec | Original ATT(+1) and CI | M = 1: trend-adjusted ATT and CI | M = 2: trend-adjusted ATT and CI |
|---|---|---|---|
| broad/RA | +0.54 (+0.35, +0.72) | **+0.46 (+0.05, +0.86)** | +0.38 (−0.37, +1.13) |
| strict/RA | +0.49 (+0.28, +0.70) | **+0.48 (+0.12, +0.83)** | +0.47 (−0.14, +1.08) |
| broad/OR | +0.57 (+0.26, +0.87) | +0.38 (−0.11, +0.86) | +0.19 (−0.63, +1.00) |
| strict/OR | +0.45 (+0.14, +0.76) | +0.37 (−0.11, +0.86) | +0.30 (−0.51, +1.10) |

**Permitless-carry firearm suicide effect SURVIVES M = 1** in both RA
specifications: the CI still excludes zero. It only becomes
indistinguishable from zero at M = 2 (extrapolating that the
post-treatment trend deviation could be twice the magnitude of the
observed pre-period one). The OR specs are more fragile and lose
significance at M = 1.

That is the kind of pattern reviewers and editors want to see — a
result with a believable point estimate that survives a plausible
pre-trend bound (M = 1) and only dies under a very conservative one
(M = 2). It supports the headline +0.6/100k finding from the panel
CS21 analysis as a defensible, if cautious, claim.

### Red-flag (civil), firearm suicide (sign: negative)

| Spec | Original ATT(+1) and CI | M = 1: trend-adjusted ATT and CI | M = 2: trend-adjusted ATT and CI |
|---|---|---|---|
| broad/RA | −0.09 (−0.33, +0.16) | +0.19 (−0.39, +0.77) | +0.47 (−0.61, +1.54) |
| strict/RA | −0.34 (−0.66, −0.01) | −0.001 (−0.64, +0.64) | +0.34 (−0.81, +1.48) |
| broad/OR | −0.12 (−0.45, +0.21) | +0.31 (−0.16, +0.78) | **+0.74 (+0.00, +1.47)** |
| strict/OR | −0.14 (−0.49, +0.22) | +0.33 (−0.15, +0.81) | **+0.80 (+0.06, +1.54)** |

**Red-flag firearm suicide effect does NOT survive even M = 1.** All
four specifications return CIs that include zero at M = 1. Worse, at
M = 2 the OR specifications **flip sign and become positive at the
edge of significance** — i.e., if you take the pre-trend at all
seriously and project it forward conservatively, the apparent
"reduction" disappears entirely and could even become a small
"increase" attributed to the policy.

That is consistent with the Ashenfelter-dip interpretation: states
adopted civil red-flag laws because firearm suicide was rising in the
years before adoption. The post-treatment "decline" we measure could
just as well be regression toward the mean — adopting states getting
back to where they would have been without the policy.

This DOES NOT mean civil-petition red-flag laws fail to reduce firearm
suicide. It means the design here cannot tell us either way without
making strong assumptions about post-treatment trends. The published
literature on red-flag laws and firearm suicide (Swanson et al. on
Connecticut and Indiana, RAND meta-reviews) uses much richer
identification strategies (case-by-case court-record matching,
synthetic control with covariates, agent-based models). Those
approaches are out of scope here but ARE the right tools for this
question.

## Method details

For each event-study series:

1. Pull all event-study coefficients ATT(e) and SEs from the
   CS21 build's `event_study.csv`.
2. Fit a weighted linear regression of the pre-period coefficients
   (e ∈ [−5, −2], skipping e = −1 which is the omitted year) on event
   time. Weights are 1 / SE(e)^2 so that less-precise pre-coefs
   contribute proportionally less.
3. Get the slope b̂ and its SE σ̂_b.
4. For each post-period e ≥ 0 and each sensitivity level M ∈ (0, 0.5,
   1.0, 2.0):
   - Trend-adjusted ATT = ATT(e) − M × (e + 1) × b̂
   - 95 % CI half-width = 1.96 × √(SE(e)^2 + (M(e+1))^2 × σ̂_b^2)

We anchor the extrapolation at e = −1 (the omitted-year baseline). The
extrapolated trend at event time e is then (e + 1) × b̂.

The implementation is the *linear extrapolation* version of the
Roth-Sant'Anna framework. The full Rambachan-Roth (2023) procedure
allows non-linear deviations and bounds the maximum absolute deviation
across all post-periods; a publishable application would use that
machinery (their `HonestDiD` R package). The linear version here is a
useful first cut and gives the same qualitative answer for these two
policies.

## Outputs

| File | What |
|---|---|
| `summary_e1.csv` | One row per (policy, control_rule, spec) with the e = +1 numbers across M ∈ {0, 1, 2}. |
| `{policy}_{control_rule}_{spec}_firearm_suicide_rate_bounds.csv` | Full bounds table per spec: one row per (event_time, M). |

## Bottom-line takeaways

- The **permitless-carry firearm-suicide effect** (positive +0.5 to
  +0.6 per 100k) survives moderate pre-trend bounds (M = 1) in both
  RA specifications. This is the strongest causal-style claim in the
  research portion of this project.
- The **red-flag firearm-suicide effect** (negative point estimates
  in every spec) does NOT survive even moderate pre-trend bounds. The
  CS21 results overstate the policy's apparent effect because adopting
  states were on rising firearm-suicide trajectories before adoption.
- The **red-flag firearm-homicide finding** from the cleanest
  specification (broad/RA, ATT = −0.14 with clean pre-trend test)
  remains the most defensible single causal-style claim in the
  project, because it has both the post-treatment significance and the
  clean pre-trend that we'd want before submitting it for review.
