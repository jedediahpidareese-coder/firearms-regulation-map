"""Emit docs/data/county_caveats.json: per-county explanatory notes that
appear in the dashboard's state-pane caveats box. The user explicitly
preferred transparency over suppression -- per-100k rates for tiny
counties and reservation-county UCR data both stay visible, but each
gets a contextual note explaining the caveat.

Three categories:

  1. small_population (programmatic): any county whose minimum
     population in 2009-2024 is below 5000. Single rare events dominate
     per-100k rates at this scale.

  2. reservation_dominant (hand-curated): counties whose territory is
     >= ~50% Native American reservation land (per Census American
     Indian Areas geography). Tribal/BIA PD reporting completeness
     varies year to year, so crime rates have high volatility that
     does NOT reflect actual victimization changes.

  3. transient_workforce (hand-curated): counties whose resident
     population dramatically understates the daily population that
     actually generates the crime / receives the policing -- Permian
     Basin oil-patch counties, Manhattan, the National Mall area DC,
     Las Vegas Strip, Disneyland-area Orange CA.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
DOCS_DATA = ROOT / "docs" / "data"

# ---- Hand-curated lists ----

# Counties with >= ~50% reservation/tribal land. Source: Census
# American Indian Areas geography + manual cross-check against the
# top-10 violent-crime-rate outliers list. Hand-curated -- not
# exhaustive, but covers the well-known cases that drive map outliers.
RESERVATION_DOMINANT = {
    # SD: Pine Ridge / Rosebud / Standing Rock / Cheyenne River / Crow Creek / Yankton areas
    "46041": "Cheyenne River Sioux Reservation (most of county)",
    "46121": "Rosebud Indian Reservation (entire county)",
    "46137": "Standing Rock Indian Reservation (eastern portion)",
    "46071": "Pine Ridge Indian Reservation (southern portion)",
    "46102": "Pine Ridge Indian Reservation (entire county; formerly Shannon County)",
    "46017": "Crow Creek Indian Reservation",
    "46031": "Cheyenne River Indian Reservation (northern portion)",
    "46135": "Yankton Sioux Reservation",
    # ND: Standing Rock / Spirit Lake / Turtle Mountain / Fort Berthold
    "38085": "Standing Rock Indian Reservation (entire county)",
    "38079": "Spirit Lake Indian Reservation",
    "38095": "Turtle Mountain Indian Reservation",
    "38105": "Fort Berthold Indian Reservation (eastern portion)",
    # AZ: Navajo Nation + others
    "04001": "Navajo Nation + Apache reservations (most of county)",
    "04017": "Navajo Nation (most of county)",
    "04007": "San Carlos Apache Reservation (eastern portion)",
    # NM: Navajo / Apache / Pueblo
    "35031": "Navajo Nation (western portion) + Pueblo lands",
    "35045": "Navajo Nation (large portion)",
    "35006": "Navajo Nation (most of county)",
    # MT: Blackfeet / Crow / Northern Cheyenne / Fort Belknap / Fort Peck
    "30035": "Blackfeet Indian Reservation",
    "30009": "Crow Indian Reservation",
    "30087": "Northern Cheyenne Reservation",
    "30005": "Fort Belknap Reservation",
    "30085": "Fort Peck Reservation",
    "30019": "Fort Peck Reservation (eastern portion)",
    # WA: Yakama, Colville
    "53077": "Yakama Indian Reservation (large portion of county)",
    "53047": "Colville Indian Reservation (eastern portion)",
    # WI: Menominee
    "55078": "Menominee Indian Reservation (entire county)",
    # OK: Multiple historical reservations (large overlap with multiple counties post-McGirt)
    # AK: Many native village areas, but the borough-level structure is different;
    # skip for now since the Aleutians + remote AK boroughs are excluded from the
    # crime panel for unrelated reasons (Section 2.11 of data appendix).
}

# Counties where resident population denominator dramatically understates
# the daily population generating crime / receiving policing.
TRANSIENT_WORKFORCE = {
    "48301": "Permian Basin oil-patch county; resident pop ~50, daily working population in the thousands. Oil-field site theft + truck-stop incidents on US-285 inflate per-capita rates.",
    "48105": "Permian Basin oil-patch county (Crockett TX); transient oil-field workforce inflates per-capita property-crime rates.",
    "36061": "Manhattan (NY): resident pop ~1.66M but daily commuter+tourist pop ~3-4M. Per-100k rates vs. resident denominator overstate by ~2-3x.",
    "11001": "DC: resident pop ~700k but daily commuter+tourist pop substantially higher. Federal-jurisdiction incidents + National Mall events inflate per-resident rates.",
    "32003": "Clark County NV (Las Vegas Strip): tourist pop ~40M/year vs ~2.3M residents. Per-resident crime rates are misleading.",
    "06059": "Orange County CA (Disneyland area): tourist + theme-park workforce inflate the daily population denominator.",
    "04012": "La Paz County AZ: hosts Quartzsite (winter snowbird population ~50k vs ~17k residents); also Colorado River Indian Tribes jurisdictional overlap.",
}


def main() -> None:
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(
        PROC / "county_panel_2009_2024.csv",
        usecols=["county_fips", "year", "population", "county_name", "state_name"],
        dtype={"county_fips": str},
    )

    out: dict[str, dict] = {}

    # 1) Programmatic: small population. Treat the COUNTY as small if its
    # minimum yearly pop in the panel window is < 5000. (Rare-event rates
    # like murder are noise-dominated below this denominator.)
    by_county = panel.groupby("county_fips").agg(
        min_pop=("population", "min"),
        max_pop=("population", "max"),
        county_name=("county_name", "first"),
        state_name=("state_name", "first"),
    )
    for fips, row in by_county.iterrows():
        if pd.notna(row["min_pop"]) and row["min_pop"] < 5000:
            entry = out.setdefault(fips, {"caveats": []})
            entry["county_name"] = row["county_name"]
            entry["state_name"] = row["state_name"]
            entry["caveats"].append({
                "type": "small_population",
                "label": "Very small population",
                "note": (
                    f"Minimum annual population in this county was "
                    f"{int(row['min_pop'])} (max {int(row['max_pop'])}). "
                    "Per-100,000 rates are highly sensitive to single events at this scale -- "
                    "a single murder produces a rate of 20-100/100k just from arithmetic. "
                    "Read year-to-year changes with care."
                ),
            })

    # 2) Hand-curated: reservation-dominant
    for fips, descr in RESERVATION_DOMINANT.items():
        entry = out.setdefault(fips, {"caveats": []})
        meta = by_county.loc[fips] if fips in by_county.index else None
        if meta is not None:
            entry["county_name"] = meta["county_name"]
            entry["state_name"] = meta["state_name"]
        entry["caveats"].append({
            "type": "reservation",
            "label": "Reservation / tribal-land county",
            "note": (
                f"County contains substantial tribal land ({descr}). Tribal police, "
                "BIA, and federal Indian Country prosecutors all report incidents to "
                "FBI UCR; reporting completeness varies year-to-year, producing "
                "spurious volatility in crime rates that does NOT reflect real "
                "victimization changes. National Crime Victimization Survey "
                "supplements (BJS) document genuinely elevated victimization rates "
                "in tribal communities, so SOME of the elevated rates are real signal."
            ),
        })

    # 3) Hand-curated: transient-workforce / tourist denominator
    for fips, note in TRANSIENT_WORKFORCE.items():
        entry = out.setdefault(fips, {"caveats": []})
        meta = by_county.loc[fips] if fips in by_county.index else None
        if meta is not None:
            entry["county_name"] = meta["county_name"]
            entry["state_name"] = meta["state_name"]
        entry["caveats"].append({
            "type": "transient_workforce",
            "label": "Resident vs. daily population denominator",
            "note": note,
        })

    out_path = DOCS_DATA / "county_caveats.json"
    out_path.write_text(json.dumps(out, indent=1))
    print(f"Wrote {out_path}: {len(out)} counties with caveats")
    counts = {}
    for c in out.values():
        for cav in c["caveats"]:
            counts[cav["type"]] = counts.get(cav["type"], 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v} counties")


if __name__ == "__main__":
    main()
