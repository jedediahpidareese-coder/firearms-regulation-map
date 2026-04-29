from __future__ import annotations

import io
import json
import math
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "outputs"


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

KLEIN_PDF_PATH = DATA_DIR / "klein_school_shootings_1979_2011.pdf"
PAH_WIKP_PATH = DATA_DIR / "pah_wikp_combo.csv"
EDUCATION_TABLE_PDF_PATH = DATA_DIR / "11s0229.pdf"
ALCOHOL_PATH = DATA_DIR / "pcyr1970_2023.txt"
FIREARM_SUICIDE_PATH = DATA_DIR / "firearm_suicide_homicide_dataset_v2.tab"
GIUS_PDF_PATH = DATA_DIR / "gius_2018_school_shootings.pdf"

NBER_1970_1999_PATH = DATA_DIR / "pop7099s.csv"
NBER_2000S_PATH = DATA_DIR / "ST-EST00INT-AGESEX.csv"
NBER_2014_PATH = DATA_DIR / "pepsyasex2014.csv"

GIUS_PANEL_PATH = PROCESSED_DIR / "gius_2018_school_panel_1990_2014.csv"
GIUS_RAW_STATE_YEAR_PATH = PROCESSED_DIR / "gius_2018_school_outcomes_raw_state_year_1990_2014.csv"
GIUS_INCIDENTS_PATH = PROCESSED_DIR / "gius_2018_school_incidents_preliminary_1990_2014.csv"
GIUS_ANNUAL_TARGETS_PATH = PROCESSED_DIR / "gius_2018_annual_targets_1990_2014.csv"
GIUS_BALANCE_CHECKS_PATH = PROCESSED_DIR / "gius_2018_balance_checks.csv"
GIUS_VARIABLES_PATH = PROCESSED_DIR / "gius_2018_variable_dictionary.csv"
GIUS_SOURCES_PATH = PROCESSED_DIR / "gius_2018_source_notes.csv"
GIUS_SUMMARY_PATH = PROCESSED_DIR / "gius_2018_panel_summary.json"


PAPER_KILLED_TARGETS = {
    1990: 1,
    1991: 8,
    1992: 6,
    1993: 10,
    1994: 11,
    1995: 9,
    1996: 13,
    1997: 11,
    1998: 13,
    1999: 18,
    2000: 10,
    2001: 8,
    2002: 7,
    2003: 6,
    2004: 2,
    2005: 12,
    2006: 29,
    2007: 47,
    2008: 16,
    2009: 12,
    2010: 16,
    2011: 10,
    2012: 43,
    2013: 19,
    2014: 17,
}

PAPER_WOUNDED_TARGETS = {
    1990: 0,
    1991: 2,
    1992: 22,
    1993: 10,
    1994: 3,
    1995: 6,
    1996: 5,
    1997: 14,
    1998: 36,
    1999: 34,
    2000: 0,
    2001: 19,
    2002: 5,
    2003: 5,
    2004: 0,
    2005: 2,
    2006: 15,
    2007: 45,
    2008: 22,
    2009: 13,
    2010: 11,
    2011: 24,
    2012: 19,
    2013: 35,
    2014: 35,
}


STATE_FIPS_TO_ABBR = {
    1: "AL",
    2: "AK",
    4: "AZ",
    5: "AR",
    6: "CA",
    8: "CO",
    9: "CT",
    10: "DE",
    12: "FL",
    13: "GA",
    15: "HI",
    16: "ID",
    17: "IL",
    18: "IN",
    19: "IA",
    20: "KS",
    21: "KY",
    22: "LA",
    23: "ME",
    24: "MD",
    25: "MA",
    26: "MI",
    27: "MN",
    28: "MS",
    29: "MO",
    30: "MT",
    31: "NE",
    32: "NV",
    33: "NH",
    34: "NJ",
    35: "NM",
    36: "NY",
    37: "NC",
    38: "ND",
    39: "OH",
    40: "OK",
    41: "OR",
    42: "PA",
    44: "RI",
    45: "SC",
    46: "SD",
    47: "TN",
    48: "TX",
    49: "UT",
    50: "VT",
    51: "VA",
    53: "WA",
    54: "WV",
    55: "WI",
    56: "WY",
}


def ensure_download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        destination.write_bytes(response.read())
    return destination


def load_state_lookup() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED_DIR / "panel_core_1979_2024.csv", usecols=["state", "state_abbr"])
    lookup = panel.drop_duplicates().sort_values("state_abbr").reset_index(drop=True)
    if lookup.shape[0] != 50:
        raise ValueError(f"Expected 50 states in panel_core_1979_2024.csv, found {lookup.shape[0]}")
    return lookup


def build_state_name_maps(state_lookup: pd.DataFrame) -> tuple[dict[str, str], dict[str, str]]:
    abbr_to_name = dict(zip(state_lookup["state_abbr"], state_lookup["state"]))
    name_to_abbr = {state: abbr for abbr, state in abbr_to_name.items()}
    name_to_abbr.update(
        {
            "District of Columbia": "DC",
            "D.C.": "DC",
            "DC": "DC",
            "Tennsessee": "TN",
            "Ilinois": "IL",
        }
    )
    return abbr_to_name, name_to_abbr


def normalize_state_abbr(value: str | None, name_to_abbr: dict[str, str]) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    if raw.upper() in name_to_abbr.values():
        return raw.upper()
    clean = raw.replace("New Y ork", "New York").replace("T ennessee", "Tennessee").replace("T exas", "Texas")
    clean = re.sub(r"\s+", " ", clean).strip()
    return name_to_abbr.get(clean)


