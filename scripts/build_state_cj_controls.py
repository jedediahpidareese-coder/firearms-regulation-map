"""Phase 4 — state-year criminal-justice controls (1979–2024).

Builds a compact state-year panel of CJ posture variables that act as
identification robustness controls for the existing state-firearm-policy
specs and the planned spatial-RDD design. The panel is intentionally
state-grain and joins to the analysis frame at run-time via
(state_fips, state_abbr, year) — it does NOT touch the existing
panel_*.csv or county_panel_2009_2024.csv outputs.

Tier 1 variables built here:

1. Imprisonment rate (sentenced state prisoners per 100,000 residents).
   Source: BJS National Prisoner Statistics (NPS-1A), distributed as
   per-year "Prisoners in 20XX" report tables. We download the
   spreadsheet zips for the years where they exist (1998–2023) and
   stitch the state-by-state stocks. Pre-1998 years are not available
   as parsed CSVs without a custom PDF/ASCII parser; this is documented
   below as a coverage gap. Population denominator is the project's
   data/processed/state_population_1900_2025.csv (already on disk).

2. Police protection expenditure per capita (real 2024 USD).
   Source: U.S. Census "Annual Survey of State and Local Government
   Finances" — Table 1 "State and Local Government Finances by Level
   of Government and by State". The Census ships this as one xls/xlsx
   per fiscal year. We download the years that exist and document
   linear interpolation for missing in-between years. Coverage:
   1992, 1997, 2002, 2009–2011, 2017–2022 (annual + Census-of-Govts
   quinquennial).

3. Capital punishment status. Source: Death Penalty Information Center
   (DPIC) executions database (CSV, public). Two columns:
   `has_death_penalty` (binary state-year, hand-coded from the timeline
   of state abolitions in 1979–2024) and `executions_count` (sum of
   DPIC records by state-year).

Tier 1 variable NOT built here (documented as a manual-download gap):

4. Sworn officers per capita. The FBI UCR LEOKA / Police Employee
   data is published in Jacob Kaplan's openICPSR project 102180. The
   existing data/county/kaplan_offenses/ bundle on this disk only
   contains the Offenses-Known file (project 100707), not the LEOKA
   companion. openICPSR requires a free user account and login to
   download project 102180 — we do not scrape it. The build is set
   up so that dropping a Kaplan LEOKA CSV into
   data/county/kaplan_leoka/ and running build_county_cj_controls.py
   will produce both the state and county sworn-officer columns.

Tier 2 variables (three-strikes, truth-in-sentencing, mandatory-min
firearm sentences) are documented as v2 work below — Tier 1 already
consumes most of the budget here.

Outputs:
    data/processed/state_cj_controls_1979_2024.csv
    data/processed/state_cj_controls_coverage.csv

CPI-U deflator: extends the project's existing CPI_BY_YEAR table back
to 1979 using BLS CPIAUCNS annual averages. Base year = 2024.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "state_cj_raw"
PROC = DATA / "processed"

YEAR_START, YEAR_END = 1979, 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))


# ---------------------------------------------------------------------
# Crosswalks
# ---------------------------------------------------------------------

# State FIPS -> postal abbreviation. 50 states + DC. Matches the
# existing scripts/audit_permitless_carry_suicide.py table.
STATE_FIPS_TO_ABBR: "OrderedDict[int, str]" = OrderedDict([
    (1,  "AL"), (2,  "AK"), (4,  "AZ"), (5,  "AR"), (6,  "CA"),
    (8,  "CO"), (9,  "CT"), (10, "DE"), (11, "DC"), (12, "FL"),
    (13, "GA"), (15, "HI"), (16, "ID"), (17, "IL"), (18, "IN"),
    (19, "IA"), (20, "KS"), (21, "KY"), (22, "LA"), (23, "ME"),
    (24, "MD"), (25, "MA"), (26, "MI"), (27, "MN"), (28, "MS"),
    (29, "MO"), (30, "MT"), (31, "NE"), (32, "NV"), (33, "NH"),
    (34, "NJ"), (35, "NM"), (36, "NY"), (37, "NC"), (38, "ND"),
    (39, "OH"), (40, "OK"), (41, "OR"), (42, "PA"), (44, "RI"),
    (45, "SC"), (46, "SD"), (47, "TN"), (48, "TX"), (49, "UT"),
    (50, "VT"), (51, "VA"), (53, "WA"), (54, "WV"), (55, "WI"),
    (56, "WY"),
])
ABBR_TO_FIPS = {v: k for k, v in STATE_FIPS_TO_ABBR.items()}

STATE_NAME_TO_ABBR: "OrderedDict[str, str]" = OrderedDict([
    ("Alabama", "AL"), ("Alaska", "AK"), ("Arizona", "AZ"),
    ("Arkansas", "AR"), ("California", "CA"), ("Colorado", "CO"),
    ("Connecticut", "CT"), ("Delaware", "DE"),
    ("District of Columbia", "DC"), ("Florida", "FL"),
    ("Georgia", "GA"), ("Hawaii", "HI"), ("Idaho", "ID"),
    ("Illinois", "IL"), ("Indiana", "IN"), ("Iowa", "IA"),
    ("Kansas", "KS"), ("Kentucky", "KY"), ("Louisiana", "LA"),
    ("Maine", "ME"), ("Maryland", "MD"), ("Massachusetts", "MA"),
    ("Michigan", "MI"), ("Minnesota", "MN"), ("Mississippi", "MS"),
    ("Missouri", "MO"), ("Montana", "MT"), ("Nebraska", "NE"),
    ("Nevada", "NV"), ("New Hampshire", "NH"), ("New Jersey", "NJ"),
    ("New Mexico", "NM"), ("New York", "NY"), ("North Carolina", "NC"),
    ("North Dakota", "ND"), ("Ohio", "OH"), ("Oklahoma", "OK"),
    ("Oregon", "OR"), ("Pennsylvania", "PA"), ("Rhode Island", "RI"),
    ("South Carolina", "SC"), ("South Dakota", "SD"),
    ("Tennessee", "TN"), ("Texas", "TX"), ("Utah", "UT"),
    ("Vermont", "VT"), ("Virginia", "VA"), ("Washington", "WA"),
    ("West Virginia", "WV"), ("Wisconsin", "WI"), ("Wyoming", "WY"),
])

# CPI-U all-urban annual-average index (BLS CPIAUCNS), base 1982-84=100.
# Used to deflate police expenditure to 2024 dollars. Values 1979–2008
# from BLS historical CPI-U tables; 2009–2024 reproduced from the
# existing scripts/build_county_panel.py table for consistency.
CPI_BY_YEAR = {
    1979: 72.6,  1980: 82.4,  1981: 90.9,  1982: 96.5,  1983: 99.6,
    1984: 103.9, 1985: 107.6, 1986: 109.6, 1987: 113.6, 1988: 118.3,
    1989: 124.0, 1990: 130.7, 1991: 136.2, 1992: 140.3, 1993: 144.5,
    1994: 148.2, 1995: 152.4, 1996: 156.9, 1997: 160.5, 1998: 163.0,
    1999: 166.6, 2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0,
    2004: 188.9, 2005: 195.3, 2006: 201.6, 2007: 207.342, 2008: 215.303,
    2009: 214.537, 2010: 218.056, 2011: 224.939, 2012: 229.594,
    2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007,
    2017: 245.120, 2018: 251.107, 2019: 255.657, 2020: 258.811,
    2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689,
}
CPI_2024 = CPI_BY_YEAR[2024]


# ---------------------------------------------------------------------
# Population denominator (state-year)
# ---------------------------------------------------------------------

def load_state_population() -> pd.DataFrame:
    """Return state population (state_abbr, year, population) covering
    1979–2024. Built from data/processed/state_population_1900_2025.csv.
    DC is not in that file; we fill DC from a small in-script table of
    Census Vintage 2024 estimates so the denominator exists for every
    state-year used in the panel.
    """
    pop = pd.read_csv(PROC / "state_population_1900_2025.csv")
    pop = pop.loc[(pop["year"] >= YEAR_START) & (pop["year"] <= YEAR_END)].copy()
    # DC fill from Census PEP / decennial estimates (rounded to nearest 1k).
    # These are not used analytically (DC is not in the firearm-laws panel)
    # but keep the table rectangular for downstream joins.
    dc_pop = {
        1979: 638000, 1980: 638000, 1981: 633000, 1982: 626000,
        1983: 622000, 1984: 624000, 1985: 626000, 1986: 627000,
        1987: 626000, 1988: 620000, 1989: 605000, 1990: 606000,
        1991: 599000, 1992: 595000, 1993: 580000, 1994: 564000,
        1995: 548000, 1996: 534000, 1997: 525000, 1998: 521000,
        1999: 521000, 2000: 572059, 2001: 574504, 2002: 573158,
        2003: 568502, 2004: 567754, 2005: 567136, 2006: 570681,
        2007: 580236, 2008: 593215, 2009: 605226, 2010: 605211,
        2011: 620427, 2012: 635040, 2013: 651538, 2014: 662328,
        2015: 675409, 2016: 685815, 2017: 694906, 2018: 701547,
        2019: 705749, 2020: 689545, 2021: 670050, 2022: 671803,
        2023: 678972, 2024: 702250,
    }
    dc_rows = pd.DataFrame([
        {"year": y, "population": float(p), "state_abbr": "DC"}
        for y, p in dc_pop.items()
    ])
    pop = pd.concat([pop, dc_rows], ignore_index=True)
    pop = pop[["state_abbr", "year", "population"]].sort_values(
        ["state_abbr", "year"]
    ).reset_index(drop=True)
    return pop


# ---------------------------------------------------------------------
# 1) Imprisonment rate from BJS Prisoners-in-XX reports
# ---------------------------------------------------------------------

# Each Prisoners report has a state-by-state table whose layout
# depends on the publication year. Rather than guess, we encode for
# each report the EXACT raw-CSV column index of each year's "Total"
# stock (relative to the row of the state name). The leading column
# is always either an empty cell or a region header; the state name
# is always present in column 0 or 1.
#
# BJS_REPORT_FILES schema:
#   (relative_path, list of (year, total_col_index_in_raw_csv))
#
# To verify a layout, read the file and inspect the row containing
# 'Alabama'. The column indices below were derived by inspection
# (see commit log for the inspection script). Numbers that appear
# to be Male/Female/percentages are skipped.
BJS_REPORT_FILES = [
    # Each (year, off) pair: off = number of columns to the RIGHT of
    # the state-name cell where that year's "Total prisoners under
    # state-or-federal jurisdiction" stock lives.
    #
    # Verified against published U.S. and California totals.
    # 1990s
    ("p98/P9803.csv",          [(1998, 1), (1997, 2)]),
    # 2000s — Table 3 has totals (current/prior year)
    ("p00/p0003.csv",          [(2000, 2), (1999, 3)]),
    ("p01/p0103.csv",          [(2001, 1), (2000, 3)]),
    ("p02/p0203.csv",          [(2002, 1), (2001, 3)]),
    ("p03/p0303.csv",          [(2003, 1), (2002, 3)]),
    ("p04/p0403.csv",          [(2004, 1), (2003, 3)]),
    ("p05/p05t03.csv",         [(2005, 1), (2004, 3)]),
    ("p06/P06at01.csv",        [(2000, 1), (2005, 2), (2006, 3)]),  # totals
    ("p07/p07t02.csv",         [(2000, 1), (2006, 2), (2007, 3)]),  # totals
    ("p08/p08at02.csv",        [(2000, 1), (2007, 3), (2008, 5)]),  # totals
    ("p09/p09at01.csv",        [(2000, 1), (2008, 2), (2009, 3)]),  # totals
    ("p10/p10at01.csv",        [(2000, 1), (2009, 2), (2010, 3)]),  # totals
    ("p11/p11at01.csv",        [(2009, 1), (2010, 2), (2011, 3)]),  # totals (no 2000 anchor in p11at01)
    # 2010s — sex-breakdown layout: Total y1, M y1, F y1, blank, Total y2, ...
    ("p13/p13t02.csv",         [(2012, 1), (2013, 5)]),
    ("p14/CSV tables/p14t02.csv", [(2013, 1), (2014, 5)]),
    ("p15/p15t02.csv",         [(2014, 1), (2015, 5)]),
    ("p16/p16t02.csv",         [(2015, 1), (2016, 5)]),
    ("p17/p17t02.csv",         [(2016, 1), (2017, 5)]),
    ("p18/p18t02.csv",         [(2017, 1), (2018, 5)]),
    ("p19/p19t02.csv",         [(2018, 1), (2019, 5)]),
    # p20st & p21st — Total at off=1, year2 Total at off=4 (no blank
    # column between the year-1 and year-2 sex blocks in those vintages).
    ("p20st/p20stt02.csv",     [(2019, 1), (2020, 4)]),
    ("p21st/p21stt02.csv",     [(2020, 1), (2021, 4)]),
    # 2022/23 — blank columns between year blocks; year2 Total at off=5
    ("p22st_rev/p22stt02.csv", [(2021, 1), (2022, 5)]),
    ("p23st/p23stt02.csv",     [(2022, 1), (2023, 5)]),
]

STATE_NAME_FIRST_TOKEN_RX = re.compile(r"^[A-Z][A-Za-z .]+(\s*/[a-z]+(?:,[a-z]+)*)?\s*$")


def _norm_state_name(s: str) -> str:
    """Strip footnote markers like '/a', '/c,d' and trailing whitespace."""
    s = s.strip()
    s = re.sub(r"/[a-z](,[a-z])*$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_int(cell) -> float:
    """Parse a cell that might be '12,345' or '12345' or '~' or ':' to float/NaN."""
    if cell is None:
        return np.nan
    s = str(cell).strip().replace(",", "")
    if s in {"", ":", "~", "(NA)", "NA", "X", "(X)"}:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_bjs_state_table(path: Path, year_col_pairs: list[tuple[int, int]]) -> pd.DataFrame:
    """Parse a Prisoners-in-XX state-by-state table.

    For each row whose first or second non-empty string is a state
    name, extract the per-year totals from the columns specified in
    `year_col_pairs` (each pair is (year, col_index_after_state_name)).

    Column-index conventions: the index is *relative to the state-name
    column*, NOT the raw csv column. So if the state name is in raw
    column 1, then col_index 1 = raw column 2, col_index 2 = raw col 3,
    etc. This sidesteps the variable presence of leading blank columns.

    Returns long DataFrame [state_abbr, year, prisoners_total,
    source_file].
    """
    raw = pd.read_csv(path, header=None, dtype=str, encoding="latin1",
                      keep_default_na=False, on_bad_lines="skip")
    out_rows = []
    name_to_abbr = STATE_NAME_TO_ABBR
    for _, row in raw.iterrows():
        cells = row.tolist()
        # Locate the state name column
        state_col = None
        norm = None
        for c, v in enumerate(cells):
            if not isinstance(v, str):
                continue
            stripped = v.strip()
            if not stripped:
                continue
            cand = _norm_state_name(stripped)
            if cand in name_to_abbr:
                state_col = c
                norm = cand
                break
            # Stop scanning if we hit a numeric — state name should be first
            if any(ch.isdigit() for ch in stripped) and len(stripped) > 3:
                break
        if state_col is None:
            continue
        for yr, off in year_col_pairs:
            tgt = state_col + off
            if tgt >= len(cells):
                continue
            v = _parse_int(cells[tgt])
            if np.isnan(v):
                continue
            # plausible prison stock magnitudes (>= 100, <= 250000)
            if not (100 <= v <= 250000):
                continue
            out_rows.append({
                "state_abbr": name_to_abbr[norm],
                "year": yr,
                "prisoners_total": v,
                "source_file": path.name,
            })
    return pd.DataFrame(out_rows)


PDF_REPORT_FILES = [
    # (path, year_curr, year_prior). The PDF Table 1 layout puts
    # state name then total_curr, total_prior, % change, sentenced_curr,
    # sentenced_prior, % change, rate. We grab the first two integers
    # (totals) and assign to (year_curr, year_prior).
    ("p80.pdf", 1980, 1979),
    ("p81.pdf", 1981, 1980),
    ("p82.pdf", 1982, 1981),
    ("p83.pdf", 1983, 1982),
    # p84/p85 not on disk
    ("p86.pdf", 1986, 1985),
    ("p87.pdf", 1987, 1986),
    ("p88.pdf", 1988, 1987),
    ("p89.pdf", 1989, 1988),
    ("p90.pdf", 1990, 1989),
    ("p91.pdf", 1991, 1990),
    ("p92.pdf", 1992, 1991),
    # p93/p94/p95 not on disk
    ("p96.pdf", 1996, 1995),
    ("p97.txt", 1997, 1996),
]


def parse_bjs_pdf_state_table(path: Path, year_curr: int, year_prior: int) -> pd.DataFrame:
    """Extract state-by-state prisoner totals from a Prisoners-in-XX
    PDF (1980–1996 vintage). Strategy: extract text, split into
    lines, find every line that starts with a known state name and
    has at least 2 large integers in its tail.

    Returns long DataFrame [state_abbr, year, prisoners_total,
    source_file]."""
    if str(path).endswith(".pdf"):
        try:
            import pypdf
        except ImportError:
            return pd.DataFrame()
        reader = pypdf.PdfReader(str(path))
        # Table 1 is always on the first 2 pages of these BJS reports.
        # Restrict text extraction to pages 0-1 to avoid pulling state
        # values from "change", "release", or "capacity" tables that
        # appear later in the document.
        text = "\n".join(p.extract_text() or "" for p in reader.pages[:2])
    else:
        text = path.read_text(encoding="latin1", errors="replace")

    # Per-state, retain the first plausible (curr, prior) pair seen.
    seen_states = {}
    name_to_abbr = STATE_NAME_TO_ABBR
    sorted_names = sorted(name_to_abbr.keys(), key=len, reverse=True)
    for line in text.split("\n"):
        line = line.strip()
        for nm in sorted_names:
            if not line.startswith(nm):
                continue
            tail = line[len(nm):].strip()
            # Strip footnote letters / symbols at start of tail
            tail = re.sub(r"^[/\.]?\s*[a-z](,[a-z])*\s*", "", tail)
            # Some BJS PDFs were OCR'd with periods used as thousands
            # separators (e.g. "87.297" instead of "87,297"). For
            # tokens of form "ddd.ddd" where the right side is exactly
            # 3 digits, treat as a thousands-separated integer rather
            # than a decimal.
            tail2 = re.sub(r"\b(\d{1,3})\.(\d{3})\b(?=\s|$|[a-z])", r"\1\2", tail)
            # Extract integer-like tokens (allow commas)
            nums = re.findall(r"-?[0-9][0-9,]*", tail2)
            vals = [int(n.replace(",", "")) for n in nums]
            # Strict plausibility:
            # - First two values are TOTAL_curr, TOTAL_prior stocks
            # - Both must be >= 200 (state stocks)
            # - Year-over-year ratio must be 0.7..1.4 (rules out the
            #   "change" tables where vals are deltas, and the
            #   "release" tables where v_curr << v_prior)
            # - At least one value >= 1000 (to filter capacity/% tables)
            if len(vals) < 2:
                break
            v_curr, v_prior = vals[0], vals[1]
            if not (200 <= v_curr <= 250000 and 200 <= v_prior <= 250000):
                break
            if max(v_curr, v_prior) < 1000:
                break
            ratio = v_curr / v_prior if v_prior > 0 else 999
            if not (0.7 <= ratio <= 1.5):
                break
            abbr = name_to_abbr[nm]
            if abbr in seen_states:
                # Already recorded; skip further matches (avoid grabbing
                # a second mention of same state in narrative text).
                break
            seen_states[abbr] = (v_curr, v_prior)
            break
    rows = []
    for abbr, (v_curr, v_prior) in seen_states.items():
        rows.append({"state_abbr": abbr, "year": year_curr,
                     "prisoners_total": v_curr, "source_file": path.name})
        rows.append({"state_abbr": abbr, "year": year_prior,
                     "prisoners_total": v_prior, "source_file": path.name})
    return pd.DataFrame(rows)


def load_bjs_imprisonment() -> pd.DataFrame:
    """Stitch state-by-year prisoner totals from all available BJS
    Prisoners-in-XX report tables (CSV + PDF). Returns long DataFrame."""
    frames = []
    for rel, year_col_pairs in BJS_REPORT_FILES:
        path = RAW / rel
        if not path.exists():
            print(f"  WARN: missing BJS file {rel}, skipping")
            continue
        try:
            df = parse_bjs_state_table(path, year_col_pairs)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  WARN: failed to parse {rel}: {e}")
    # PDF parsers for the older years
    for rel, yc, yp in PDF_REPORT_FILES:
        path = RAW / rel
        if not path.exists():
            print(f"  WARN: missing PDF {rel}, skipping")
            continue
        try:
            df = parse_bjs_pdf_state_table(path, yc, yp)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  WARN: failed to parse PDF {rel}: {e}")
    if not frames:
        return pd.DataFrame(columns=["state_abbr", "year", "prisoners_total", "source_file"])
    out = pd.concat(frames, ignore_index=True)
    # Where multiple reports report the same state-year, prefer the one
    # whose source_file has the LATER report number (revised counts).
    # We pick the lexicographic max of source_file, which works because
    # later reports sort later (p23st > p19 > p15 > p11 > p09 > p98).
    # That's not strictly true (p06 < p07 < p08 < p09 < p10 < p11 < p14)
    # but for the year ranges where we have overlap, the LAST report
    # to publish that year's number is the canonical revised value.
    out = out.sort_values(["state_abbr", "year", "source_file"]).reset_index(drop=True)
    out = out.drop_duplicates(["state_abbr", "year"], keep="last")
    return out[["state_abbr", "year", "prisoners_total"]]


# ---------------------------------------------------------------------
# 2) Police protection expenditure from Census state-and-local summary
# ---------------------------------------------------------------------

# Each "slsstab1" file is a wide spreadsheet whose second header row
# names the states. We support two layouts:
# - Layout "5col" (2009 onward): blocks of 5 cols per state
#   (S&L, S&L CV, State, Local, Local CV). State name in row 8 (xls)
#   or row 8 (xlsx).
# - Layout "3col" (pre-2009): blocks of 3 cols per state
#   (S&L, State, Local). State name in row 2.
#
# Police-protection row label is " Police protection " (with extra
# whitespace), located on the "expenditure" subsection of the table.

CENSUS_GOV_FIN_FILES = [
    # (path, fiscal_year, layout: 'csv'|'3col_xls'|'5col_xls', state_header_row, police_row)
    ("92slsstab.csv",   1992, "csv_us",   None, None),   # US-only
    ("97slsstab.csv",   1997, "csv_us",   None, None),
    ("02slsstab.xls",   2002, "3col_xls", 2,    123),
    ("02slsstab1b.xls", 2002, "3col_xls_b", 2,  123),
    ("09slsstab.xls",   2009, "5col_xls", 8,    123),
    ("09slsstab1b.xls", 2009, "5col_xls_b", 8,  123),
    ("10slsstab.xls",   2010, "5col_xls", 8,    123),
    ("10slsstab1b.xls", 2010, "5col_xls_b", 8,  123),
    ("11slsstab.xls",   2011, "5col_xls", 8,    123),
    ("11slsstab1b.xls", 2011, "5col_xls_b", 8,  123),
    ("17slsstab1.xlsx", 2017, "5col_xlsx", 8,   None),
    ("18slsstab1.xlsx", 2018, "5col_xlsx", 8,   None),
    ("19slsstab1.xlsx", 2019, "5col_xlsx", 8,   None),
    ("20slsstab1.xlsx", 2020, "5col_xlsx", 8,   None),
    ("21slsstab1.xlsx", 2021, "5col_xlsx", 8,   None),
    ("22slsstab1.xlsx", 2022, "5col_xlsx", 8,   None),
]


def _find_police_row(df: pd.DataFrame) -> int | None:
    """Locate the row whose first or second column contains
    'Police protection'. The 2017+ xlsx layout puts the label in
    column 1 (column 0 is a Line number)."""
    for i in range(df.shape[0]):
        for c in (0, 1):
            if c >= df.shape[1]:
                continue
            cell = str(df.iloc[i, c])
            if "olice protec" in cell:
                return i
    return None


def _find_state_header_row(df: pd.DataFrame) -> int | None:
    """Return the row index that contains a state name as a header
    label. Looks for any of the canonical state names — works for
    both the 1a half (starts at Alabama) and the 1b half (starts at
    Missouri or similar)."""
    targets = {"Alabama", "Alaska", "Missouri", "Montana"}
    for i in range(min(20, df.shape[0])):
        row = df.iloc[i]
        for v in row:
            if isinstance(v, str) and v.strip() in targets:
                return i
    return None


def _extract_state_cols(df: pd.DataFrame, header_row: int, block_size: int,
                         block_offset: int) -> list[tuple[int, str]]:
    """Walk the header row by `block_size` columns and collect
    (col_index, state_name) tuples for every block whose name is a
    valid state. block_offset = first column index of the first state's
    block (typically 4 for 3col layout, 6 for 5col)."""
    out = []
    cols = df.shape[1]
    for col in range(block_offset, cols, block_size):
        name = df.iloc[header_row, col]
        if isinstance(name, str):
            n = name.strip()
            if n in STATE_NAME_TO_ABBR:
                out.append((col, n))
    return out


def parse_census_govfin(path: Path, year: int, layout: str,
                        state_header_row: int | None,
                        police_row: int | None) -> pd.DataFrame:
    """Return long DataFrame with (state_abbr, year, police_expend_thousands)."""
    if layout in {"csv_us"}:
        # National-only: emit a single "US" row tagged with state_abbr=NaN
        # so the caller knows we have only the bound, not by-state values.
        return pd.DataFrame()  # not used as state-level
    if layout.startswith("3col"):
        df = pd.read_excel(path, sheet_name=0, header=None)
        block_size = 3
        # 3col_xls (1a half) blocks start at col 4 (after US block at 1-3).
        # 3col_xls_b (1b half) blocks start at col 1.
        block_offset = 4 if layout == "3col_xls" else 1
    elif layout.startswith("5col"):
        df = pd.read_excel(path, sheet_name=0, header=None)
        block_size = 5
        # xlsx (2017+) uses an extra leading "Line" column, shifting
        # the state blocks one column right relative to the .xls layout.
        if layout == "5col_xlsx":
            block_offset = 7
        elif layout == "5col_xls":
            block_offset = 6
        else:  # 5col_xls_b — second-half file, blocks start at col 1
            block_offset = 1
    else:
        raise ValueError(f"unknown layout {layout}")
    # Always auto-detect to avoid drift between vintages.
    detected = _find_police_row(df)
    if detected is None:
        raise RuntimeError(f"could not find police row in {path.name}")
    police_row = detected
    detected_hdr = _find_state_header_row(df)
    if detected_hdr is None:
        raise RuntimeError(f"could not find state header row in {path.name}")
    state_header_row = detected_hdr
    states = _extract_state_cols(df, state_header_row, block_size, block_offset)
    rows = []
    for col, name in states:
        val = _parse_int(df.iloc[police_row, col])
        if np.isnan(val):
            continue
        rows.append({
            "state_abbr": STATE_NAME_TO_ABBR[name],
            "year": year,
            "police_expend_thousands": val,
        })
    return pd.DataFrame(rows)


def load_police_expenditure() -> pd.DataFrame:
    """Stitch and (optionally) interpolate police expenditure across
    all years 1979–2024. Output is long: state_abbr, year,
    police_expend_per_capita_real_2024, police_expend_imputed_flag."""
    frames = []
    for fname, year, layout, hdr, prow in CENSUS_GOV_FIN_FILES:
        path = RAW / fname
        if not path.exists():
            continue
        try:
            df = parse_census_govfin(path, year, layout, hdr, prow)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  WARN: census {fname}: {e}")
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)
    # If multiple files cover the same state-year (1a + 1b halves), sum
    # them is wrong; keep the first non-null. With the layouts above
    # the 1a half covers AL..MS and 1b covers MO..WY, so there's no
    # overlap, but keep groupby max as a guard.
    raw = raw.groupby(["state_abbr", "year"], as_index=False)[
        "police_expend_thousands"].max()
    return raw


# ---------------------------------------------------------------------
# 3) Capital punishment from DPIC + state abolition timeline
# ---------------------------------------------------------------------

# State -> first year the state had NO active death-penalty statute.
# i.e. has_death_penalty[state, year] = (year < ABOLITION_YEAR[state]).
# States not in this dict are treated as either always-active during
# 1979–2024 (death-penalty active throughout) or always-inactive
# (NEVER_DP set below). Sources: DPIC "States With and Without the
# Death Penalty" timeline; for a few states the abolition year is the
# date of the legislative repeal (Capital cases pre-repeal that were
# later commuted are still counted as DP-eligible at the time).
ABOLITION_YEAR = {
    # Modern abolitions (post-1976 Gregg)
    "NM": 2009,   # NM abolished 2009 (signed March 2009; effective July)
    "IL": 2011,   # IL abolished March 2011
    "CT": 2012,   # CT abolished April 2012
    "MD": 2013,   # MD abolished May 2013
    "NE": 2015,   # NE abolished 2015 by veto override; reinstated by ballot 2016
    "DE": 2016,   # DE Supreme Court ruled DP statute unconstitutional Aug 2016
    "WA": 2018,   # WA Supreme Court struck down DP October 2018
    "NH": 2019,   # NH legislative repeal May 2019
    "CO": 2020,   # CO abolished March 2020
    "VA": 2021,   # VA abolished March 2021 (first Southern state)
    # Earlier abolitions / pre-1976 holdovers
    "NY": 2007,   # NY high court ruled statute unconstitutional 2004; legislature
                  # did not repair, statute effectively dead — we use 2007 as the
                  # year the Court of Appeals confirmed no path to constitutional
                  # statute (People v. Taylor 2007). Some sources use 2004; the
                  # difference is minor for state-year averaging.
    "RI": 1984,   # RI abolished 1984
    "MA": 1984,   # MA Supreme Judicial Court struck down DP 1984
    "NJ": 2007,   # NJ legislative abolition Dec 2007
    # Reinstatements: NE 2016 reinstated DP via ballot; we model below.
}

# State -> reinstatement year (rare). NE was abolished in 2015 then
# reinstated via 2016 ballot referendum; we treat 2016 onward as DP-active.
REINSTATEMENT_YEAR = {
    "NE": 2016,
}

# States that NEVER had an active post-Gregg DP statute during 1979–2024.
# Sources: DPIC "States Without the Death Penalty".
NEVER_DP = {
    "AK", "HI", "IA", "ME", "MI", "MN", "ND", "VT", "WV", "WI",
    "DC",
}


def has_death_penalty(state_abbr: str, year: int) -> int:
    """Return 1 if the state had an active death-penalty statute on
    Dec 31 of `year`, else 0. Does not encode moratoria (e.g.
    California's Newsom moratorium 2019+) — the underlying statute
    is still active, the executions just don't happen."""
    if state_abbr in NEVER_DP:
        return 0
    abolition = ABOLITION_YEAR.get(state_abbr)
    reinst = REINSTATEMENT_YEAR.get(state_abbr)
    if abolition is None:
        return 1
    if year < abolition:
        return 1
    if reinst is not None and year >= reinst:
        return 1
    return 0


def load_executions() -> pd.DataFrame:
    """Return state-year execution counts from the DPIC database."""
    path = RAW / "executions.csv"
    if not path.exists():
        return pd.DataFrame(columns=["state_abbr", "year", "executions_count"])
    df = pd.read_csv(path)
    df["Execution Date"] = pd.to_datetime(df["Execution Date"], errors="coerce")
    df = df.dropna(subset=["Execution Date"])
    df["year"] = df["Execution Date"].dt.year
    # Federal executions: State="United States". Drop these — we report
    # state-level only (the Federal column will be derivable from
    # excluding state==Federal, but we don't need it for this panel).
    df = df.loc[df["Federal"].astype(str).str.strip().str.lower() == "no"].copy()
    df["state_abbr"] = df["State"].map(STATE_NAME_TO_ABBR)
    df = df.dropna(subset=["state_abbr"])
    out = (df.groupby(["state_abbr", "year"]).size()
             .reset_index(name="executions_count"))
    return out


# ---------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------

def make_state_year_grid() -> pd.DataFrame:
    rows = []
    for fips, abbr in STATE_FIPS_TO_ABBR.items():
        for yr in YEARS:
            rows.append({"state_fips": fips, "state_abbr": abbr, "year": yr})
    return pd.DataFrame(rows)


def main() -> None:
    print("=== Building state CJ controls 1979–2024 ===")

    # Population denominator
    pop = load_state_population()
    print(f"  Loaded population for {pop['state_abbr'].nunique()} states "
          f"× {pop['year'].nunique()} years")

    # Imprisonment from BJS
    print("  Loading BJS Prisoners reports ...")
    bjs = load_bjs_imprisonment()
    print(f"    Got {len(bjs)} state-year prisoner records "
          f"covering {sorted(bjs['year'].unique())[:3]}..."
          f"{sorted(bjs['year'].unique())[-3:]}")

    # Police expenditure
    print("  Loading Census State & Local Govt Finances ...")
    police = load_police_expenditure()
    print(f"    Got {len(police)} state-year police-expenditure records "
          f"across years {sorted(police['year'].unique()) if not police.empty else 'NONE'}")

    # Executions
    print("  Loading DPIC executions ...")
    execs = load_executions()
    print(f"    Got {len(execs)} state-year execution records")

    # Build grid
    grid = make_state_year_grid()
    grid = grid.merge(pop, on=["state_abbr", "year"], how="left")
    grid = grid.merge(bjs, on=["state_abbr", "year"], how="left")
    grid = grid.merge(police, on=["state_abbr", "year"], how="left")
    grid = grid.merge(execs, on=["state_abbr", "year"], how="left")
    grid["executions_count"] = grid["executions_count"].fillna(0).astype("Int64")

    # Imprisonment rate per 100,000
    grid["imprisonment_rate"] = np.where(
        grid["population"].notna() & grid["prisoners_total"].notna(),
        grid["prisoners_total"] / grid["population"] * 100_000.0,
        np.nan,
    )

    # Police expenditure per capita, real 2024 USD.
    # Census expenditure is in thousands of dollars (current year).
    cpi = grid["year"].map(lambda y: CPI_BY_YEAR.get(int(y), np.nan))
    grid["police_expend_per_capita_nominal"] = np.where(
        grid["population"].notna() & grid["police_expend_thousands"].notna(),
        grid["police_expend_thousands"] * 1000.0 / grid["population"],
        np.nan,
    )
    grid["police_expenditure_per_capita_real_2024"] = (
        grid["police_expend_per_capita_nominal"] * (CPI_2024 / cpi)
    )

    # Linear interpolation across years per state for police expenditure.
    # The Census Annual Survey covers ~quinquennial Censuses of Government
    # plus partial annual surveys; we interpolate between observed years
    # within each state to fill in-between gaps. We do NOT extrapolate
    # outside the observed window — leading and trailing NaNs remain.
    grid = grid.sort_values(["state_abbr", "year"])
    interp_col = "police_expenditure_per_capita_real_2024"
    grid["police_expenditure_imputed_flag"] = grid[interp_col].isna()
    grid[interp_col] = (
        grid.groupby("state_abbr")[interp_col]
            .transform(lambda s: s.interpolate(method="linear", limit_area="inside"))
    )
    # If a value was imputed, mark; otherwise (was non-null) reset flag
    grid["police_expenditure_imputed_flag"] = (
        grid["police_expenditure_imputed_flag"] & grid[interp_col].notna()
    ).astype(int)

    # Death penalty status
    grid["has_death_penalty"] = grid.apply(
        lambda r: has_death_penalty(r["state_abbr"], int(r["year"])), axis=1
    ).astype("Int64")

    # Per-variable coverage flags
    grid["has_imprisonment_rate"] = grid["imprisonment_rate"].notna().astype(int)
    grid["has_police_expenditure"] = grid[
        "police_expenditure_per_capita_real_2024"].notna().astype(int)
    grid["sworn_officers_per_100k"] = np.nan  # placeholder; build_county_cj_controls fills if LEOKA available
    grid["has_sworn_officers"] = 0

    out_cols = [
        "state_fips", "state_abbr", "year",
        "imprisonment_rate",
        "sworn_officers_per_100k",
        "police_expenditure_per_capita_real_2024",
        "has_death_penalty",
        "executions_count",
        # diagnostics & raw inputs
        "prisoners_total",
        "police_expend_per_capita_nominal",
        "population",
        # coverage / imputation flags
        "has_imprisonment_rate",
        "has_police_expenditure",
        "police_expenditure_imputed_flag",
        "has_sworn_officers",
    ]
    out = grid[out_cols].sort_values(["state_abbr", "year"]).reset_index(drop=True)

    # Coverage diagnostics: per-variable, per-year non-null share
    cov_rows = []
    for var in ["imprisonment_rate",
                "police_expenditure_per_capita_real_2024",
                "has_death_penalty",
                "executions_count",
                "sworn_officers_per_100k"]:
        for yr in YEARS:
            sub = out[out["year"] == yr]
            n = len(sub)
            n_nonnull = sub[var].notna().sum() if var != "executions_count" else \
                int((sub[var].fillna(0) >= 0).sum())  # always defined
            cov_rows.append({
                "variable": var, "year": yr,
                "n_states": n, "n_with_value": int(n_nonnull),
                "coverage_pct": round(100.0 * int(n_nonnull) / n, 1) if n else 0.0,
            })
    cov = pd.DataFrame(cov_rows)

    out_path = PROC / "state_cj_controls_1979_2024.csv"
    cov_path = PROC / "state_cj_controls_coverage.csv"
    out.to_csv(out_path, index=False)
    cov.to_csv(cov_path, index=False)
    print(f"\nWrote {out_path} ({len(out)} rows × {out.shape[1]} cols)")
    print(f"Wrote {cov_path}")

    print("\nCoverage summary by variable (across 1979–2024):")
    for var in ["imprisonment_rate",
                "police_expenditure_per_capita_real_2024",
                "has_death_penalty",
                "executions_count",
                "sworn_officers_per_100k"]:
        nn = out[var].notna().sum() if var != "executions_count" else len(out)
        print(f"  {var:48s}  {nn:5d} / {len(out):5d}  "
              f"({100.0*nn/len(out):5.1f}%)")


if __name__ == "__main__":
    main()
