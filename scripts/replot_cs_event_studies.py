"""Quick one-off: regenerate the CS21 + RDD event-study SVGs for all
policies using the existing event_study.csv outputs. Use this whenever
the plotter changes (e.g. the 2026-05-01 tier-filter fix and dot-and-
whisker refactor) without re-running the full estimator pipelines.
"""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
import pandas as pd
from cs_lib import plot_event_study, OUTCOMES
from lib_rdd import plot_event_study_svg as plot_rdd_es, OUTCOMES_PRIMARY, OUTCOMES_SECONDARY
from lib_cs_county import plot_event_study_county, OUTCOMES_COUNTY

ROOT = Path(__file__).resolve().parent.parent
POLICIES = [
    "permitless_carry", "red_flag", "ubc",
    "stand_your_ground", "magazine_ban", "age21_handgun", "assault_weapons_ban",
]

def main() -> None:
    print("=== CS21 event-study replot ===")
    for policy in POLICIES:
        csv = ROOT / "outputs" / f"{policy}_cs" / "event_study.csv"
        if not csv.exists():
            print(f"  skip (no event_study.csv): {policy}")
            continue
        es_df = pd.read_csv(csv)
        figs = ROOT / "outputs" / f"{policy}_cs" / "figures"
        figs.mkdir(exist_ok=True)
        for control_rule in ("broad", "strict"):
            for spec in ("or", "ra"):
                sub = es_df[es_df["control_rule"] == control_rule]
                out = figs / f"event_study_{control_rule}_{spec}_4panel.svg"
                title = f"-- {policy.replace('_', ' ')}"
                plot_event_study(sub, out, spec, OUTCOMES, title_suffix=title)
                print(f"  wrote {policy}/{out.name}")

    print("\n=== RDD event-study replot ===")
    for policy in POLICIES:
        csv = ROOT / "outputs" / f"{policy}_rdd" / "event_study.csv"
        if not csv.exists():
            print(f"  skip (no rdd event_study.csv): {policy}")
            continue
        es_df = pd.read_csv(csv)
        figs = ROOT / "outputs" / f"{policy}_rdd" / "figures"
        figs.mkdir(exist_ok=True)
        title = f"({policy}, primary outcomes)"
        plot_rdd_es(es_df, figs / "event_study_primary.svg",
                    OUTCOMES_PRIMARY, title_suffix=title)
        print(f"  wrote {policy}/event_study_primary.svg")
        title = f"({policy}, secondary outcomes)"
        plot_rdd_es(es_df, figs / "event_study_secondary.svg",
                    OUTCOMES_SECONDARY, title_suffix=title)
        print(f"  wrote {policy}/event_study_secondary.svg")

    print("\n=== Stacked-DD event-study replot ===")
    for policy in POLICIES:
        csv = ROOT / "outputs" / f"{policy}_stackdd" / "event_study.csv"
        if not csv.exists():
            print(f"  skip (no stackdd event_study.csv): {policy}")
            continue
        es_df = pd.read_csv(csv)
        figs = ROOT / "outputs" / f"{policy}_stackdd" / "figures"
        figs.mkdir(exist_ok=True)
        # Bridge column shape: stacked-DD CSV has (outcome, spec, tier,
        # event_time, beta, se, ...). cs_lib.plot_event_study expects "att"
        # and "control_rule"; bridge accordingly.
        bridged = es_df.rename(columns={"beta": "att"}).assign(control_rule="single")
        # Tier-aware filtering (mirrors run_stacked_dd.py logic).
        for spec_name in ("unweighted", "ra", "eb"):
            if "tier" in bridged.columns:
                tier_filter = "all" if spec_name == "unweighted" else "headline"
                sub = bridged[(bridged["spec"] == spec_name) & (bridged["tier"] == tier_filter)]
            else:
                sub = bridged[bridged["spec"] == spec_name]
            if sub.empty:
                continue
            out = figs / f"event_study_{spec_name}_4panel.svg"
            title = f"-- {policy.replace('_', ' ')}"
            plot_event_study(sub, out, spec_name, OUTCOMES, title_suffix=title)
            print(f"  wrote {policy}_stackdd/{out.name}")

    print("\n=== County-CS21 event-study replot ===")
    for policy in ("permitless_carry", "red_flag", "ubc"):
        csv = ROOT / "outputs" / f"{policy}_cs_county" / "event_study.csv"
        if not csv.exists():
            print(f"  skip (no county_cs event_study.csv): {policy}")
            continue
        es_df = pd.read_csv(csv)
        figs = ROOT / "outputs" / f"{policy}_cs_county" / "figures"
        figs.mkdir(exist_ok=True)
        for control_rule in ("broad", "strict"):
            for spec in ("or", "ra"):
                sub = es_df[es_df["control_rule"] == control_rule]
                out = figs / f"event_study_{control_rule}_{spec}_4panel.svg"
                title = f"-- {policy.replace('_', ' ')} (county grain)"
                plot_event_study_county(sub, out, spec, OUTCOMES_COUNTY, title_suffix=title)
                print(f"  wrote {policy}_cs_county/{out.name}")


if __name__ == "__main__":
    main()