def largest_remainder_allocation(weights: list[float], target: int) -> list[int]:
    if target < 0:
        raise ValueError("target must be nonnegative")
    if target == 0:
        return [0 for _ in weights]
    weight_sum = sum(weights)
    if weight_sum <= 0:
        raise ValueError("weights must sum to a positive value when target > 0")
    raw = [(weight / weight_sum) * target for weight in weights]
    base = [math.floor(value) for value in raw]
    remainder = target - sum(base)
    order = sorted(range(len(raw)), key=lambda idx: (raw[idx] - base[idx], weights[idx], -idx), reverse=True)
    for idx in order[:remainder]:
        base[idx] += 1
    return base


def flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(column) for column in frame.columns]
        return frame
    flattened = []
    for column in frame.columns:
        parts = [str(part) for part in column if str(part) != "nan"]
        flattened.append(" ".join(parts).strip())
    frame.columns = flattened
    return frame


def build_base_panel(state_lookup: pd.DataFrame) -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED_DIR / "panel_core_1979_2024.csv")
    panel = panel.merge(state_lookup, on=["state", "state_abbr"], how="inner")
    panel = panel.loc[panel["year"].between(1990, 2014)].copy()
    panel = panel.sort_values(["state_abbr", "year"]).reset_index(drop=True)
    return panel


