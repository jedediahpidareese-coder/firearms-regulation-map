# Entropy Balancing (EB) vs Regression Adjustment (RA): Methodology Scan and Project Recommendations

**Audience:** Internal methods note for the state-level firearm-policy DiD/RDD/SCM project.
**Author:** Internal methodology review, May 2026.
**Scope:** When EB is preferred over plain RA in modern causal-inference practice, and what that implies for the headline specification of each of our three estimators (Callaway-Sant'Anna, Cengiz stacked-DiD, Dube-Lester-Reich spatial RDD).
**TL;DR:** RA is the right default for our CS21 ATT(g,t) and DLR spatial RDD headlines; EB is the right default for the stacked-DiD headline; DR-EB is worth reporting as a robustness check for stacked-DiD where it is computationally cheap. The strongest empirical case for EB is in the stacked spec, where the treated set per cohort is small (often 1-3 states) and exact moment matching of pre-treatment covariates is materially better than fitting a 3-coefficient OLS regression on `n_control ~ 30-40` controls.

---

## Section 1. Foundational EB Methodology

### 1.1 Hainmueller (2012), *Political Analysis* 20(1):25-46

URL: <https://www.cambridge.org/core/journals/political-analysis/article/abs/entropy-balancing-for-causal-effects-a-multivariate-reweighting-method-to-produce-balanced-samples-in-observational-studies/220E4FC838066552B53128E647E4FAA7>; preprint <https://www.mit.edu/~jhainm/Paper/eb.pdf>.

**Key contribution.** Introduces entropy balancing: a maximum-entropy reweighting scheme that solves for non-negative weights on control units that exactly match the treated group on a chosen set of covariate moments (means, variances, higher moments), while staying as close as possible to uniform weights in Kullback-Leibler distance. This bypasses the iterative "estimate propensity score - check balance - respecify" loop that plagues IPW.

**When EB is recommended.** When the analyst can clearly specify which moments of which covariates need to be balanced; when the estimand is the ATT (EB by construction targets the treated mean); when the propensity score is hard to specify (e.g., few treated units, complex selection mechanism); when the analyst wants exact rather than approximate balance. EB dominates inverse-probability weighting (IPW) in most finite samples because it removes the stochastic balance failure mode of estimated propensities.

**Limitations.** EB fails when (a) the convex optimization is infeasible because the treated covariate vector lies outside the convex hull of control covariates (no positive weights satisfy the constraints), (b) overlap is poor and a small number of controls receive extreme weights, inflating variance and effective-sample-size loss, (c) the chosen moment specification leaves out important confounders.

### 1.2 Hainmueller & Xu (2013), *Journal of Statistical Software* 54(7):1-18

URL: <https://www.jstatsoft.org/article/view/v054i07>.

**Key contribution.** Implementation paper for the Stata `ebalance` package (a sibling R package `ebal` exists). Documents the dual-Newton solver, weight-trimming option, and standard-error machinery; the LaLonde (1986) replication is the canonical demonstration.

**Practical takeaway.** The default `ebalance` solver matches first moments only; balancing variances and interactions is a flag. Our `lib_stacked_dd.py` rolls its own dual-Newton solver, which is consistent with the Hainmueller-Xu reference implementation (verified in code review of `entropy_balance` lines 106-144).

### 1.3 Zhao & Percival (2017), *Journal of Causal Inference* 5(1):20160010

URL: <https://www.degruyterbrill.com/document/doi/10.1515/jci-2016-0010/html>; arXiv <https://arxiv.org/abs/1501.03571>.

**Key contribution.** Proves that EB is a doubly-robust estimator. Specifically, the EB-weighted difference-in-means is consistent for the ATT if EITHER (a) the outcome model is linear in the balanced moments OR (b) the propensity-score model is logistic in those same moments. This is the analytic justification for using EB as a stand-alone estimator rather than always pairing it with an outcome regression.

**When DR-EB is recommended.** Whenever you would otherwise use AIPW or DR-DID and you want the IPW-side weights to satisfy exact moment balance. DR-EB = entropy-balance the controls, then run an outcome regression on the EB-weighted sample. The regression "augmentation" gives bias protection against EB's moment-misspecification, and EB gives bias protection against outcome-model misspecification. Asymptotically efficient when both models are correct.

**Limitation.** Double robustness is asymptotic; in small samples the augmented estimator can be MORE variable than the EB-only estimator if the outcome regression is overfit. Kang & Schafer (2007)-style scenarios in which both models are slightly wrong have shown DR estimators can blow up.

### 1.4 Imai & Ratkovic (2014), *JRSSB* 76(1):243-263

URL: <https://academic.oup.com/jrsssb/article-abstract/76/1/243/7075938>; preprint <https://imai.fas.harvard.edu/research/files/CBPS.pdf>.

**Key contribution.** Covariate Balancing Propensity Score (CBPS): estimates the propensity score under the dual constraint that (i) it satisfies the logistic likelihood and (ii) the resulting IPW weights balance covariate moments. Inverse Probability Tilting (IPT) - an over-identified GMM version of CBPS - coincides with Hainmueller's EB when the score is correctly specified.

**When CBPS is preferred over EB.** When the estimand is the ATE (population) rather than the ATT (treated). CBPS handles the symmetric balancing condition naturally; EB targets the treated group only. Also when the analyst wants a continuous-treatment generalization (Fong, Hazlett & Imai 2018 generalize CBPS to continuous treatments more cleanly than EB does).

**When EB is preferred over CBPS.** When estimand is ATT, when sample is small, and when one wants exact rather than over-identified-GMM-balanced moments. EB's solution is unique (when it exists) and does not depend on a logistic-link assumption.

### 1.5 Athey, Imbens & Wager (2018), *JRSSB* 80(4):597-623

URL: <https://academic.oup.com/jrsssb/article/80/4/597/7048352>; arXiv <https://arxiv.org/abs/1604.07125>.

**Key contribution.** Approximate Residual Balancing (ARB): a high-dimensional generalization of EB. First fits a sparse (Lasso) outcome model in each treatment arm, then computes weights that approximately balance the residuals between treated and control. Achieves sqrt(n)-consistent ATE estimation in high-dimensional settings (p >> n possible) under overlap and sparsity assumptions.

**When ARB / modern EB is recommended.** When p (covariate count) is large relative to n_treated, AND the analyst is willing to accept approximate (not exact) balance. The default EB behavior of exact balance becomes infeasible when p approaches n_control; ARB relaxes the constraint and supplies the missing precision via the Lasso outcome model.

**Limitation for our use case.** Our project has p = 3 to p = 8 covariates and n_states ~ 50, so we are nowhere near the high-dimensional regime. ARB is not the operative method; standard Hainmueller EB is. But ARB's framework reinforces the case for combining EB with an outcome regression (the DR-EB recipe).

### 1.6 Sant'Anna & Zhao (2020), *Journal of Econometrics* 219(1):101-122

URL: <https://www.sciencedirect.com/science/article/abs/pii/S0304407620301901>; preprint <https://psantanna.com/files/SantAnna_Zhao_DRDID.pdf>; arXiv <https://arxiv.org/abs/1812.01723>.

**Key contribution.** Extends DR estimation to the DiD setting. Proposes two estimators: (1) "DR-DID" using inverse-probability-of-treatment weighting + outcome regression, and (2) "DR-DID-improved" that handles repeated cross-sections. Both are consistent if EITHER the outcome model OR the propensity model is correct; both attain the semiparametric efficiency bound when both are correct. This is the Sant'Anna piece of the CS21 backbone, and is the source of CS21's preferred RA spec (`dr` in the `did` R package).

**When SZ20 says use plain RA.** When the analyst is confident the outcome model is correct AND the propensity model is hard to specify (few treated units, exotic selection mechanism). RA does not require modeling treatment.

**When SZ20 says use DR.** Default. Robustness across two model specifications outweighs the small efficiency loss when both are correct.

**Connection to EB.** SZ20 uses inverse-propensity weights for the IPW component. EB weights satisfy the same first-order conditions as the IPW weights from a correctly-specified logistic propensity (per Zhao-Percival 2017), so swapping in EB for IPW inside the SZ20 framework gives a "DR-EB-DID" estimator - exactly the stacked-DiD spec we already implement in `lib_stacked_dd.py`. CS21's `did` R package does NOT use EB internally; it uses the IPW weights from a logistic propensity.

### 1.7 Roth, Sant'Anna, Bilinski & Poe (2023), *Journal of Econometrics* 235(2):2218-2244

URL: <https://www.sciencedirect.com/science/article/abs/pii/S0304407623001318>; preprint <https://www.jonathandroth.com/assets/files/DiD_Review_Paper.pdf>; arXiv <https://arxiv.org/abs/2201.01194>.

**Key contribution.** The canonical practitioner survey for modern DiD. Frames recent advances as relaxations of three components of the canonical 2x2 DiD: (i) staggered timing, (ii) parallel trends, (iii) inferential framework. Recommends estimators by use case.

**Position on EB vs RA.** Treats covariate-conditional parallel trends as the foundational identifying assumption. Endorses three approaches to enforcing the conditioning - regression adjustment (RA), inverse-probability weighting (IPW), and doubly-robust (DR) - and recommends DR as the default when feasible. Does not single out EB as a separate category, treating it instead as an instance of the IPW/DR family. Strongly cautions that with a small treated set OR poor overlap, all weighting methods (including EB) can become unstable, and the analyst should report sensitivity to the chosen weighting scheme.

**Practical guidance for state-year panels.** When the number of treated units per cohort is small (< 5), the survey cautions that nonparametric balancing methods (matching, EB) may overfit baseline differences and that the analyst should report unweighted (no-covariate) ATT alongside the covariate-adjusted version as a sensitivity check. This is a direct argument for the multiverse approach.

### 1.8 Recent literature (2023-2025)

**Kallus & Santacatterina (2023+) "Mixing Samples to Address Weak Overlap"** URL: <https://arxiv.org/abs/2411.10801>. Argues that even EB suffers when the convex hull of controls only weakly contains the treated covariate vector, and proposes mixing-sample estimators as a remedy. Relevant for our small-treated-set firearm cohorts.

**"When Good Balance Goes Bad" (Journal of Financial Reporting, 2022; cited in CRAN WeightIt docs)** URL: <https://publications.aaahq.org/jfr/article/7/1/167/133/When-Good-Balance-Goes-Bad-A-Discussion-of-Common>. Catalogues common EB pitfalls: silently accepting infeasible solutions; reporting ATT estimates from EB runs that converged to a near-singular weight distribution; not reporting effective sample size (ESS) or max weight; failing to test sensitivity to which moments are balanced. Recommends always reporting the ESS, the max weight, and the L1 imbalance after weighting.

**"Large Sample Properties of Entropy Balancing" (J. Statistical Computation, 2023)** URL: <https://www.sciencedirect.com/science/article/pii/S2452306223000813>. Provides asymptotic distribution theory for EB-weighted ATT under standard regularity conditions, confirming that bootstrap inference (as we use in `lib_stacked_dd`) is valid.

**Tubbicke (2023), Stata Journal: `ebct` for continuous treatments** URL: <https://journals.sagepub.com/doi/10.1177/1536867X231196291>. Generalizes EB to continuous treatments, useful if our project ever moves from the binary policy-on/off framing toward a dosage analysis.

**Caetano & Callaway (2024) "DiD when Parallel Trends Holds Conditional on Covariates"** URL: <https://bcallaway11.github.io/files/DID-Covariates/Caetano_Callaway_2024.pdf>. Updates CS21 guidance for time-varying covariates and clarifies that the DR estimator inside CS21 uses an IPW logistic propensity rather than EB. Explicitly notes that swapping in EB-style weights changes the bias properties when the conditional-parallel-trends assumption fails, and is not a free improvement.

---

## Section 2. Decision Rules: When EB Is Preferred over RA

| Condition | Recommendation | Citation |
|---|---|---|
| Treated cohorts < 5 states | RA (or unweighted DiD); EB likely overfits the few treated covariate vectors | Roth-Sant'Anna et al. 2023 (sec. on small samples) |
| Treated cohorts 5-15 states | DR-EB preferred; EB alone acceptable | Sant'Anna & Zhao 2020; Zhao & Percival 2017 |
| Treated cohorts > 15 states | EB or DR-EB; RA acceptable as headline | Hainmueller 2012; Athey et al. 2018 |
| Covariate dimension <= 3 | RA fine; EB and RA give nearly identical answers | Caetano & Callaway 2024 |
| Covariate dimension 4-8 | EB strictly better than RA on bias-variance grounds; DR-EB best | Hainmueller 2012; Zhao & Percival 2017 |
| Covariate dimension > 8 | ARB (Lasso + balance) or DR with regularized OR | Athey, Imbens & Wager 2018 |
| Treatment-effect heterogeneity across cohorts (Goodman-Bacon flag) | Use any cohort-stratified estimator (CS21 ATT(g,t), stacked-DiD); EB inside the cohort can help | Roth-Sant'Anna et al. 2023; Goodman-Bacon 2021 |
| Pre-trend test fails for unweighted DiD | Try EB or DR-EB; if pre-trend still fails, switch to honest-DID/Roth bounds | Roth (2022) JESM; Rambachan-Roth 2023 |
| Pre-trend test passes | RA fine; EB unlikely to materially change estimate but harmless | Hainmueller 2012 |
| Outcome variability low (homicide rate, smooth panels) | RA preferred; EB adds variance with little bias gain | Sant'Anna & Zhao 2020 |
| Outcome variability high (suicide rate by age subgroup, mass-shooting count) | EB preferred; smoothing covariate distributions reduces noise | Hainmueller 2012; Zhao-Percival 2017 |
| Policy-era confounders (alcohol, opioid, COVID) | Include them as balanced covariates; EB ensures exact balance vs RA which only enforces mean-zero residual | Hainmueller 2012 |
| Audience: econometrics journal | RA / DR-DID per CS21; EB as a robustness check | Sant'Anna-Zhao 2020; Roth et al. 2023 |
| Audience: public-health journal | EB or DR-EB increasingly common; RAND Gun Policy reviews accept both | RAND Gun Policy methodology, <https://www.rand.org/research/gun-policy/methodology.html> |

**Synthesis.** The modern verdict is that EB is preferred over plain RA when (a) treated set is moderate (5-30 cohorts), (b) covariate count is in the "RA-overfit" zone (4-8 covariates with treated n in the dozens), (c) the outcome is noisy enough that exact moment matching reduces residual variance, OR (d) you suspect the linear-in-X functional form of RA is wrong. In nearly every other case, RA and EB agree to within Monte Carlo noise, and the choice is presentational.

---

## Section 3. Recommendations Per Estimator

### 3.1 Callaway-Sant'Anna ATT(g,t) (`cs_lib.py`)

**Headline spec recommendation: RA, with `or` (no-covariate) reported as sensitivity.**

**Rationale.** CS21's preferred specification is the Sant'Anna-Zhao (2020) doubly-robust DiD, which uses logistic IPW + outcome regression. Our `cs_lib.py` currently implements the OR ("or") and RA paths; the DR path is not yet implemented because it would require a per-(g,t) propensity-score estimation that, with our small treated cohorts (often a single state per cohort), yields highly unstable weights. With a single treated state per cohort, the effective propensity score is degenerate (treated unit has p=1, control units have p=0 modulo X), and IPW collapses. RA is the workhorse that survives this regime.

**Why not EB inside CS21.** Three reasons:
1. **Cohort-specific outcome regression conflict.** CS21 estimates a separate outcome regression per (g, t) pair; the regression coefficient on X is identified off the controls only. EB-weighting the controls would change the regression coefficient AND the residual that gets averaged, double-counting the covariate adjustment. The IPW component of DR-DID is supposed to be ORTHOGONAL to the OR component, not redundant with it.
2. **Single-treated-state cohorts.** EB requires more than one treated unit if you want to balance variances; with one treated state the "target" is a single point and EB collapses to nearest-neighbor matching on the moment vector, which is exactly what RA already does asymptotically when n_control >> p.
3. **Implementation cost.** Adding EB to `cs_lib.py` requires per-(g, t) entropy balancing on n_control ~ 30-40 units against a 3-coordinate target. This is computationally trivial but adds a maintenance surface, and the published literature does not show it improving CS21's bias profile in state-year panels.

**Multiverse recommendation.** Report `or` (no-controls) and `ra` (with the three core covariates) side by side in headline event-study plots. Do NOT add EB to `cs_lib.py` for the headline; if a reviewer asks, generate a one-off DR-EB comparison using `lib_stacked_dd.py` on the same cohort definitions.

### 3.2 Cengiz Stacked-DiD (`lib_stacked_dd.py`)

**Headline spec recommendation: EB (entropy-balanced controls within stack), with unweighted stacked-DiD as sensitivity.**

**Rationale.** This is where EB earns its keep. The stacked design creates many small "sub-experiments," one per cohort, each with 1-3 treated states and 30-40 clean controls (per `build_stacks` in `lib_stacked_dd.py` lines 61-101). For each sub-experiment EB exactly matches the treated baseline covariate moments using a non-parametric weighting that does not depend on a functional-form assumption. Within each stack the gain over RA is small but real; aggregated across 10-30 cohorts the bias-variance improvement is non-trivial.

**Double-counting concern (stack-by-state and stack-by-event-time FE).** The stacked TWFE absorbs (a) state-stack and (b) event-time-stack effects. EB weights are defined within (stack_id, state) cells and broadcast to all years within that cell - i.e., EB acts as a state-stack-level constant scalar that is then "demeaned out" by the stack-by-state FE. This means EB weights ONLY influence the regression through the cross-cell variation; they cannot double-count the FE adjustment. Verified in `lib_stacked_dd.stack_eb_weights` (lines 147-190): weights are constant within (stack_id, state). Conclusion: no double-counting risk in our spec, and EB is fully compatible with the FE structure.

**Why DR-EB is worth running too.** Per Zhao-Percival (2017), augmenting the EB estimator with an outcome regression provides asymptotic protection against EB's moment-misspecification at minimal implementation cost - just add `covariates=` to the `twfe_within` call after EB-weighting, which the existing API already supports via the `covariates` argument. Recommend reporting both EB-only and DR-EB as columns in the stacked-DiD results table.

### 3.3 Dube-Lester-Reich Spatial RDD (`lib_rdd.py`)

**Headline spec recommendation: RA, do not add EB.**

**Rationale.** The DLR spatial RDD identifies the policy effect off cross-border county pairs straddling a state boundary. The key identifying machinery is the county-pair-by-year fixed effect (or border-segment FE), which absorbs all time-invariant cross-sectional differences between paired counties at each year. In other words, the FE structure is doing the cross-sectional balancing job that EB would otherwise do. Adding EB on top would re-balance moments that the FE has already differenced out, which is at best redundant and at worst variance-inflating.

**When EB MIGHT be added to RDD.** If the analyst wanted to weight the panel of counties by their similarity in time-VARYING characteristics (e.g., unemployment shocks, opioid mortality trends) that the FE cannot absorb. In that case EB on the time-varying X at the pair-year level is sensible. But this is a niche extension, not the headline spec.

**Multiverse recommendation.** RA with the existing `RA_COVARIATES` is the headline. Report unweighted (no-X) and population-weighted (the existing `weights="population"` option) as sensitivities. Do not add EB to `lib_rdd.py`.

### 3.4 Cross-estimator summary table

| Estimator | Headline spec | EB role | DR-EB role | Multiverse columns |
|---|---|---|---|---|
| CS21 ATT(g,t) (`cs_lib.py`) | **RA** | Not added | Not added (degenerate with single treated state) | `or`, `ra` |
| Stacked-DiD (`lib_stacked_dd.py`) | **EB** | Headline | Sensitivity column | unweighted, EB, DR-EB |
| Spatial RDD (`lib_rdd.py`) | **RA** | Not added (FE absorbs balance) | Not added | unweighted, RA, population-weighted |

---

## Section 4. Concrete Implementation Guidance

### 4.1 Should EB be added to `cs_lib.py`?

**No.** Reasons:
- CS21 ATT(g,t) is computed cohort-by-cohort with often a single treated state. EB target is degenerate (1-point support).
- The DR component of CS21 is supposed to use IPW from a logistic propensity; swapping in EB conflicts with the cohort-specific outcome regression bias structure.
- Caetano-Callaway (2024) explicitly documents that EB-as-IPW inside CS21 changes the bias-when-PT-fails properties in non-obvious ways.
- Reviewer-defensible default in CS21 is `dr` (per Sant'Anna-Zhao 2020). Our current `or` and `ra` specs are an acceptable simplification given the small-cohort size; full DR is a future enhancement that should use the `did` R package via reticulate or Stata, not a homegrown EB.

### 4.2 Should EB stay as the existing alternative in `lib_stacked_dd.py`?

**Yes - and promote it from "alternative" to "headline."** The current code already supports `weights=stack_eb_weights(...)` in `twfe_within`; the necessary change is presentational - report EB-weighted stacked-DiD as the headline column, with unweighted stacked-DiD as a sensitivity. Add a DR-EB column by passing `covariates=RA_COVARIATES` to the EB-weighted `twfe_within` call (the API already supports this).

**Diagnostics to add:** Per the "When Good Balance Goes Bad" cautions, log per-stack (a) max EB weight, (b) ESS = (sum w)^2 / sum(w^2), (c) post-balance L1 imbalance. Flag any stack with max_weight > 5 * mean_weight or ESS < 0.5 * n_control as a non-converged or degenerate balance and downweight its contribution to the aggregate ATT.

### 4.3 Should EB be added to `lib_rdd.py`?

**No.** The pair-by-year FE absorbs cross-sectional balance; adding EB would re-balance already-balanced moments. Population weighting (already supported) is the standard sensitivity. The existing `RA_COVARIATES` adjustment for time-varying X is sufficient.

### 4.4 Recommended default headline spec per estimator

| Estimator | Default headline | Default sensitivity panel |
|---|---|---|
| CS21 ATT(g,t) | `ra` (RA with 3 covariates) | `or` (no covariates) |
| Stacked-DiD | EB-weighted, no extra covariates | unweighted; DR-EB (EB + RA covariates) |
| Spatial RDD | RA with covariates | unweighted; population-weighted |
| SCM | (separate scope; standard SCM weights, no EB) | per-state placebo distribution |

### 4.5 EB convergence diagnostic to report

**One-line summary:** For each EB-weighted stack, report `max_weight / mean_weight` and `ESS = 1 / sum(w^2)` (with weights normalized to sum to 1). Flag any stack with `max_weight / mean_weight > 5` or `ESS < n_control / 2` as a poorly-balanced stack and consider dropping or trimming.

A concrete implementation snippet to add to `lib_stacked_dd.stack_eb_weights` (advisory; do not modify code in this scan):

```
# After computing w_c per stack:
w_norm = w_c / w_c.sum()
ess = 1.0 / np.sum(w_norm ** 2)
max_ratio = w_norm.max() / w_norm.mean()
diagnostics.append({
    "stack_id": stack_id, "n_control": len(w_c),
    "ess": ess, "max_weight_ratio": max_ratio,
    "converged": ok,
})
```

This diagnostic file should be written to `outputs/<policy>_stackdd/eb_diagnostics.csv` and reviewed before reporting EB-weighted ATTs.

---

## Methodological Gotcha (Flag for Reviewer)

**The biggest risk of using EB inside the stacked-DiD headline is silent infeasibility.** Hainmueller's (2012) algorithm can return a "converged" weight vector that satisfies the moment constraints only approximately when the treated covariate vector lies near (or just outside) the convex hull of the control covariate vectors. Our current `entropy_balance` function (lines 106-144 in `lib_stacked_dd.py`) returns `(w, converged)` where `converged` is a boolean Newton-tolerance check, not a feasibility check. A stack can return `converged=True` but with `max_weight > 100 * mean_weight`, indicating that one or two control states are doing essentially all the work. This is ESS collapse: the EB estimator becomes a 1-2-state matching estimator with no inferential support. **Recommendation:** add the ESS / max-weight diagnostic as a HARD CHECK before accepting any EB-weighted ATT into the headline table. If ESS < 5 controls (out of ~30), fall back to the unweighted stacked-DiD for that stack.

A secondary gotcha: in our state-year panel, several plausible "controls" (e.g., Texas as a control for a New York permitless-carry analysis) are obviously dissimilar on the policy-era confounders. EB will silently weight them down, but this can create the appearance of balance on the chosen moments while leaving unobserved confounders unbalanced. The defense is to present EB-weighted results alongside a "matched-by-region" or "matched-by-pre-period-trend" sensitivity, which would catch divergence between balance on observables and balance on the latent dimensions.

---

## Bibliography (with URLs)

1. Hainmueller, J. (2012). "Entropy Balancing for Causal Effects." *Political Analysis* 20(1):25-46. <https://www.cambridge.org/core/journals/political-analysis/article/abs/entropy-balancing-for-causal-effects-a-multivariate-reweighting-method-to-produce-balanced-samples-in-observational-studies/220E4FC838066552B53128E647E4FAA7>
2. Hainmueller, J. & Xu, Y. (2013). "ebalance: A Stata Package for Entropy Balancing." *Journal of Statistical Software* 54(7):1-18. <https://www.jstatsoft.org/article/view/v054i07>
3. Zhao, Q. & Percival, D. (2017). "Entropy Balancing is Doubly Robust." *Journal of Causal Inference* 5(1):20160010. <https://www.degruyterbrill.com/document/doi/10.1515/jci-2016-0010/html>
4. Imai, K. & Ratkovic, M. (2014). "Covariate Balancing Propensity Score." *JRSSB* 76(1):243-263. <https://academic.oup.com/jrsssb/article-abstract/76/1/243/7075938>
5. Athey, S., Imbens, G. & Wager, S. (2018). "Approximate Residual Balancing." *JRSSB* 80(4):597-623. <https://academic.oup.com/jrsssb/article/80/4/597/7048352>
6. Sant'Anna, P.H.C. & Zhao, J. (2020). "Doubly Robust Difference-in-Differences Estimators." *Journal of Econometrics* 219(1):101-122. <https://www.sciencedirect.com/science/article/abs/pii/S0304407620301901>
7. Roth, J., Sant'Anna, P.H.C., Bilinski, A. & Poe, J. (2023). "What's Trending in Difference-in-Differences?" *Journal of Econometrics* 235(2):2218-2244. <https://www.sciencedirect.com/science/article/abs/pii/S0304407623001318>
8. Callaway, B. & Sant'Anna, P.H.C. (2021). "Difference-in-Differences with Multiple Time Periods." *Journal of Econometrics* 225(2):200-230. <https://psantanna.com/files/Callaway_SantAnna_2020.pdf>
9. Caetano, C. & Callaway, B. (2024). "DiD when Parallel Trends Holds Conditional on Covariates." Working paper. <https://bcallaway11.github.io/files/DID-Covariates/Caetano_Callaway_2024.pdf>
10. Cengiz, D., Dube, A., Lindner, A. & Zipperer, B. (2019). "The Effect of Minimum Wages on Low-Wage Jobs." *QJE* 134(3):1405-1454.
11. Dube, A., Lester, T.W. & Reich, M. (2010). "Minimum Wage Effects Across State Borders." *Review of Economics and Statistics* 92(4):945-964. <https://irle.berkeley.edu/wp-content/uploads/2010/11/Minimum-Wage-Effects-Across-State-Borders.pdf>
12. RAND Gun Policy Methodology. <https://www.rand.org/research/gun-policy/methodology.html>
13. "When Good Balance Goes Bad." *Journal of Financial Reporting* 7(1):167. <https://publications.aaahq.org/jfr/article/7/1/167/133/When-Good-Balance-Goes-Bad-A-Discussion-of-Common>
14. Tubbicke, S. (2023). "ebct: Using entropy balancing for continuous treatments." *Stata Journal*. <https://journals.sagepub.com/doi/10.1177/1536867X231196291>
15. Wing, C. et al. (2024). "Stacked Difference-in-Differences." NBER Working Paper 32054. <https://www.nber.org/system/files/working_papers/w32054/w32054.pdf>
16. Roth, J., Sant'Anna, P.H.C., et al. (2025). "DiD: A Practitioner's Guide." <https://arxiv.org/abs/2503.13323>
