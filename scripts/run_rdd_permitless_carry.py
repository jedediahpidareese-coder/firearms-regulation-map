"""Phase 6 spatial RDD: permitless concealed carry.

Treatment: first 1->0 switch in Tufts `law_permitconcealed` (the indicator
that a permit is required for concealed carry; flipping to 0 means the
state went permitless). Joined down to the county panel from the state
panel as `law_permitconcealed`.

Identification: Dube-Lester-Reich (2010, RESTAT) contiguous-county-pair
DiD adapted to firearm policy. County FE + state-pair x year FE; within-
strip sample defined by Census 2020 population centroids (see Section 2.12
of data_appendix.md). Headline bandwidth 100 km (selected per Agent B's
diagnostic on straddling-pair counts), state-cluster SE.

Outcomes: PRIMARY = true county-level Kaplan UCR rates; SECONDARY = state-
joined-down mortality (no within-state county variation, included as
robustness only -- see methodology).

Outputs (under outputs/permitless_carry_rdd/):
    cohort_n.csv         which states adopted in which year
    headline.csv         one row per outcome at the headline spec
    robustness.csv       all 10 BATTERY_SPECS x all outcomes
    event_study.csv      per-outcome event-time coefficients
    figures/event_study_{primary,secondary}.svg

Optional flags:
  --with-covid    append OxCGRT covid_stringency_mean to the covariate
                  set in the headline spec (and every covariate-bearing
                  battery spec); write outputs to
                  permitless_carry_rdd_with_covid/.
  --with-efna     append Fraser Institute efna_overall to the covariate
                  set. Combined with --with-covid, output is
                  outputs/permitless_carry_rdd_with_covid_efna/; alone,
                  outputs/permitless_carry_rdd_with_efna/.
  --with-despair  append the deaths-of-despair stack
                  (synthetic_opioid_death_rate, freq_mental_distress_pct,
                  ami_pct). Combinable with --with-covid and --with-efna;
                  maximal output is permitless_carry_rdd_with_covid_efna_
                  despair/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lib_rdd import (
    load_county_panel_with_borders,
    run_full_battery,
    OUTCOMES_PRIMARY, OUTCOMES_SECONDARY,
)

ROOT = Path(__file__).resolve().parent.parent


def main(with_covid: bool = False, with_efna: bool = False,
         with_despair: bool = False) -> None:
    flag_tokens = []
    if with_covid:   flag_tokens.append("covid")
    if with_efna:    flag_tokens.append("efna")
    if with_despair: flag_tokens.append("despair")
    suffix = ("_with_" + "_".join(flag_tokens)) if flag_tokens else ""
    out_dir = ROOT / "outputs" / f"permitless_carry_rdd{suffix}"
    print("Loading county panel + border distances ...")
    panel = load_county_panel_with_borders()
    print(f"  {len(panel):,} county-year rows")
    flags = []
    if with_covid:   flags.append("with-covid")
    if with_efna:    flags.append("with-efna")
    if with_despair: flags.append("with-despair")
    if flags:
        print(f"[{'+'.join(flags)}] writing outputs to {out_dir.relative_to(ROOT)}")

    summary = run_full_battery(
        panel,
        treatment_var="law_permitconcealed",
        direction="1to0",
        policy_name="permitless_carry",
        out_dir=out_dir,
        outcomes_primary=OUTCOMES_PRIMARY,
        outcomes_secondary=OUTCOMES_SECONDARY,
        with_covid=with_covid,
        with_efna=with_efna,
        with_despair=with_despair,
    )
    print(f"\nDone. Summary: {summary}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-covid", action="store_true",
                        help="Append OxCGRT covid_stringency_mean to the "
                             "headline RDD covariate set; write outputs to "
                             "outputs/permitless_carry_rdd_with_covid/.")
    parser.add_argument("--with-efna", action="store_true",
                        help="Append Fraser Institute efna_overall to the "
                             "headline RDD covariate set. Combined with "
                             "--with-covid, outputs/permitless_carry_rdd_"
                             "with_covid_efna/; alone, "
                             "outputs/permitless_carry_rdd_with_efna/.")
    parser.add_argument("--with-despair", action="store_true",
                        help="Append the deaths-of-despair stack "
                             "(synthetic_opioid_death_rate, "
                             "freq_mental_distress_pct, ami_pct) to the "
                             "headline RDD covariate set. Combinable with "
                             "--with-covid and --with-efna; maximal output "
                             "is outputs/permitless_carry_rdd_with_covid_"
                             "efna_despair/.")
    args = parser.parse_args()
    main(with_covid=args.with_covid, with_efna=args.with_efna,
         with_despair=args.with_despair)