def parse_klein_incidents(state_lookup: pd.DataFrame) -> pd.DataFrame:
    _, name_to_abbr = build_state_name_maps(state_lookup)
    text = "\n".join((page.extract_text() or "") for page in PdfReader(KLEIN_PDF_PATH).pages)
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("Ilinois", "Illinois").replace("Tennsessee", "Tennessee")
    text = re.sub(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),(\d{4})",
        r"\1 \2, \3",
        text,
    )
    text = re.sub(
        r"\b\d+\s+Date/Place/ School Name/Age Killed / Wounded Motives/Contributory Factors Warnings / Notes\s*",
        " ",
        text,
    )
    text = re.sub(
        r"\b\d+\s+THE BULLY SOCIETY: U\.S\. School Shootings data, 1979-2011\*.*?Warnings / Notes\s*",
        " ",
        text,
        flags=re.S,
    )

    state_tokens = list(state_lookup["state"]) + ["District of Columbia", "DC", "D.C.", "AL", "Tennsessee", "Ilinois"]
    state_pattern = "|".join(sorted((re.escape(token) for token in state_tokens), key=len, reverse=True))

    entry_pattern = re.compile(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}.*?#\d+\s)",
        re.S,
    )
    header_pattern = re.compile(
        rf"^(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{{1,2}},\s*\d{{4}})\s+"
        rf"(?P<city>.+?),\s+(?P<state>{state_pattern}|[A-Z]{{2}}),?\s*(?P<school>.*?)\s+#(?P<incident_id>\d+)\s*$",
        re.S,
    )
    stop_pattern = re.compile(
        r"(?:\b(?:[A-Z][A-Za-z/?()'\-.]*(?: [A-Za-z][A-Za-z/?()'\-.]*){0,8}:|SUICIDE\b|ACCIDENT\b|Accident\b|Accidental\b|Date/Place/))"
    )

    def first_stop(text_value: str, start: int) -> int:
        match = stop_pattern.search(text_value, start)
        return match.start() if match else len(text_value)

    def parse_count(text_value: str | None) -> tuple[int, str | None]:
        if text_value is None:
            return 0, None
        cleaned = re.sub(r"\s+", " ", text_value).strip()
        cleaned = re.sub(r"\b\d{1,2}-year[- ]old\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b\d{1,2} years? old\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bages? \d{1,2}(?: and \d{1,2})*\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r",\s*\d{1,2}(?:\s+and\s+\d{1,2})+\b", "", cleaned, flags=re.I)
        numbers = [int(value) for value in re.findall(r"\b(\d+)\b", cleaned)]
        total = sum(numbers)
        if total == 0 and re.search(r"[A-Za-z]", cleaned) and not re.fullmatch(r"0+|none|unknown", cleaned, flags=re.I):
            total = 1
        return total, cleaned or None

    records: list[dict[str, object]] = []
    matches = list(entry_pattern.finditer(text))
    for index, match in enumerate(matches):
        start = match.start()
        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = text.find("FINAL SUMMARY")
        segment = re.sub(r"\s+", " ", text[start:end]).strip()
        incident_token = re.search(r"#(\d+)\s", segment)
        if incident_token is None:
            continue
        header = segment[: incident_token.end()].strip()
        body = segment[incident_token.end() :].strip()
        parsed_header = header_pattern.match(header)
        if parsed_header is None:
            raise ValueError(f"Failed to parse Klein header: {header}")

        killed_index = body.find("Killed:")
        wounded_index = body.find("Wounded:")

        killed_text = None
        wounded_text = None
        if killed_index >= 0:
            killed_start = killed_index + len("Killed:")
            killed_end = min(
                value
                for value in [wounded_index if wounded_index > killed_start else None, first_stop(body, killed_start), len(body)]
                if value is not None
            )
            killed_text = body[killed_start:killed_end].strip()
        if wounded_index >= 0:
            wounded_start = wounded_index + len("Wounded:")
            wounded_end = first_stop(body, wounded_start)
            wounded_text = body[wounded_start:wounded_end].strip()

        killed_count, killed_text_clean = parse_count(killed_text)
        wounded_count, wounded_text_clean = parse_count(wounded_text)

        incident_date = re.sub(r",\s*", ", ", parsed_header.group("date"))
        state_abbr = normalize_state_abbr(parsed_header.group("state"), name_to_abbr)
        if state_abbr is None:
            raise ValueError(f"Failed to normalize Klein state: {parsed_header.group('state')}")
        if state_abbr == "DC":
            continue

        incident_year = pd.to_datetime(incident_date).year
        if not 1990 <= incident_year <= 2011:
            continue

        records.append(
            {
                "incident_id": int(parsed_header.group("incident_id")),
                "date": pd.to_datetime(incident_date),
                "year": incident_year,
                "state_abbr": state_abbr,
                "state": state_lookup.loc[state_lookup["state_abbr"] == state_abbr, "state"].iloc[0],
                "city": parsed_header.group("city").strip(),
                "school": parsed_header.group("school").strip(),
                "killed_raw": killed_count,
                "wounded_raw": wounded_count,
                "killed_text": killed_text_clean,
                "wounded_text": wounded_text_clean,
                "source_family": "Klein (2012)",
            }
        )

    incidents = pd.DataFrame.from_records(records)
    if incidents.empty:
        raise ValueError("Failed to parse any Klein incidents.")
    return incidents


def build_pah_wikp_incidents(state_lookup: pd.DataFrame) -> pd.DataFrame:
    _, name_to_abbr = build_state_name_maps(state_lookup)
    frame = pd.read_csv(PAH_WIKP_PATH)
    frame["date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.loc[frame["date"].dt.year.between(2012, 2014)].copy()
    frame["killed_raw"] = pd.to_numeric(frame["Fatalities"], errors="coerce").fillna(0).astype(int)
    frame["wounded_raw"] = pd.to_numeric(frame["Wounded"], errors="coerce").fillna(0).astype(int)
    for column in ["City", "State", "School", "Source", "Desc"]:
        frame[column] = frame[column].fillna("")
    frame = frame.loc[(frame["killed_raw"] + frame["wounded_raw"]) > 0].copy()
    frame["state_abbr"] = frame["State"].map(lambda value: normalize_state_abbr(value, name_to_abbr))
    frame = frame.loc[frame["state_abbr"].isin(state_lookup["state_abbr"])].copy()
    frame["state"] = frame["state_abbr"].map(dict(zip(state_lookup["state_abbr"], state_lookup["state"])))
    for column in ["City", "State", "School"]:
        frame[f"{column.lower()}_norm"] = (
            frame[column].str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
        )
    frame["event_key"] = (
        frame["date"].dt.strftime("%Y-%m-%d")
        + "|"
        + frame["city_norm"]
        + "|"
        + frame["state_abbr"]
        + "|"
        + frame["school_norm"]
    )

    events = (
        frame.groupby("event_key", as_index=False)
        .agg(
            date=("date", "first"),
            year=("date", lambda series: int(series.iloc[0].year)),
            state_abbr=("state_abbr", "first"),
            state=("state", "first"),
            city=("City", "first"),
            school=("School", "first"),
            killed_raw=("killed_raw", "max"),
            wounded_raw=("wounded_raw", "max"),
            source_family=("Source", lambda series: " / ".join(sorted(set(value for value in series if value)))),
            description=("Desc", lambda series: " || ".join(value for value in series if value.strip())),
        )
        .sort_values(["date", "state_abbr", "city", "school"])
        .reset_index(drop=True)
    )
    events["incident_id"] = [f"PW-{index + 1:03d}" for index in range(events.shape[0])]
    return events[
        [
            "incident_id",
            "date",
            "year",
            "state_abbr",
            "state",
            "city",
            "school",
            "killed_raw",
            "wounded_raw",
            "description",
            "source_family",
        ]
    ]


def build_preliminary_incidents(state_lookup: pd.DataFrame) -> pd.DataFrame:
    klein = parse_klein_incidents(state_lookup)
    pah_wikp = build_pah_wikp_incidents(state_lookup)
    incidents = pd.concat([klein, pah_wikp], ignore_index=True, sort=False)
    incidents["victims_raw"] = incidents["killed_raw"] + incidents["wounded_raw"]
    incidents = incidents.sort_values(["date", "state_abbr", "city", "school"]).reset_index(drop=True)
    return incidents


def build_raw_outcome_state_year(incidents: pd.DataFrame, base_panel: pd.DataFrame) -> pd.DataFrame:
    raw = (
        incidents.groupby(["state", "state_abbr", "year"], as_index=False)[["killed_raw", "wounded_raw", "victims_raw"]]
        .sum()
        .merge(
            incidents.groupby(["state_abbr", "year"], as_index=False)["incident_id"]
            .nunique()
            .rename(columns={"incident_id": "incident_count_raw"}),
            on=["state_abbr", "year"],
            how="left",
        )
    )
    balanced = base_panel[["state", "state_abbr", "year"]].drop_duplicates().merge(
        raw,
        on=["state", "state_abbr", "year"],
        how="left",
    )
    fill_columns = ["killed_raw", "wounded_raw", "victims_raw", "incident_count_raw"]
    balanced[fill_columns] = balanced[fill_columns].fillna(0).astype(int)
    return balanced.sort_values(["state_abbr", "year"]).reset_index(drop=True)


def calibrate_outcomes(raw_state_year: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    calibrated = raw_state_year.copy()
    calibrated["killed_gius_2018"] = 0
    calibrated["wounded_gius_2018"] = 0

    annual_rows: list[dict[str, int]] = []
    for year in range(1990, 2015):
        year_mask = calibrated["year"] == year
        year_slice = calibrated.loc[year_mask].copy()

        killed_target = PAPER_KILLED_TARGETS[year]
        wounded_target = PAPER_WOUNDED_TARGETS[year]

        killed_weights = year_slice["killed_raw"].tolist()
        if sum(killed_weights) == 0 and killed_target > 0:
            killed_weights = year_slice["incident_count_raw"].tolist()
        if sum(killed_weights) == 0 and killed_target > 0:
            raise ValueError(f"No killed weights available for year {year}")

        wounded_weights = year_slice["wounded_raw"].tolist()
        if sum(wounded_weights) == 0 and wounded_target > 0:
            wounded_weights = year_slice["incident_count_raw"].tolist()
        if sum(wounded_weights) == 0 and wounded_target > 0:
            raise ValueError(f"No wounded weights available for year {year}")

        killed_alloc = largest_remainder_allocation(killed_weights, killed_target)
        wounded_alloc = largest_remainder_allocation(wounded_weights, wounded_target)

        calibrated.loc[year_mask, "killed_gius_2018"] = killed_alloc
        calibrated.loc[year_mask, "wounded_gius_2018"] = wounded_alloc

        annual_rows.append(
            {
                "year": year,
                "paper_killed_target": killed_target,
                "paper_wounded_target": wounded_target,
                "paper_victims_target": killed_target + wounded_target,
                "raw_killed_total": int(year_slice["killed_raw"].sum()),
                "raw_wounded_total": int(year_slice["wounded_raw"].sum()),
                "raw_victims_total": int(year_slice["victims_raw"].sum()),
                "calibrated_killed_total": int(sum(killed_alloc)),
                "calibrated_wounded_total": int(sum(wounded_alloc)),
                "calibrated_victims_total": int(sum(killed_alloc) + sum(wounded_alloc)),
            }
        )

    calibrated["school_shooting_victims_gius_2018"] = calibrated["killed_gius_2018"] + calibrated["wounded_gius_2018"]
    annual = pd.DataFrame(annual_rows)
    return calibrated, annual


def build_education_series(state_lookup: pd.DataFrame) -> pd.DataFrame:
    ensure_download(
        "https://www2.census.gov/library/publications/2010/compendia/statab/130ed/tables/11s0229.pdf",
        EDUCATION_TABLE_PDF_PATH,
    )
    page_text = PdfReader(EDUCATION_TABLE_PDF_PATH).pages[0].extract_text() or ""
    lines = [re.sub(r"\s+", " ", line).strip() for line in page_text.splitlines()]
    lines = [line for line in lines if line]
    rows = []
    number_pattern = r"(\d+\.\d)"
    for line in lines:
        normalized = (
            line.replace("New Y ork", "New York")
            .replace("T ennessee", "Tennessee")
            .replace("T exas", "Texas")
            .replace("District of Columbia", "District of Columbia")
        )
        numbers = [float(value) for value in re.findall(number_pattern, normalized)]
        if len(numbers) != 9:
            continue
        first_number = re.search(number_pattern, normalized)
        if first_number is None:
            continue
        state_name = normalized[: first_number.start()]
        state_name = re.sub(r"\s*\.\s*", " ", state_name)
        state_name = re.sub(r"\.+", " ", state_name)
        state_name = re.sub(r"\s+", " ", state_name).strip()
        if state_name not in set(state_lookup["state"]):
            continue
        rows.append(
            {
                "state": state_name,
                "share_bachelors_1990": numbers[1],
                "share_bachelors_2000": numbers[4],
                "share_bachelors_2008_anchor": numbers[7],
            }
        )
    education = pd.DataFrame(rows)
    if education.shape[0] != 50:
        raise ValueError(f"Education anchor extraction failed; expected 50 states, found {education.shape[0]}")

    acs = pd.read_csv(PROCESSED_DIR / "demographic_controls_1999_2024.csv", usecols=["state", "year", "share_bachelors_plus"])
    acs = acs.loc[acs["year"].between(2008, 2014)].copy()

    interpolated_rows: list[dict[str, object]] = []
    for row in education.itertuples(index=False):
        for year in range(1990, 2008):
            if year == 1990:
                value = row.share_bachelors_1990
            elif year == 2000:
                value = row.share_bachelors_2000
            elif year < 2000:
                fraction = (year - 1990) / (2000 - 1990)
                value = row.share_bachelors_1990 + fraction * (row.share_bachelors_2000 - row.share_bachelors_1990)
            else:
                fraction = (year - 2000) / (2008 - 2000)
                value = row.share_bachelors_2000 + fraction * (row.share_bachelors_2008_anchor - row.share_bachelors_2000)
            interpolated_rows.append({"state": row.state, "year": year, "share_bachelors_plus": float(value)})

    interpolated = pd.DataFrame(interpolated_rows)
    combined = pd.concat([interpolated, acs], ignore_index=True, sort=False)
    combined = combined.merge(state_lookup, on="state", how="left")
    combined = combined.sort_values(["state_abbr", "year"]).reset_index(drop=True)
    return combined[["state", "state_abbr", "year", "share_bachelors_plus"]]


def build_age_5_18_series(state_lookup: pd.DataFrame, base_panel: pd.DataFrame) -> pd.DataFrame:
    ensure_download("https://data.nber.org/data/census-intercensal-population/pop7099s.csv", NBER_1970_1999_PATH)
    ensure_download(
        "https://data.nber.org/data/census-intercensal-population/2000s/ST-EST00INT-AGESEX.csv",
        NBER_2000S_PATH,
    )
    ensure_download(
        "https://data.nber.org/data/census-intercensal-population/2014/pepsyasex2014.csv",
        NBER_2014_PATH,
    )

    state_abbrs = set(state_lookup["state_abbr"])
    state_names = set(state_lookup["state"])

    pop_7099 = pd.read_csv(NBER_1970_1999_PATH, usecols=["year", "state2", "agegr", "age", "pop"], low_memory=False)
    pop_7099["age_numeric"] = pd.to_numeric(pop_7099["age"], errors="coerce")
    pop_7099["agegr_numeric"] = pd.to_numeric(pop_7099["agegr"], errors="coerce")
    pop_7099["age_for_filter"] = pop_7099["age_numeric"].fillna(pop_7099["agegr_numeric"])
    pop_7099 = pop_7099.loc[
        pop_7099["year"].between(1990, 1999)
        & pop_7099["state2"].isin(state_abbrs)
        & pop_7099["age_for_filter"].between(5, 18)
    ].copy()
    age_7099 = (
        pop_7099.groupby(["state2", "year"], as_index=False)["pop"]
        .sum()
        .rename(columns={"state2": "state_abbr", "pop": "age_5_18_population"})
    )

    pop_2000s = pd.read_csv(NBER_2000S_PATH)
    pop_2000s = pop_2000s.loc[pop_2000s["SEX"] == 0].copy()
    pop_2000s["state_abbr"] = pop_2000s["STATE"].map(STATE_FIPS_TO_ABBR)
    pop_2000s = pop_2000s.loc[pop_2000s["state_abbr"].isin(state_abbrs) & pop_2000s["AGE"].between(5, 18)].copy()
    estimate_columns = [f"POPESTIMATE{year}" for year in range(2000, 2011)]
    age_2000s = pop_2000s.melt(
        id_vars=["state_abbr", "NAME", "AGE"],
        value_vars=estimate_columns,
        var_name="year",
        value_name="age_5_18_population",
    )
    age_2000s["year"] = age_2000s["year"].str.replace("POPESTIMATE", "", regex=False).astype(int)
    age_2000s = (
        age_2000s.groupby(["state_abbr", "year"], as_index=False)["age_5_18_population"]
        .sum()
        .sort_values(["state_abbr", "year"])
    )

    pop_2014 = pd.read_csv(NBER_2014_PATH)
    pop_2014 = pop_2014.loc[pop_2014["geodisplaylabel"].isin(state_names)].copy()
    for year in range(2011, 2015):
        columns = [f"est7{year}sex0_age{age}" for age in range(5, 19)]
        pop_2014[f"age_5_18_{year}"] = pop_2014[columns].sum(axis=1)
    age_2014 = pop_2014.melt(
        id_vars=["geodisplaylabel"],
        value_vars=[f"age_5_18_{year}" for year in range(2011, 2015)],
        var_name="year",
        value_name="age_5_18_population",
    )
    age_2014["year"] = age_2014["year"].str.replace("age_5_18_", "", regex=False).astype(int)
    age_2014 = age_2014.rename(columns={"geodisplaylabel": "state"}).merge(state_lookup, on="state", how="left")
    age_2014 = age_2014[["state_abbr", "year", "age_5_18_population"]]

    age = pd.concat([age_7099, age_2000s, age_2014], ignore_index=True, sort=False)
    age = age.groupby(["state_abbr", "year"], as_index=False)["age_5_18_population"].sum()

    denominator = base_panel[["state", "state_abbr", "year", "population"]].drop_duplicates()
    merged = denominator.merge(age, on=["state_abbr", "year"], how="left")
    merged["share_age_5_18"] = merged["age_5_18_population"] / merged["population"]
    return merged[["state", "state_abbr", "year", "age_5_18_population", "share_age_5_18"]]


def build_alcohol_series(state_lookup: pd.DataFrame) -> pd.DataFrame:
    lines = ALCOHOL_PATH.read_text(encoding="latin1").splitlines()
    data_lines = [line for line in lines if re.match(r"^\d{4}\s+\d{1,2}\s+\d", line)]
    alcohol = pd.read_fwf(
        io.StringIO("\n".join(data_lines)),
        colspecs=[(0, 4), (5, 7), (8, 9), (10, 20), (21, 30), (31, 40), (42, 47), (48, 50), (51, 60), (62, 67)],
        names=[
            "year",
            "state_fips",
            "beverage_type",
            "gallons_beverage",
            "gallons_ethanol",
            "population_age_14_plus",
            "per_capita_age_14_plus_raw",
            "decile_age_14_plus",
            "population_age_21_plus",
            "per_capita_age_21_plus_raw",
        ],
    )
    alcohol["state_abbr"] = alcohol["state_fips"].map(STATE_FIPS_TO_ABBR)
    alcohol = alcohol.loc[
        alcohol["beverage_type"] == 4
    ].copy()
    alcohol = alcohol.loc[alcohol["state_abbr"].isin(state_lookup["state_abbr"]) & alcohol["year"].between(1990, 2014)].copy()
    alcohol["per_capita_alcohol_ethanol_14plus"] = alcohol["per_capita_age_14_plus_raw"] / 10000.0
    alcohol = alcohol.merge(state_lookup, on="state_abbr", how="left")
    return alcohol[["state", "state_abbr", "year", "per_capita_alcohol_ethanol_14plus"]]


def build_firearm_suicide_series(state_lookup: pd.DataFrame) -> pd.DataFrame:
    suicides = pd.read_csv(FIREARM_SUICIDE_PATH, sep="\t")
    suicides = suicides.loc[suicides["year"].between(1990, 2014)].copy()
    suicides["state_abbr"] = suicides["state"].map({state: abbr for state, abbr in zip(state_lookup["state"], state_lookup["state_abbr"])})
    suicides = suicides.loc[suicides["state_abbr"].isin(state_lookup["state_abbr"])].copy()
    suicides["firearm_suicide_ratio"] = suicides["firearm_suicides"] / suicides["total_suicides"]
    return suicides[
        [
            "state",
            "state_abbr",
            "year",
            "firearm_suicides",
            "total_suicides",
            "firearm_suicide_ratio",
            "fss",
        ]
    ].rename(columns={"fss": "firearm_suicide_share_proxy_fss"})


def build_land_area_series(state_lookup: pd.DataFrame) -> pd.DataFrame:
    request = urllib.request.Request(
        "https://www.census.gov/geographies/reference-files/2010/geo/state-area.html",
        headers={"User-Agent": USER_AGENT},
    )
    html = urllib.request.urlopen(request).read().decode("utf-8", errors="ignore")
    table = pd.read_html(io.StringIO(html))[0]
    table = flatten_columns(table)
    state_column = next(column for column in table.columns if column.startswith("State and other areas2"))
    land_area_column = next(column for column in table.columns if column.startswith("Land Area1") and "Sq. Mi." in column)
    area = table[[state_column, land_area_column]].rename(columns={state_column: "state", land_area_column: "land_area_sq_mi"})
    area["state"] = area["state"].astype(str).str.strip()
    area = area.loc[area["state"].isin(state_lookup["state"])].copy()
    area["land_area_sq_mi"] = pd.to_numeric(area["land_area_sq_mi"], errors="coerce")
    return area.merge(state_lookup, on="state", how="left")


def build_variable_dictionary() -> pd.DataFrame:
    rows = [
        {
            "variable_name": "school_shooting_victims_gius_2018",
            "group": "Outcome",
            "label": "School shooting victims",
            "description": "Calibrated number of persons killed plus wounded in school shootings in the state-year. Annual national totals match Gius (2018) Figures 1 and 2.",
        },
        {
            "variable_name": "killed_gius_2018",
            "group": "Outcome",
            "label": "School shooting fatalities",
            "description": "Calibrated state-year fatalities with annual national totals matched to Figure 1 in Gius (2018).",
        },
        {
            "variable_name": "wounded_gius_2018",
            "group": "Outcome",
            "label": "School shooting injuries",
            "description": "Calibrated state-year injuries with annual national totals matched to Figure 2 in Gius (2018).",
        },
        {
            "variable_name": "incident_count_raw",
            "group": "Outcome",
            "label": "Raw school shooting incidents",
            "description": "Pre-calibration count of distinct school shooting incidents in the state-year from the cited source family used for the reconstruction.",
        },
        {
            "variable_name": "gius_assault_ban",
            "group": "Law",
            "label": "Assault weapons ban dummy",
            "description": "Equals 1 if a state assault weapons ban was in force or if the federal assault weapons ban was in effect (1994-2004).",
        },
        {
            "variable_name": "gius_state_private_sale_bg",
            "group": "Law",
            "label": "Private-sale background check dummy",
            "description": "Equals 1 if the state required any background check for private firearm sales, using a broad Tufts-law crosswalk.",
        },
        {
            "variable_name": "gius_restrictive_ccw",
            "group": "Law",
            "label": "Restrictive concealed-carry dummy",
            "description": "Equals 1 for may-issue or prohibited concealed-carry regimes, proxied with Tufts `mayissue`.",
        },
        {
            "variable_name": "gius_federal_bg",
            "group": "Law",
            "label": "Federal dealer background check dummy",
            "description": "Equals 1 in 1994-2014 for the Brady Act dealer background-check regime.",
        },
        {
            "variable_name": "population_density",
            "group": "Control",
            "label": "Population density",
            "description": "Annual resident population divided by Census land area in square miles.",
        },
        {
            "variable_name": "share_bachelors_plus",
            "group": "Control",
            "label": "Share with bachelor's degree or more",
            "description": "ACS actual values for 2008-2014 combined with interpolated 1990/2000/2008 Census anchors for 1990-2007.",
        },
        {
            "variable_name": "pcpi_nominal",
            "group": "Control",
            "label": "Per capita income proxy",
            "description": "BEA per capita personal income in current dollars, used as the closest continuous state-year proxy for the paper's per-capita income control.",
        },
        {
            "variable_name": "unemployment_rate",
            "group": "Control",
            "label": "Unemployment rate",
            "description": "Annual average unemployment rate from the core panel.",
        },
        {
            "variable_name": "share_age_5_18",
            "group": "Control",
            "label": "Share age 5-18",
            "description": "Population ages 5 through 18 divided by total population, using NBER/Census age-sex files.",
        },
        {
            "variable_name": "per_capita_alcohol_ethanol_14plus",
            "group": "Control",
            "label": "Per-capita alcohol consumption",
            "description": "NIAAA apparent ethanol gallons per capita age 14 and older, beverage-type total.",
        },
        {
            "variable_name": "firearm_suicide_ratio",
            "group": "Control",
            "label": "Firearm suicide ratio",
            "description": "Firearm suicides divided by total suicides, used as a gun-ownership proxy.",
        },
    ]
    return pd.DataFrame(rows)


def build_source_notes() -> pd.DataFrame:
    rows = [
        {
            "component": "School shootings, 1990-2011",
            "status": "reconstructed",
            "source_name": "Klein (2012) PDF appendix",
            "location": str(KLEIN_PDF_PATH),
            "note": "Event-level counts parsed from the local Klein appendix PDF and aggregated to state-year.",
        },
        {
            "component": "School shootings, 2012-2014",
            "status": "reconstructed",
            "source_name": "Pah/Wikipedia combined file",
            "location": str(PAH_WIKP_PATH),
            "note": "Deduplicated event-level fatalities and injuries used to distribute 2012-2014 state-year outcomes before calibration.",
        },
        {
            "component": "Annual outcome targets",
            "status": "exact paper benchmark",
            "source_name": "Gius (2018) Figures 1 and 2",
            "location": str(GIUS_PDF_PATH),
            "note": "Annual killed and wounded totals were read from the paper figures rendered from the local PDF. The extracted yearly values sum exactly to the published 354 killed and 382 wounded totals.",
        },
        {
            "component": "State gun laws",
            "status": "proxy crosswalk",
            "source_name": "Existing Tufts-based state law panel",
            "location": str(PROCESSED_DIR / "panel_core_1979_2024.csv"),
            "note": "Restrictive CCW and private-sale background-check variables are reconstructed from the Tufts-law panel to match the paper's categories as closely as possible.",
        },
        {
            "component": "Educational attainment",
            "status": "mixed exact/interpolated",
            "source_name": "Census Statistical Abstract Table 229 + ACS",
            "location": str(EDUCATION_TABLE_PDF_PATH),
            "note": "1990, 2000, and 2008 anchors come from Census Table 229. 2008-2014 values use ACS actuals. 1991-1999 and 2001-2007 are linearly interpolated.",
        },
        {
            "component": "Age 5-18 share",
            "status": "exact reconstructed",
            "source_name": "NBER/Census intercensal age-sex files",
            "location": str(NBER_1970_1999_PATH),
            "note": "State-year age counts are summed directly from age-specific Census/NBER files and divided by annual total population from the core panel.",
        },
        {
            "component": "Alcohol consumption",
            "status": "exact reconstructed",
            "source_name": "NIAAA apparent per-capita alcohol file",
            "location": str(ALCOHOL_PATH),
            "note": "Uses beverage-type total ethanol per capita age 14 and older.",
        },
        {
            "component": "Firearm suicide ratio",
            "status": "proxy approximation",
            "source_name": "Harvard Dataverse firearm suicide-homicide panel",
            "location": str(FIREARM_SUICIDE_PATH),
            "note": "Matches the paper's proxy concept but not necessarily the exact original source file used by Gius.",
        },
        {
            "component": "Income control",
            "status": "proxy approximation",
            "source_name": "Existing BEA/FRED state income panel",
            "location": str(PROCESSED_DIR / "panel_core_1979_2024.csv"),
            "note": "Uses per capita personal income as the closest continuous historical state-year proxy for the paper's income control.",
        },
    ]
    return pd.DataFrame(rows)


def build_balance_checks(panel: pd.DataFrame, annual_targets: pd.DataFrame) -> pd.DataFrame:
    required_columns = [
        "school_shooting_victims_gius_2018",
        "killed_gius_2018",
        "wounded_gius_2018",
        "gius_assault_ban",
        "gius_state_private_sale_bg",
        "gius_restrictive_ccw",
        "gius_federal_bg",
        "population_density",
        "share_bachelors_plus",
        "pcpi_nominal",
        "unemployment_rate",
        "share_age_5_18",
        "per_capita_alcohol_ethanol_14plus",
        "firearm_suicide_ratio",
    ]
    rows_expected = 50 * 25
    duplicate_state_year_rows = int(panel.duplicated(["state_abbr", "year"]).sum())
    missing_required_cells = int(panel[required_columns].isna().sum().sum())
    annual_target_match = int(
        (
            annual_targets["paper_victims_target"].eq(annual_targets["calibrated_victims_total"])
            & annual_targets["paper_killed_target"].eq(annual_targets["calibrated_killed_total"])
            & annual_targets["paper_wounded_target"].eq(annual_targets["calibrated_wounded_total"])
        ).all()
    )
    checks = [
        {"check_name": "rows_expected", "value": rows_expected, "detail": "50 states x 25 years (1990-2014)"},
        {"check_name": "rows_actual", "value": int(panel.shape[0]), "detail": "Observed rows in final panel"},
        {"check_name": "distinct_states", "value": int(panel["state_abbr"].nunique()), "detail": "Expected 50"},
        {"check_name": "distinct_years", "value": int(panel["year"].nunique()), "detail": "Expected 25"},
        {"check_name": "duplicate_state_year_rows", "value": duplicate_state_year_rows, "detail": "Must equal 0"},
        {"check_name": "missing_required_cells", "value": missing_required_cells, "detail": "Must equal 0"},
        {"check_name": "annual_targets_matched", "value": annual_target_match, "detail": "1 means calibrated state-year sums match the paper's yearly figures exactly"},
    ]
    return pd.DataFrame(checks)


def assemble_final_panel(
    base_panel: pd.DataFrame,
    calibrated_outcomes: pd.DataFrame,
    education: pd.DataFrame,
    age_series: pd.DataFrame,
    alcohol: pd.DataFrame,
    firearm_suicides: pd.DataFrame,
    land_area: pd.DataFrame,
) -> pd.DataFrame:
    panel = base_panel[
        [
            "state",
            "state_abbr",
            "year",
            "assault",
            "mayissue",
            "universal",
            "universalh",
            "gunshow",
            "gunshowh",
            "universalpermit",
            "universalpermith",
            "population",
            "unemployment_rate",
            "pcpi_nominal",
        ]
    ].copy()
    panel = panel.merge(
        calibrated_outcomes[
            [
                "state",
                "state_abbr",
                "year",
                "incident_count_raw",
                "killed_raw",
                "wounded_raw",
                "victims_raw",
                "killed_gius_2018",
                "wounded_gius_2018",
                "school_shooting_victims_gius_2018",
            ]
        ],
        on=["state", "state_abbr", "year"],
        how="left",
    )
    panel = panel.merge(education, on=["state", "state_abbr", "year"], how="left")
    panel = panel.merge(age_series, on=["state", "state_abbr", "year"], how="left")
    panel = panel.merge(alcohol, on=["state", "state_abbr", "year"], how="left")
    panel = panel.merge(firearm_suicides, on=["state", "state_abbr", "year"], how="left")
    panel = panel.merge(land_area[["state", "state_abbr", "land_area_sq_mi"]], on=["state", "state_abbr"], how="left")

    panel["gius_assault_ban"] = ((panel["assault"] == 1) | panel["year"].between(1994, 2004)).astype(int)
    panel["gius_federal_bg"] = (panel["year"] >= 1994).astype(int)
    panel["gius_restrictive_ccw"] = panel["mayissue"].fillna(0).astype(int)
    panel["gius_state_private_sale_bg"] = (
        panel[["universal", "universalh", "gunshow", "gunshowh", "universalpermit", "universalpermith"]].fillna(0).max(axis=1)
    ).astype(int)
    panel["population_density"] = panel["population"] / panel["land_area_sq_mi"]

    panel["school_shooting_victims_gius_2018"] = panel["school_shooting_victims_gius_2018"].fillna(0).astype(int)
    panel["killed_gius_2018"] = panel["killed_gius_2018"].fillna(0).astype(int)
    panel["wounded_gius_2018"] = panel["wounded_gius_2018"].fillna(0).astype(int)
    panel["incident_count_raw"] = panel["incident_count_raw"].fillna(0).astype(int)
    panel["killed_raw"] = panel["killed_raw"].fillna(0).astype(int)
    panel["wounded_raw"] = panel["wounded_raw"].fillna(0).astype(int)
    panel["victims_raw"] = panel["victims_raw"].fillna(0).astype(int)

    ordered_columns = [
        "state",
        "state_abbr",
        "year",
        "school_shooting_victims_gius_2018",
        "killed_gius_2018",
        "wounded_gius_2018",
        "incident_count_raw",
        "victims_raw",
        "killed_raw",
        "wounded_raw",
        "gius_assault_ban",
        "gius_state_private_sale_bg",
        "gius_restrictive_ccw",
        "gius_federal_bg",
        "population",
        "land_area_sq_mi",
        "population_density",
        "share_bachelors_plus",
        "pcpi_nominal",
        "unemployment_rate",
        "age_5_18_population",
        "share_age_5_18",
        "per_capita_alcohol_ethanol_14plus",
        "firearm_suicides",
        "total_suicides",
        "firearm_suicide_ratio",
        "firearm_suicide_share_proxy_fss",
    ]
    panel = panel[ordered_columns].sort_values(["state_abbr", "year"]).reset_index(drop=True)
    return panel


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    state_lookup = load_state_lookup()
    base_panel = build_base_panel(state_lookup)

    incidents = build_preliminary_incidents(state_lookup)
    raw_state_year = build_raw_outcome_state_year(incidents, base_panel)
    calibrated_outcomes, annual_targets = calibrate_outcomes(raw_state_year)

    education = build_education_series(state_lookup)
    age_series = build_age_5_18_series(state_lookup, base_panel)
    alcohol = build_alcohol_series(state_lookup)
    firearm_suicides = build_firearm_suicide_series(state_lookup)
    land_area = build_land_area_series(state_lookup)

    final_panel = assemble_final_panel(
        base_panel=base_panel,
        calibrated_outcomes=calibrated_outcomes,
        education=education,
        age_series=age_series,
        alcohol=alcohol,
        firearm_suicides=firearm_suicides,
        land_area=land_area,
    )

    variable_dictionary = build_variable_dictionary()
    source_notes = build_source_notes()
    balance_checks = build_balance_checks(final_panel, annual_targets)

    final_panel.to_csv(GIUS_PANEL_PATH, index=False)
    raw_state_year.to_csv(GIUS_RAW_STATE_YEAR_PATH, index=False)
    incidents.to_csv(GIUS_INCIDENTS_PATH, index=False)
    annual_targets.to_csv(GIUS_ANNUAL_TARGETS_PATH, index=False)
    balance_checks.to_csv(GIUS_BALANCE_CHECKS_PATH, index=False)
    variable_dictionary.to_csv(GIUS_VARIABLES_PATH, index=False)
    source_notes.to_csv(GIUS_SOURCES_PATH, index=False)

    summary = {
        "panel_path": str(GIUS_PANEL_PATH),
        "rows": int(final_panel.shape[0]),
        "years": [int(final_panel["year"].min()), int(final_panel["year"].max())],
        "states": int(final_panel["state_abbr"].nunique()),
        "paper_total_killed": int(sum(PAPER_KILLED_TARGETS.values())),
        "paper_total_wounded": int(sum(PAPER_WOUNDED_TARGETS.values())),
        "paper_total_victims": int(sum(PAPER_KILLED_TARGETS.values()) + sum(PAPER_WOUNDED_TARGETS.values())),
        "raw_total_killed": int(raw_state_year["killed_raw"].sum()),
        "raw_total_wounded": int(raw_state_year["wounded_raw"].sum()),
        "calibrated_total_victims": int(final_panel["school_shooting_victims_gius_2018"].sum()),
        "exact_vs_approx": {
            "exact": [
                "Balanced 50-state 1990-2014 panel structure",
                "Annual national killed and wounded totals from Gius (2018) figures",
                "Federal assault-weapons-ban and federal background-check timing",
                "Population, unemployment, land area, age 5-18 counts, alcohol series",
            ],
            "approximate": [
                "State-year allocation of school-shooting victims within each year",
                "Private-sale background-check law crosswalk from Tufts variables",
                "Income control proxied with BEA per capita personal income",
                "Pre-2008 annual bachelor's-degree shares interpolated between Census anchors",
                "Firearm-suicide proxy based on a reconstructed state panel rather than the exact Gius source file",
            ],
        },
    }
    GIUS_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf8")

    print(f"Built: {GIUS_PANEL_PATH}")
    print(f"Rows: {final_panel.shape[0]}")
    print(f"Balanced states x years: {final_panel['state_abbr'].nunique()} x {final_panel['year'].nunique()}")
    print(
        "Paper totals:",
        sum(PAPER_KILLED_TARGETS.values()),
        "killed,",
        sum(PAPER_WOUNDED_TARGETS.values()),
        "wounded,",
        sum(PAPER_KILLED_TARGETS.values()) + sum(PAPER_WOUNDED_TARGETS.values()),
        "victims",
    )


if __name__ == "__main__":
    main()
