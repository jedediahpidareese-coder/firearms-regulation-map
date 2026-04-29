# Permitless Carry and Suicide Feasibility Audit

Date: 2026-04-29

## Recommendation

Revise the design before any manuscript drafting. The current candidate question is important, but the present design should not be used for a causal paper. The audit produces two warning signs: the estimated association is not firearm-specific, and the joint pretrend tests reject for the main firearm suicide outcomes. The literature check also narrows the novelty claim because recent work already studies concealed-carry license requirements and, in some cases, permitless carry directly.

The candidate should be treated as paused unless a revised design can pass the mechanism and pretrend checks.

## Reproducibility

Script:

- `scripts/audit_permitless_carry_suicide.py`

Main output folder:

- `outputs/permitless_carry_suicide_audit/`

Generated files:

- `analysis_config.json`
- `analysis_panel_summary.csv`
- `average_post_results.csv`
- `calendar_restriction_results.csv`
- `cohort_year_estimates.csv`
- `event_study_coefficients.csv`
- `figure_index.csv`
- `joint_pretrend_tests.csv`
- `leave_one_early_adopter_out_results.csv`
- `outcome_summary.csv`
- `sample_membership_by_treated_state.csv`
- `stacked_sample_main.csv`
- `treated_state_estimates.csv`
- `treatment_adoption_table.csv`
- `figures/event_study_*.svg`

## Treatment Definition

The treatment variable is `permitconcealed` from the Tufts-based state firearm law panel in `data/processed/panel_core_1979_2024.csv`.

The adoption rule is the first observed state-year transition from `permitconcealed == 1` to `permitconcealed == 0`. The interpretation is repeal of a concealed-carry permit requirement, or adoption of permitless concealed carry. The adoption year is treated as event time 0. The script uses the annual law coding as given and does not prorate partial-year effective dates.

Treatment is modeled as absorbing after first adoption. The audit table checks reversals after adoption. In the current data, all 26 treated states with adoption through 2023 remain coded as permitless through 2024.

Treated states through the suicide-data endpoint:

| State | Adoption year |
| --- | ---: |
| Alabama | 2023 |
| Alaska | 2003 |
| Arizona | 2010 |
| Arkansas | 2021 |
| Florida | 2023 |
| Georgia | 2022 |
| Idaho | 2016 |
| Indiana | 2022 |
| Iowa | 2021 |
| Kansas | 2015 |
| Kentucky | 2019 |
| Maine | 2015 |
| Mississippi | 2015 |
| Missouri | 2017 |
| Montana | 2021 |
| Nebraska | 2023 |
| New Hampshire | 2017 |
| North Dakota | 2017 |
| Ohio | 2022 |
| Oklahoma | 2019 |
| South Dakota | 2019 |
| Tennessee | 2021 |
| Texas | 2021 |
| Utah | 2021 |
| West Virginia | 2016 |
| Wyoming | 2011 |

Louisiana and South Carolina adopt in 2024 in the law panel but are outside the current suicide-outcome endpoint, so they are not treated units in this analysis.

## Sample Definition

The base analysis panel contains 2,250 observations: 50 states by 45 years, 1979-2023. DC is excluded because the core law panel is a 50-state panel.

The main stacked sample contains 4,446 state-stack-year observations across 40 states and 26 treated-state adoption stacks. The event window is -5 to +3. Post-Bruen years are included in the main sample because 2022 and 2023 are in the mortality panel. A separate robustness check excludes post-Bruen calendar years by truncating the analysis at 2021.

For each treated-state stack, comparison states must satisfy both conditions in every event-window year:

- `permitconcealed == 1`
- `mayissue == 0`

This limits the donor pool to licensed shall-issue states. May-issue states are excluded from the comparison group. Later adopters can serve as controls only when they remain licensed shall-issue throughout the focal treated state's event window.

## Outcome Construction

The suicide outcomes are built by merging `data/firearm_suicide_homicide_dataset_v2.tab` to the core panel. The mortality file supplies `firearm_suicides` and `total_suicides`; nonfirearm suicides are constructed as total suicides minus firearm suicides.

Rates use the annual `population` denominator from the core panel:

- `firearm_suicide_rate = 100000 * firearm_suicides / population`
- `nonfirearm_suicide_rate = 100000 * nonfirearm_suicides / population`
- `total_suicide_rate = 100000 * total_suicides / population`
- `firearm_suicide_share = firearm_suicides / total_suicides`

