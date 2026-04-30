# Universal background checks — Callaway-Sant'Anna ATT(g, t)

**Date:** 2026-04-30
**Script:** [`scripts/run_cs_ubc.py`](../../scripts/run_cs_ubc.py)
**Output folder:** `outputs/ubc_cs/`

Third policy in the research portion of the project, after
[permitless carry](../permitless_carry_cs/methodology.md) and
[red-flag laws](../red_flag_cs/methodology.md). Same estimator, same
panel, same six outcomes, same four-spec robustness grid. The only
differences are the treatment definition and the strict-rule control
filter.

## Headline numbers (all four specs collapse to 2 unique results)

UBC has a smaller universe of relevant policy variables than carry or
red-flag, so the strict control rule (`universal == 0` AND
`universalpermit == 0` throughout the window) doesn't subset the
never-treated pool further than our base filter already does. As a
result the strict-rule numbers are identical to the broad-rule numbers
in this analysis. We report two specs (OR / RA) instead of four.

Per 100,000 population, post-treatment ATT and pre-trend z. Bold =
pre-trend doesn't reject (clean spec).

| Outcome | OR ATT | OR pre-z | RA ATT | RA pre-z |
|---|---|---|---|---|
| Firearm suicide rate | −0.42 | **+1.3** | **−0.48** | **+0.8** |
| Non-firearm suicide rate | −0.64 | +2.2 (BAD) | −0.45 | +2.2 (BAD) |
| Total suicide rate | **−1.06** | **−0.6** | **−0.93** | **−0.8** |
| Firearm homicide rate | **−0.59** | **+0.4** | −0.58 | −5.9 (BAD) |
| Total homicide rate | −0.39 | **−0.5** | −0.53 | −2.9 (BAD) |
| Motor vehicle theft (placebo) | +38.6 | **+0.4** | +40.8 | +1.8 |

### What the table tells us

**The biggest finding here:** UBC adoption is associated with about
**−1.0 total suicides per 100,000 residents per year**, with clean
pre-trends in both specs (z = −0.6 to −0.8). Firearm suicide alone
falls by ~0.45/100k (clean pre-trend in both specs). This is a
substantively large effect — about 7-9% relative to a typical state's
total suicide rate.

**But the substitution / mechanism story is unusual.** Non-firearm
suicide ALSO falls, by 0.45–0.64 per 100k, with a marginally
significant pre-trend (z = +2.2). UBC has no direct mechanism to
prevent non-firearm suicide. Three possibilities:

1. **Adopting states are also implementing other suicide-prevention
   policies** (mental-health funding, crisis-line investments) at the
   same time. This is a confounder, not a causal effect of UBC alone.
2. **UBC is correlated with a broader cultural shift** in adopting
   states (mostly post-2013 Democratic states) toward gun-policy
   liberalism that includes other suicide-prevention efforts.
3. **Genuine spillover** through unspecified mechanisms (e.g., gun
   removal during BG checks, or broader stigma effects). Unlikely as
   a primary explanation.

**The placebo (motor vehicle theft) fails substantially** at +38 to +40
per 100k with clean pre-trends. This is the same picture as the
permitless-carry analysis but with opposite sign — UBC adopters
(mostly Democratic, post-2013 states) had property-crime trends that
diverged from non-adopters during the 2013-2021 wave. The clean
pre-trend on MVT means the divergence STARTED at adoption, not before;
that's actually a more honest situation than permitless carry's
placebo (which had pre-period AND post-period gaps).

**The firearm homicide finding (−0.59 in OR with clean pre-trend) is
genuinely interesting** — it's about 4× larger in magnitude than the
red-flag firearm-homicide finding (−0.14) and has a similarly clean
pre-trend in the OR spec.

### How to read this honestly

The cleanest possible read: UBC adoption is associated with substantial
declines in firearm suicide AND firearm homicide, with clean
pre-trends. The total-suicide decline is implausibly large for UBC
alone given that non-firearm suicide also drops, suggesting other
co-occurring policies / cultural changes in adopting states are doing
some of the work.

The published literature (e.g., RAND's review of universal background
checks) generally finds NO statistically significant effect on firearm
suicide or homicide. Our finding is much larger and more significant
than typical. The discrepancy likely comes from:

