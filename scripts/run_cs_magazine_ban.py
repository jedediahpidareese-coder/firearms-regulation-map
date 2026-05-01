"""Phase 2: Callaway-Sant'Anna ATT(g, t) for state-level large-capacity
magazine (LCM) bans.

Treatment: first 0->1 switch in Tufts `magazine`, the indicator that the
state bans the sale of large-capacity ammunition magazines beyond just
assault-pistol magazines (covers rifle/shotgun magazines too). The
companion variables `tenroundlimit` (10-round-or-less limit, vs the
federal 15-round threshold from 1994-2004) and `magazinepreowned`
(possession ban, not just sale ban) are used only as descriptive context
in the audit; the treatment is the broad sale-ban indicator.

Outcomes (same six as the other policy runs):
  firearm_suicide_rate, nonfirearm_suicide_rate, total_suicide_rate,
  firearm_homicide_rate, homicide_rate, motor_vehicle_theft_rate (placebo).

Headline outcome for LCM bans is `firearm_homicide_rate` and (in v2 of
this project) mass-shooting frequency. The current panel does not
include a state-year mass-shooting outcome, so we report homicide as the
main targeted outcome and flag the mass-shooting omission in the
appendix as a v2 limitation.

Specs (4): {OR, RA} x {broad, strict} where:
  - broad  = every never-treated state (magazine never flips to 1 in
             1999-2024)
  - strict = control state must have magazine == 0 for every year of
             [g-5, g+5] (i.e., truly never-banned across the relevant
             event window).

Outputs:
  outputs/magazine_ban_cs/{att_gt,event_study,overall_att,
                          cohort_n,dropped_log}.csv
  outputs/magazine_ban_cs/figures/event_study_{control_rule}_{spec}_4panel.svg
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cs_lib import (
    OUTCOMES, ANALYSIS_YEARS,
    load_panel_core_augmented, derive_cohorts, strict_control_pool,
    run_one_outcome_all_tiers, event_study_aggregations, overall_att,
    plot_event_study,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "magazine_ban_cs"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# v2 firearm suicide / homicide file ends 2023, so we exclude post-2023 cohorts.
EXCLUDE_COHORTS_AFTER = 2023

# Strict control rule: magazine == 0 every year of [g-5, g+5].
STRICT_RULE_VARS = ("magazine",)
STRICT_RULE_VALUES = (0,)


def main():
    print("Loading panel ...")
    panel = load_panel_core_augmented()
    print(f"  {len(panel):,} state-year rows in {ANALYSIS_YEARS[0]}-{ANALYSIS_YEARS[1]}")

    print("Deriving LCM cohorts (treatment = first 0->1 switch in magazine) ...")
    cohorts, never_treated, dropped = derive_cohorts(
        panel, treatment_var="magazine", direction="0to1",
        min_pre_k=5, exclude_after=EXCLUDE_COHORTS_AFTER,
    )
    print(f"  cohorts: {len(cohorts)} (years {sorted(cohorts)})")
    for g in sorted(cohorts):
        print(f"    {g}: {len(cohorts[g])} states ({', '.join(cohorts[g])})")
    print(f"  never-treated controls (magazine never flips to 1): {len(never_treated)}")
    print(f"  dropped: {len(dropped)}")

    pd.DataFrame([{"g_cohort": g, "n_states": len(s), "states": ",".join(s)}
                  for g, s in sorted(cohorts.items())]
                 ).to_csv(OUT / "cohort_n.csv", index=False)
    pd.DataFrame(dropped).to_csv(OUT / "dropped_log.csv", index=False)

    print("\nstrict-rule control pool size by cohort (magazine==0 throughout [g-5, g+5]):")
    for g in sorted(cohorts):
        strict = strict_control_pool(panel, sorted(never_treated), g,
                                     STRICT_RULE_VARS, STRICT_RULE_VALUES)
        print(f"  {g}: {len(strict)} states ({', '.join(strict[:8])}{'...' if len(strict) > 8 else ''})")

    print("\nRunning ATT(g, t) for each (outcome, spec, control_rule) ...")
    pieces = []
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            for outcome in OUTCOMES:
                print(f"  control_rule={control_rule}  spec={spec}  {outcome}")
                sub = run_one_outcome_all_tiers(panel, outcome, cohorts, never_treated,
                                      spec=spec, control_rule=control_rule,
                                      strict_rule_vars=STRICT_RULE_VARS,
                                      strict_rule_values=STRICT_RULE_VALUES)
                pieces.append(sub)
    att_df = pd.concat(pieces, ignore_index=True)
    att_df.to_csv(OUT / "att_gt.csv", index=False)
    print(f"  Wrote {len(att_df):,} (outcome, spec, control_rule, g, t) rows")

    print("\nAggregating ...")
    es_df = event_study_aggregations(att_df)
    es_df.to_csv(OUT / "event_study.csv", index=False)
    overall_df = overall_att(att_df)
    overall_df.to_csv(OUT / "overall_att.csv", index=False)

    print("\nOverall post-treatment ATT (per 100,000):")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            print(f"\n  --- control_rule = {control_rule},  spec = {spec} ---")
            sub = overall_df[(overall_df["spec"] == spec)
                             & (overall_df["control_rule"] == control_rule)]
            for _, r in sub.iterrows():
                sig = "**" if abs(r["z"]) >= 1.96 else "  "
                print(f"  {sig} {r['outcome']:<26}  ATT = {r['att_overall_post']:>+8.3f}  "
                      f"(SE {r['se_overall_post']:.3f}, z {r['z']:>+5.2f})  "
                      f"pre-trends z = {r['z_pretrends']:>+5.2f}")

    print("\nPlotting event-study figures ...")
    for control_rule in ("broad", "strict"):
        for spec in ("or", "ra"):
            es_filtered = es_df[es_df["control_rule"] == control_rule]
            plot_event_study(es_filtered,
                             FIG / f"event_study_{control_rule}_{spec}_4panel.png",
                             spec, OUTCOMES,
                             title_suffix="-- magazine ban (Tufts magazine)")
            print(f"  Wrote {(FIG / f'event_study_{control_rule}_{spec}_4panel.svg').relative_to(ROOT)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