Logged rate outcomes add `0.01` before logging. The logit firearm-share outcome uses a continuity correction: `log((firearm_suicides + 0.5) / (nonfirearm_suicides + 0.5))`.

The analysis panel has no missing firearm suicide counts and no missing total suicide counts for 1979-2023.

## Estimation Details

The main specification is a stacked difference-in-differences/event-study design. Each treated state receives its own stack identifier. The average post-treatment model is:

```text
y_ist = beta * post_ist + X_st gamma + state-by-stack FE + year-by-stack FE + error_ist
```

The event-study model replaces `post_ist` with treated-state event-time indicators for event times -5, -4, -3, -2, 0, 1, 2, and 3. Event time -1 is omitted.

Controls in the core specification:

- `ln_population`
- `unemployment_rate`
- `ln_pcpi_real_2024`
- `violent_rate`
- `property_rate`

The audit also saves models without controls and models adding `per_capita_alcohol_ethanol_14plus`.

Standard errors are clustered by state abbreviation. No weights are used.

## Main Results

Core-control average post estimates:

| Outcome | Estimate | SE | p-value |
| --- | ---: | ---: | ---: |
| Firearm suicide rate | 0.407 | 0.121 | 0.001 |
| Nonfirearm suicide rate | 0.204 | 0.113 | 0.071 |
| Total suicide rate | 0.611 | 0.157 | 0.000 |
| Firearm suicide share | 0.000 | 0.005 | 0.938 |
| Log firearm suicide rate | 0.023 | 0.011 | 0.039 |
| Log nonfirearm suicide rate | 0.022 | 0.015 | 0.160 |
| Log total suicide rate | 0.024 | 0.009 | 0.006 |
| Logit firearm suicide share | 0.002 | 0.019 | 0.919 |

The positive log firearm-suicide result is not matched by a change in the firearm share of suicides. The point estimate for nonfirearm suicide is also positive and similar in magnitude. This weakens the proposed access-to-firearms mechanism.

## Diagnostics

Event-study coefficient table:

- `event_study_coefficients.csv`

Event-study figures:

- `figures/event_study_firearm_suicide_rate.svg`
- `figures/event_study_nonfirearm_suicide_rate.svg`
- `figures/event_study_total_suicide_rate.svg`
- `figures/event_study_firearm_suicide_share.svg`
- `figures/event_study_ln_firearm_suicide_rate.svg`
- `figures/event_study_ln_nonfirearm_suicide_rate.svg`
- `figures/event_study_ln_total_suicide_rate.svg`
- `figures/event_study_logit_firearm_suicide_share.svg`

Joint pretrend tests use event times -5, -4, -3, and -2. The pretrend test rejects for firearm suicide rate, total suicide rate, log firearm suicide rate, and log total suicide rate.

| Outcome | Chi-square | df | p-value |
| --- | ---: | ---: | ---: |
| Firearm suicide rate | 15.925 | 4 | 0.003 |
| Nonfirearm suicide rate | 4.615 | 4 | 0.329 |
| Total suicide rate | 14.138 | 4 | 0.007 |
| Firearm suicide share | 5.088 | 4 | 0.278 |
| Log firearm suicide rate | 13.108 | 4 | 0.011 |
| Log nonfirearm suicide rate | 6.153 | 4 | 0.188 |
| Log total suicide rate | 12.835 | 4 | 0.012 |
| Logit firearm suicide share | 5.035 | 4 | 0.284 |

Calendar restrictions:

| Sample | Outcome | Estimate | SE | p-value |
| --- | --- | ---: | ---: | ---: |
| Exclude 2020-2023 | Log firearm suicide rate | 0.022 | 0.016 | 0.166 |
| Exclude 2020-2023 | Log nonfirearm suicide rate | 0.013 | 0.019 | 0.515 |
| Exclude 2020-2023 | Log total suicide rate | 0.017 | 0.011 | 0.132 |
| Exclude 2020-2023 | Logit firearm suicide share | 0.010 | 0.026 | 0.702 |
| Exclude post-Bruen years | Log firearm suicide rate | 0.028 | 0.013 | 0.039 |
| Exclude post-Bruen years | Log nonfirearm suicide rate | 0.023 | 0.018 | 0.194 |
| Exclude post-Bruen years | Log total suicide rate | 0.026 | 0.010 | 0.013 |
| Exclude post-Bruen years | Logit firearm suicide share | 0.005 | 0.022 | 0.816 |

