"""County-grain Callaway-Sant'Anna ATT(g, t) for universal background checks.

Treatment: a state's first 0->1 switch in the Tufts `law_universal`
indicator (universal background check at point of purchase for ALL
firearms by both licensed dealers and private sellers). Treatment is
treated as absorbing.

Older state UBC laws adopted before our 2009+ panel begins (CA 1991,
CT 1999, HI 1981, RI 1990) are excluded as already-treated. The modern
adoption wave we estimate effects for runs 2014-2021 (CO 2013 has too
short a pre-period under our 5-yr min-pre rule and so falls out).

This is the county-grain parallel of `scripts/run_cs_ubc.py`. The
state-grain runner uses a strict control rule that excludes states
with `universalpermit==1` at any point during [g-5, g+5] (states
that have permit-based UBC, like HI/MA, would otherwise contaminate
the never-treated pool). The county panel does NOT carry
`law_universalpermit` so we cannot enforce that condition here; the
strict rule below uses only `law_universal == 0` throughout the
window. As a result the broad and strict pools coincide on this
panel, and the OR/strict and OR/broad columns will be identical for
every outcome (same for RA). We still emit both columns for output
parity with the state-grain pipeline.

Outcomes (8): five Kaplan UCR county-level rates plus three state-joined-
down mortality rates - see lib_cs_county.OUTCOMES_COUNTY for the list.

Outputs:
  outputs/ubc_cs_county/{att_gt,event_study,overall_att,
                         cohort_n,dropped_log}.csv
  outputs/ubc_cs_county/figures/event_study_{control_rule}_{spec}_4panel.svg
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib_cs_county import (
    OUTCOMES_COUNTY, ANALYSIS_YEARS,
    load_county_panel_2009_2024,
    derive_state_cohorts_for_county, strict_control_pool_county,
    run_one_outcome_county, event_study_aggregations_county,
    overall_att_county, plot_event_study_county,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "ubc_cs_county"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

EXCLUDE_COHORTS_AFTER = 2024

# Strict control: law_universal==0 throughout [g-5, g+5]. (See module
# docstring re: law_universalpermit not being on the county panel.)
STRICT_RULE_VARS = ("law_universal",)
STRICT_RULE_VALUES = (0,)


def main():
    print("Loading county panel ...")
    panel = load_county_panel_2009_2024()
    print(f"  {len(panel):,} county-year rows in "
          f"{ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}, "
          f"{panel['county_fips'].nunique():,} counties, "
          f"{panel['state_fips'].nunique()} states")

    print("Deriving UBC cohorts (treatment = first 0->1 switch in "
          "`law_universal`) ...")
    cohorts, never_treated, dropped = derive_state_cohorts_for_county(
        panel, treatment_var="law_universal", direction="0to1",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        n_states = len(cohorts[g])
        n_counties = panel[panel["state_fips"].isin(cohorts[g])
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        abbrs = [panel[panel["state_fips"] == sf]["state_abbr"].iloc[0]
                 for sf in cohorts[g]]
        print(f"    {g}: {n_states} states ({', '.join(abbrs)}), "
              f"{n_counties} counties")
    print(f"  never-treated controls: {len(never_treated)} states")
    print(f"  dropped: {len(dropped)}")

    cohort_rows = []
    for g, sfs in sorted(cohorts.items()):
        abbrs = [panel[panel["state_fips"] == sf]["state_abbr"].iloc[0]
                 for sf in sfs]
        n_counties = panel[panel["state_fips"].isin(sfs)
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        cohort_rows.append({"g_cohort": g,
                             "n_states": len(sfs),
                             "n_counties": n_counties,
                             "state_fips": ",".join(sfs),
                             "states": ",".join(abbrs)})
    pd.DataFrame(cohort_rows).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort:")
    for g in sorted(cohorts):
        strict = strict_control_pool_county(
            panel, sorted(never_treated), g,
            STRICT_RULE_VARS, STRICT_RULE_VALUES)
        n_counties = panel[panel["state_fips"].isin(strict)
                           & (panel["year"] == g - 1)]["county_fips"].nunique()
        print(f"  {g}: {len(strict)} states / {n_counties} counties")

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule) ...")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome in OUTCOMES_COUNTY:
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome_county(
                    panel, outcome, cohorts, never_treated,
                    spec=spec, control_rule=control_rule,
                    strict_rule_vars=STRICT_RULE_VARS,
                    strict_rule_values=STRICT_RULE_VALUES)
                pieces.append(sub)
    att_df = pd.concat(pieces, ignore_index=True)
    att_df.to_csv(OUT / "att_gt.csv", index=False)
    print(f"  Wrote {len(att_df):,} (outcome, spec, control_rule, g, t) rows")

    print("\nAggregating ...")
    es_df = event_study_aggregations_county(att_df)
    es_df.to_csv(OUT / "event_study.csv", index=False)
    overall_df = overall_att_county(att_df)
    overall_df.to_csv(OUT / "overall_att.csv", index=False)

    print("\nOverall post-treatment ATT (per 100,000):")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            print(f"\n  --- control_rule = {control_rule},  spec = {spec} ---")
            sub = overall_df[(overall_df["spec"] == spec)
                             & (overall_df["control_rule"] == control_rule)]
            for _, r in sub.iterrows():
                sig = "**" if abs(r["z"]) >= 1.96 else "  "
                print(f"  {sig} {r['outcome']:<32}  "
                      f"ATT = {r['att_overall_post']:>+10.3f}  "
                      f"(SE {r['se_overall_post']:.3f}, z {r['z']:>+6.2f})  "
                      f"pre-trends z = {r['z_pretrends']:>+5.2f}")

    print("\nPlotting event-study figures ...")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            es_filtered = es_df[es_df["control_rule"] == control_rule]
            plot_event_study_county(
                es_filtered,
                FIG / f"event_study_{control_rule}_{spec}_4panel.svg",
                spec, OUTCOMES_COUNTY,
                title_suffix="-- universal background checks (law_universal)")
            print(f"  Wrote "
                  f"{(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