- **Different control groups.** Most published studies use
  synthetic-control or close-pair matching designs that pick
  comparison states more conservatively than our never-treated CS21
  approach.
- **Different time periods.** The 2013-2021 modern UBC wave has more
  available years than studies completed before 2020.
- **Confounding by other policies.** UBC adopters in this wave are
  mostly states that also adopted red-flag laws, magazine bans, etc.
  during the same window. The CS21 estimate captures the joint effect
  of "becoming a UBC state" rather than UBC alone.

**A reviewer would call for at minimum a synthetic-control followup**
(per state) plus controls for concurrent policy adoption. We do not
implement either here.

## Sample

- 8 cohorts, 11 treated states (2013-2021).
- Treated states: DE, CO, NY (2013); WA (2014); OR (2015); NV (2017);
  VT (2018, plus another in 2018); NM (2019); VA (2020); MD (2021).
- Excluded as already-treated (adopted before our analysis window):
  HI 1981, RI 1990, CA 1991, CT 1999.
- Excluded from never-treated pool: states that have universalpermit
  (the permit-mechanism UBC) at any point — primarily MA, IA, IL, MI,
  NJ, NC.
- Never-treated control pool: 32 states.

## Method

Same as the previous policies — see
[`scripts/cs_lib.py`](../../scripts/cs_lib.py) for the shared CS21
machinery and [`scripts/run_cs_permitless_carry.py`](../../scripts/run_cs_permitless_carry.py)
methodology document for the full estimator, bootstrap, and aggregation
details. The only policy-specific knobs:

- Treatment variable: `universal`.
- Treatment direction: `0to1`.
- Strict rule: `universal == 0` AND `universalpermit == 0` for every
  year of `[g-5, g+5]`. (As noted, this didn't change the never-treated
  pool further so the strict-rule numbers equal the broad-rule numbers
  in this build.)

## Comparison to the other two policies in the project

| | Permitless carry | Civil red-flag | UBC |
|---|---|---|---|
| Adopters in sample | 25 states (9 cohorts) | 13 states (5 cohorts) | 11 states (8 cohorts) |
| Adopter profile | Republican states 2010-2024 | Democratic + mixed 2016-2024 | Democratic states 2013-2021 |
| Headline outcome | Firearm suicide +0.6 (clean RA pre-trend) | Firearm homicide −0.14 (clean RA pre-trend) | **Total suicide −1.0 (clean both specs)** |
| Substitution test | Passes (nonfirearm flat, total rises with firearm) | Fails (nonfirearm rises slightly) | Suspicious (nonfirearm also falls) |
| Placebo (MVT) | Fails (significant pre AND post) | Clean pre, significant post | Clean pre, significant post |

**Three policies, three different identification stories.** Permitless
carry has the cleanest substitution test and is the easiest to
interpret causally (firearm suicide rises, total suicide rises, no
substitution). UBC has the largest total-suicide effect but the
substitution test is unusual (non-firearm also falls), suggesting
co-policy confounding. Red-flag has the cleanest single-outcome
finding (firearm homicide) but firearm-suicide is unidentified.

## Outputs

| File | What |
|---|---|
| `att_gt.csv` | One row per (outcome, spec, control_rule, g, t). |
| `event_study.csv` | One row per (outcome, spec, control_rule, event_time). |
| `overall_att.csv` | One row per (outcome, spec, control_rule). |
| `cohort_n.csv` | Cohort sizes. |
| `dropped_log.csv` | States dropped from analysis with reasons. |
| `figures/event_study_{control_rule}_{spec}_4panel.svg` | 4 figures. |

## Recommended next steps for the UBC-specific question

1. **Synthetic control per treated state.** With 11 treated states and
   relatively short post-windows (the 2013 cohort has 10 post-years;
   the 2021 cohort has 2), per-state synthetic counterfactuals would
   be informative.
2. **Controls for concurrent policy adoption.** Several UBC adopters
   (CO, NY, WA, NV, VT, NM, VA, MD) also adopted red-flag laws within
   the same window. A spec that controls for red-flag adoption
   indicator at adoption time would isolate UBC's marginal effect.
3. **Roth-Sant'Anna bounds for the suicide outcomes.** The
   `nonfirearm_suicide_rate` pre-trend (z = +2.2) is mildly suspicious;
   bounds analysis would tell us how robust the substantial declines
   are to that pre-trend.
