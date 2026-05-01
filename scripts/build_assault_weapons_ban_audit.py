"""Phase 1 — assault-weapons-ban (AWB) cohort construction.

Treatment variable: Tufts `assault` (an indicator that the state bans
the sale of assault weapons beyond just assault pistols, covering
long guns). Direction: 0->1.

Builds outputs/assault_weapons_ban_audit/treatment_adoption_table.csv,
mirroring the layout of the permitless_carry audit's table.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "assault_weapons_ban_audit"
OUT.mkdir(parents=True, exist_ok=True)

ANALYSIS_LO, ANALYSIS_HI = 1999, 2023
MIN_PRE_K = 5  # CS21 requires this many pre-period years


def first_transition(values, direction="0to1"):
    """Return the year of the first 0->1 (or 1->0) transition in a list of
    (year, value) tuples, or None if none observed."""
    prev = None
    for y, v in values:
        if pd.isna(v):
            continue
        if prev is not None:
            if direction == "0to1" and prev == 0 and v == 1:
                return int(y)
            if direction == "1to0" and prev == 1 and v == 0:
                return int(y)
        prev = v
    return None


def all_reversals(values):
    """All 1->0 transition years (post-adoption reversals)."""
    out = []
    prev = None
    for y, v in values:
        if pd.isna(v):
            continue
        if prev == 1 and v == 0:
            out.append(int(y))
        prev = v
    return out


def main():
    panel = pd.read_csv(PROC / "panel_core_augmented.csv")
    panel = panel.sort_values(["state_abbr", "year"]).reset_index(drop=True)

    rows = []
    for st, grp in panel.groupby("state_abbr"):
        if st == "DC":
            continue
        state_name = grp["state"].iloc[0]
        # values across the full panel range to capture pre-1999 starting state
        full_years = list(zip(grp["year"].tolist(), grp["assault"].tolist()))
        # Restrict the search for "first adoption" to the analysis window
        win = [(y, v) for y, v in full_years
               if (y is not None and not pd.isna(y))]
        # First-time 0->1 anywhere in the panel.
        first = first_transition(full_years, direction="0to1")
        # Whether they start the analysis window already banned.
        start_val = None
        for y, v in full_years:
            if y == ANALYSIS_LO:
                start_val = v
                break
        starts_banned = int(start_val == 1) if start_val is not None else 0
        # End-of-window value (uses ANALYSIS_HI).
        end_val = None
        for y, v in full_years:
            if y == ANALYSIS_HI:
                end_val = v
                break
        ends_banned = int(end_val == 1) if end_val is not None else 0
        reversals = all_reversals(full_years)
        # Adoption year for THIS analysis: only flips in [ANALYSIS_LO+1, ANALYSIS_HI].
        # (We exclude pre-1999 adopters by leaving adoption_year blank for them.)
        adoption_year = None
        if first is not None and ANALYSIS_LO + 1 <= first <= ANALYSIS_HI:
            adoption_year = first
        # Included in mortality sample: must have full [g-MIN_PRE_K, g+H] in window
        # and be inside ANALYSIS_LO..ANALYSIS_HI. We allow up to 2023 cohorts to be
        # included even with H=0 post-period (they will be aggregated into ATTs that
        # only contribute to event_time >= 0 cells where t>=g and t<=ANALYSIS_HI).
        included = bool(adoption_year is not None
                        and adoption_year - MIN_PRE_K >= ANALYSIS_LO)
        # Absorbing if no reversal post-adoption
        absorbing = (adoption_year is not None
                     and not any(r > adoption_year for r in reversals))
        post_reversal_yrs = ",".join(str(r) for r in reversals
                                     if (adoption_year is None or r > adoption_year))
        rows.append(OrderedDict([
            ("state", state_name),
            ("state_abbr", st),
            ("treatment_variable", "assault"),
            ("adoption_rule", "first 0-to-1 switch in assault (Tufts)"),
            ("adoption_year", adoption_year if adoption_year is not None else ""),
            ("included_in_mortality_sample", included),
            ("absorbing_after_adoption_through_2024", absorbing),
            ("post_adoption_reversal_years", post_reversal_yrs),
            ("starts_banned_1999", starts_banned),
            ("ends_banned_2023", ends_banned),
            ("first_observed_adoption_year_any_panel", first if first else ""),
            ("notes_rand_crosscheck", ""),
        ]))

    # Annotate with RAND/Siegel cross-check notes (manual).
    NOTES = {
        # Already-banned at 1999 start (excluded from analysis window):
        "CA": "CA enacted Roberti-Roos AWB 1989; tightened 1999 (post-Stockton). "
              "Tufts marks assault==1 from 1990 onward; matches RAND.",
        "CT": "CT 1993 AWB (post-Stockton wave); tightened post-Newtown 2013 "
              "(added more guns to list). Tufts assault==1 from 1993 onward; "
              "tightening is not a 0-to-1 transition so excluded from cohorts.",
        "MA": "MA 1998 AWB (predates federal sunset). Tufts assault==1 from "
              "1999 onward. Already-banned at 1999, excluded from cohorts.",
        "NJ": "NJ 1990 AWB (early post-Stockton). Tufts assault==1 from 1990 "
              "onward; matches RAND.",
        # In-window adopters:
        "NY": "NY enacted SAFE Act precursor in 2000; further tightened post-Newtown "
              "2013 (NY SAFE Act). Tufts assault flips 0->1 in 2000; excluded from "
              "cohorts because 2000 - 5 = 1995 < ANALYSIS_LO.",
        "MD": "MD Firearm Safety Act 2013 (post-Newtown). Tufts: 0->1 in 2013. "
              "Matches RAND State Firearm Laws Database.",
        "DE": "DE Lethal Weapons Act 2022. Tufts: 0->1 in 2022. Matches RAND.",
        "IL": "IL Protect Illinois Communities Act, January 2023 (post-Highland Park). "
              "Tufts: 0->1 in 2023. Matches RAND.",
        "WA": "WA HB 1240, April 2023. Tufts: 0->1 in 2023. Matches RAND.",
        # Variant: HI has assault PISTOL ban only (no long guns), so Tufts codes 0.
        "HI": "HI bans assault PISTOLS only (no long guns), so Tufts coding rule "
              "(must cover long guns) yields assault==0 throughout. RAND notes "
              "HI's assault-pistol law but excludes from a state-AWB list for the "
              "same reason. No discrepancy.",
    }
    for r in rows:
        st = r["state_abbr"]
        if st in NOTES:
            r["notes_rand_crosscheck"] = NOTES[st]

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "treatment_adoption_table.csv", index=False)

    # Console summary
    treated = df[df["adoption_year"] != ""].copy()
    included_n = int(df["included_in_mortality_sample"].sum())
    print(f"Wrote {OUT / 'treatment_adoption_table.csv'}")
    print(f"  observed 0->1 adoptions in 1999-2023: {len(treated)}")
    for _, r in treated.iterrows():
        flag = "INCLUDED" if r["included_in_mortality_sample"] else "EXCLUDED (pre-window)"
        print(f"    {r['state_abbr']} {r['adoption_year']}  {flag}")
    print(f"  cohorts contributing to CS21 sample (>= MIN_PRE_K pre years): {included_n}")
    cohort_yrs = sorted(set(r["adoption_year"] for r in rows
                            if r["included_in_mortality_sample"]))
    print(f"  distinct cohort years: {len(cohort_yrs)} ({cohort_yrs})")


if __name__ == "__main__":
    main()