Excluding 2020-2023 weakens the main estimates. Excluding only post-Bruen years does not restore a firearm-share mechanism.

Cohort-specific and treated-state-specific estimates are saved in:

- `cohort_year_estimates.csv`
- `treated_state_estimates.csv`
- `leave_one_early_adopter_out_results.csv`

The cohort estimates are heterogeneous and sometimes point in opposite directions. For example, the Wyoming 2011 cohort has a negative log-firearm-suicide estimate, while Alaska 2003 and Idaho/West Virginia 2016 are positive. This reinforces the concern that a pooled post coefficient is not enough to sustain a manuscript.

## Literature Check

Goh, Fleegler, and Siegel (2026) substantially overlaps with this project. Their JAMA Network Open article analyzes 50 states from 1976 to 2024 and includes six laws, one of which is "laws requiring permits for concealed carry" or the opposite of permitless carry. The article reports that concealed-carry license requirements are associated with an 8.9 percent lower firearm suicide rate and no corresponding nonfirearm-suicide association. They use a two-year lag, state and year fixed effects, age-adjusted firearm suicide rates, nonfirearm suicide as a negative-control outcome, and Tufts law data.

This means a simple state-panel claim that concealed-carry permit requirements reduce firearm suicide is not novel. A project here would need to contribute through design rather than topic alone.

Other overlapping work:

- Schell et al. (2024) estimate firearm-mortality effects for several policy classes, including concealed carry and allowing concealed carry without a permit, using Bayesian panel methods over 1979-2019.
- Grimsley et al. (2024) study transition to permitless open carry using 2013-2021 state-level data and report associations with firearm-related suicide.
- Lundstrom, Pence, and Smith (2023) study West Virginia's 2016 permitless concealed-carry law and find higher firearm mortality after enactment.
- McCourt (2018) is a Johns Hopkins dissertation that directly examines concealed carry and suicide, including permitless laws, with 1980-2015 data. It reports harmful permitless-carry effects but notes the limited number of permitless states before 2015.

What remains potentially novel:

- A focused post-2015, multi-state permitless concealed-carry design rather than omnibus law scoring.
- A strict donor rule comparing adopters only with licensed shall-issue states, excluding may-issue states from the comparison group.
- Event-study diagnostics and explicit firearm-share mechanism tests.
- Inclusion of the large 2021-2023 adoption wave, including post-Bruen sensitivity checks.

That novelty is currently not enough, because the local estimates fail the mechanism and pretrend diagnostics.

## Bottom Line

Do not draft the paper yet. The current candidate should be revised or abandoned. A revised design would need at minimum age-adjusted mortality outcomes from CDC WONDER or NVSS, stronger time-varying confounders, exact effective-date handling or exposure prorating, and a design that produces firearm-specific effects without rejected pretrends. If those checks fail again, the better move is to abandon permitless-carry suicide as the main paper and pivot to a different question.

## Sources Checked

- Goh M, Fleegler EW, Siegel M. 2026. "State Gun Laws and Firearm Suicide Rates." JAMA Network Open. https://pubmed.ncbi.nlm.nih.gov/41920544/
- Schell TL, Smart R, Cefalu M, Griffin BA, Morral AR. 2024. "State Policies Regulating Firearms and Changes in Firearm Mortality." JAMA Network Open. https://pubmed.ncbi.nlm.nih.gov/39083273/
- Grimsley EA, Torikashvili JV, Janjua HM, Read MD, Kuo PC, Diaz JJ. 2024. "Transition to Permitless Open Carry and Association with Firearm-Related Suicide." Journal of the American College of Surgeons. https://pubmed.ncbi.nlm.nih.gov/38465793/
- Lundstrom EW, Pence JK, Smith GS. 2023. "Impact of a Permitless Concealed Firearm Carry Law in West Virginia, 1999-2015 and 2016-2020." American Journal of Public Health. https://doi.org/10.2105/AJPH.2023.307382
- McCourt AD. 2018. "Concealed Carry of Firearms in the United States: A Public Health Law Analysis of State Policy and State Suicide Mortality." Johns Hopkins University dissertation. https://jscholarship.library.jhu.edu/items/97f604de-3201-44e2-a5e1-1657b6d9e8c3
