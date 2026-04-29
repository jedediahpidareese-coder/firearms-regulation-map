from __future__ import annotations

import json
import math
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "outputs" / "permitless_carry_suicide_audit"

CORE_PANEL_PATH = PROCESSED_DIR / "panel_core_1979_2024.csv"
MORTALITY_PATH = DATA_DIR / "firearm_suicide_homicide_dataset_v2.tab"
ALCOHOL_PATH = DATA_DIR / "pcyr1970_2023.txt"

TREATMENT_VARIABLE = "permitconcealed"
MAY_ISSUE_VARIABLE = "mayissue"
ANALYSIS_START_YEAR = 1979
ANALYSIS_END_YEAR = 2023
EVENT_WINDOW = (-5, 3)
OMITTED_EVENT_TIME = -1
LOG_RATE_OFFSET = 0.01
EARLY_ADOPTER_CUTOFF = 2011
BRUEN_YEAR = 2022

CORE_CONTROLS = [
    "ln_population",
    "unemployment_rate",
    "ln_pcpi_real_2024",
    "violent_rate",
    "property_rate",
]
ALCOHOL_CONTROL = "per_capita_alcohol_ethanol_14plus"

OUTCOMES = [
    "firearm_suicide_rate",
    "nonfirearm_suicide_rate",
    "total_suicide_rate",
    "firearm_suicide_share",
    "ln_firearm_suicide_rate",
    "ln_nonfirearm_suicide_rate",
    "ln_total_suicide_rate",
    "logit_firearm_suicide_share",
]

STATE_FIPS_TO_ABBR = {
    1: "AL",
    2: "AK",
    4: "AZ",
    5: "AR",
    6: "CA",
    8: "CO",
    9: "CT",
    10: "DE",
    11: "DC",
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


def sanitize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def load_alcohol_series(state_lookup: pd.DataFrame) -> pd.DataFrame:
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
        (alcohol["beverage_type"] == 4)
        & alcohol["state_abbr"].isin(state_lookup["state_abbr"])
        & alcohol["year"].between(ANALYSIS_START_YEAR, ANALYSIS_END_YEAR)
    ].copy()
    alcohol[ALCOHOL_CONTROL] = alcohol["per_capita_age_14_plus_raw"] / 10000.0
    alcohol = alcohol.merge(state_lookup, on="state_abbr", how="left")
    return alcohol[["state", "state_abbr", "year", ALCOHOL_CONTROL]]


def load_analysis_panel() -> pd.DataFrame:
    core = pd.read_csv(CORE_PANEL_PATH)
    core = core.loc[core["year"].between(ANALYSIS_START_YEAR, ANALYSIS_END_YEAR)].copy()
    core["year"] = core["year"].astype(int)
    state_lookup = core[["state", "state_abbr"]].drop_duplicates()

    mortality = pd.read_csv(MORTALITY_PATH, sep="\t")
    mortality["state"] = mortality["state"].str.replace('"', "", regex=False).str.title()
    mortality["year"] = pd.to_numeric(mortality["year"], errors="coerce").astype("Int64")
    mortality = mortality.loc[
        mortality["year"].between(ANALYSIS_START_YEAR, ANALYSIS_END_YEAR)
        & (mortality["state"] != "District Of Columbia")
    ].copy()
    mortality["year"] = mortality["year"].astype(int)

    panel = core.merge(
        mortality[
            [
                "state",
                "year",
                "firearm_suicides",
                "total_suicides",
                "firearm_homicides",
                "total_homicides",
                "fss",
            ]
        ],
        on=["state", "year"],
        how="left",
        validate="one_to_one",
    )
    panel = panel.merge(load_alcohol_series(state_lookup), on=["state", "state_abbr", "year"], how="left")

    panel["nonfirearm_suicides"] = panel["total_suicides"] - panel["firearm_suicides"]
    panel["firearm_suicide_rate"] = 100000.0 * panel["firearm_suicides"] / panel["population"]
    panel["nonfirearm_suicide_rate"] = 100000.0 * panel["nonfirearm_suicides"] / panel["population"]
    panel["total_suicide_rate"] = 100000.0 * panel["total_suicides"] / panel["population"]
    panel["firearm_suicide_share"] = panel["firearm_suicides"] / panel["total_suicides"]
    panel["ln_firearm_suicide_rate"] = np.log(panel["firearm_suicide_rate"] + LOG_RATE_OFFSET)
    panel["ln_nonfirearm_suicide_rate"] = np.log(panel["nonfirearm_suicide_rate"] + LOG_RATE_OFFSET)
    panel["ln_total_suicide_rate"] = np.log(panel["total_suicide_rate"] + LOG_RATE_OFFSET)
    panel["logit_firearm_suicide_share"] = np.log(
        (panel["firearm_suicides"] + 0.5) / (panel["nonfirearm_suicides"] + 0.5)
    )
    return panel.sort_values(["state", "year"]).reset_index(drop=True)


def build_treatment_table(core_full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, group in core_full.sort_values(["state", "year"]).groupby("state"):
        values = group[TREATMENT_VARIABLE].to_numpy()
        years = group["year"].to_numpy()
        adoption_year = None
        reversals_after_adoption: list[int] = []
        for idx in range(1, len(group)):
            if values[idx - 1] == 1 and values[idx] == 0 and adoption_year is None:
                adoption_year = int(years[idx])
            elif adoption_year is not None and values[idx - 1] == 0 and values[idx] == 1:
                reversals_after_adoption.append(int(years[idx]))
        post_values = group.loc[group["year"] >= adoption_year, TREATMENT_VARIABLE] if adoption_year else pd.Series(dtype=float)
        rows.append(
            {
                "state": state,
                "state_abbr": group["state_abbr"].iloc[0],
                "treatment_variable": TREATMENT_VARIABLE,
                "adoption_rule": "first 1-to-0 switch in permitconcealed",
                "adoption_year": adoption_year,
                "included_in_mortality_sample": bool(adoption_year is not None and adoption_year <= ANALYSIS_END_YEAR),
                "absorbing_after_adoption_through_2024": bool(adoption_year is not None and post_values.eq(0).all()),
                "post_adoption_reversal_years": ";".join(map(str, reversals_after_adoption)),
                "starts_permit_required": int(values[0]),
                "ends_permit_required": int(values[-1]),
            }
        )
    return pd.DataFrame(rows)


def control_states_for_treated_unit(
    panel: pd.DataFrame,
    treated_state: str,
    adoption_year: int,
    excluded_states: set[str],
) -> list[str]:
    start, end = EVENT_WINDOW
    window = panel.loc[panel["year"].between(adoption_year + start, adoption_year + end)].copy()
    controls = []
    for state, group in window.groupby("state"):
        if state == treated_state or state in excluded_states:
            continue
        if group[TREATMENT_VARIABLE].eq(1).all() and group[MAY_ISSUE_VARIABLE].eq(0).all():
            controls.append(state)
    return sorted(controls)


def build_stacked_sample(
    panel: pd.DataFrame,
    adoption_table: pd.DataFrame,
    *,
    max_year: int | None = None,
    exclude_years: set[int] | None = None,
    exclude_states: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    exclude_years = exclude_years or set()
    exclude_states = exclude_states or set()
    treated = adoption_table.loc[
        adoption_table["included_in_mortality_sample"] & ~adoption_table["state"].isin(exclude_states)
    ].copy()
    stacks = []
    membership_rows = []
    for _, row in treated.iterrows():
        treated_state = row["state"]
        adoption_year = int(row["adoption_year"])
        start_year = adoption_year + EVENT_WINDOW[0]
        end_year = adoption_year + EVENT_WINDOW[1]
        sample_end_year = min(end_year, max_year) if max_year is not None else end_year
        window = panel.loc[panel["year"].between(start_year, sample_end_year)].copy()
        if exclude_years:
            window = window.loc[~window["year"].isin(exclude_years)].copy()
        window = window.loc[~window["state"].isin(exclude_states)].copy()
        controls = control_states_for_treated_unit(panel, treated_state, adoption_year, exclude_states)
        keep_states = [treated_state] + controls
        stack = window.loc[window["state"].isin(keep_states)].copy()
        stack["stack_id"] = f"{row['state_abbr']}_{adoption_year}"
        stack["treated_unit_state"] = treated_state
        stack["treated_unit_abbr"] = row["state_abbr"]
        stack["adoption_year"] = adoption_year
        stack["treated_state"] = (stack["state"] == treated_state).astype(int)
        stack["event_time"] = stack["year"] - adoption_year
        stack["post"] = ((stack["treated_state"] == 1) & (stack["event_time"] >= 0)).astype(int)
        if stack.loc[stack["treated_state"].eq(1), "post"].sum() == 0:
            membership_rows.append(
                {
                    "stack_id": f"{row['state_abbr']}_{adoption_year}",
                    "treated_state": treated_state,
                    "adoption_year": adoption_year,
                    "included": False,
                    "reason_excluded": "no treated post-treatment observations after calendar restrictions",
                    "control_state_count": len(controls),
                    "control_states": ";".join(controls),
                }
            )
            continue
        membership_rows.append(
            {
                "stack_id": f"{row['state_abbr']}_{adoption_year}",
                "treated_state": treated_state,
                "adoption_year": adoption_year,
                "included": True,
                "reason_excluded": "",
                "control_state_count": len(controls),
                "control_states": ";".join(controls),
            }
        )
        stacks.append(stack)
    if not stacks:
        return pd.DataFrame(), pd.DataFrame(membership_rows)
    stacked = pd.concat(stacks, ignore_index=True)
    stacked["state_stack_fe"] = stacked["state_abbr"] + "_" + stacked["stack_id"]
    stacked["year_stack_fe"] = stacked["year"].astype(str) + "_" + stacked["stack_id"]
    return stacked, pd.DataFrame(membership_rows)


def build_cohort_year_sample(panel: pd.DataFrame, adoption_table: pd.DataFrame, cohort_year: int) -> pd.DataFrame:
    treated_states = adoption_table.loc[adoption_table["adoption_year"].eq(cohort_year), "state"].tolist()
    if not treated_states:
        return pd.DataFrame()
    start_year = cohort_year + EVENT_WINDOW[0]
    end_year = cohort_year + EVENT_WINDOW[1]
    window = panel.loc[panel["year"].between(start_year, end_year)].copy()
    controls = []
    for state, group in window.groupby("state"):
        if state in treated_states:
            continue
        if group[TREATMENT_VARIABLE].eq(1).all() and group[MAY_ISSUE_VARIABLE].eq(0).all():
            controls.append(state)
    sample = window.loc[window["state"].isin(treated_states + controls)].copy()
    sample["stack_id"] = f"cohort_{cohort_year}"
    sample["treated_unit_state"] = ";".join(treated_states)
    sample["treated_unit_abbr"] = ""
    sample["adoption_year"] = cohort_year
    sample["treated_state"] = sample["state"].isin(treated_states).astype(int)
    sample["event_time"] = sample["year"] - cohort_year
    sample["post"] = ((sample["treated_state"] == 1) & (sample["event_time"] >= 0)).astype(int)
    sample["state_stack_fe"] = sample["state_abbr"] + "_" + sample["stack_id"]
    sample["year_stack_fe"] = sample["year"].astype(str) + "_" + sample["stack_id"]
    return sample


class FitResult:
    def __init__(self, names: list[str], beta: np.ndarray, vcov: np.ndarray, nobs: int, clusters: int, rank: int):
        self.names = names
        self.beta = beta
        self.vcov = vcov
        self.nobs = nobs
        self.clusters = clusters
        self.rank = rank

    def coef_row(self, term: str) -> dict[str, float | int | str]:
        idx = self.names.index(term)
        coef = float(self.beta[idx])
        se = float(math.sqrt(self.vcov[idx, idx])) if self.vcov[idx, idx] >= 0 else float("nan")
        t_stat = coef / se if se and not math.isnan(se) else float("nan")
        p_value = float(2 * stats.norm.sf(abs(t_stat))) if not math.isnan(t_stat) else float("nan")
        return {
            "term": term,
            "coefficient": coef,
            "std_error": se,
            "t_stat": t_stat,
            "p_value_normal": p_value,
            "ci95_low": coef - 1.96 * se if not math.isnan(se) else float("nan"),
            "ci95_high": coef + 1.96 * se if not math.isnan(se) else float("nan"),
            "nobs": self.nobs,
            "clusters": self.clusters,
            "rank": self.rank,
        }


def fit_ols_cluster(
    data: pd.DataFrame,
    outcome: str,
    terms: list[str],
    controls: list[str],
    *,
    cluster_col: str = "state_abbr",
) -> FitResult | None:
    required = [outcome, cluster_col, "state_stack_fe", "year_stack_fe", *terms, *controls]
    frame = data.dropna(subset=required).copy().reset_index(drop=True)
    if frame.empty:
        return None

    regressors = terms + controls
    # Keep terms with variation after sample restrictions.
    kept_regressors = [col for col in regressors if frame[col].nunique(dropna=True) > 1]
    if not kept_regressors:
        return None

    state_fe = pd.get_dummies(frame["state_stack_fe"], drop_first=True, dtype=float)
    year_fe = pd.get_dummies(frame["year_stack_fe"], drop_first=True, dtype=float)
    x = np.column_stack(
        [
            np.ones(len(frame)),
            frame[kept_regressors].to_numpy(dtype=float),
            state_fe.to_numpy(dtype=float),
            year_fe.to_numpy(dtype=float),
        ]
    )
    names = ["const", *kept_regressors, *state_fe.columns.tolist(), *year_fe.columns.tolist()]
    y = frame[outcome].to_numpy(dtype=float)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    xtx_inv = np.linalg.pinv(x.T @ x)
    meat = np.zeros((x.shape[1], x.shape[1]))
    clusters = frame[cluster_col].astype(str)
    for _, index in frame.groupby(clusters).groups.items():
        idx = np.asarray(index)
        xi = x[idx, :]
        ui = residual[idx]
        xu = xi.T @ ui
        meat += np.outer(xu, xu)
    rank = int(np.linalg.matrix_rank(x))
    nobs = int(len(frame))
    nclusters = int(clusters.nunique())
    vcov = xtx_inv @ meat @ xtx_inv
    if nclusters > 1 and nobs > rank:
        vcov *= (nclusters / (nclusters - 1)) * ((nobs - 1) / (nobs - rank))
    return FitResult(names=names, beta=beta, vcov=vcov, nobs=nobs, clusters=nclusters, rank=rank)


def average_post_results(stacked: pd.DataFrame, controls_by_spec: dict[str, list[str]], sample_label: str) -> pd.DataFrame:
    rows = []
    for controls_name, controls in controls_by_spec.items():
        for outcome in OUTCOMES:
            fit = fit_ols_cluster(stacked, outcome, ["post"], controls)
            if fit is None or "post" not in fit.names:
                continue
            row = fit.coef_row("post")
            row.update(
                {
                    "sample": sample_label,
                    "outcome": outcome,
                    "controls_spec": controls_name,
                    "controls": ";".join(controls),
                    "model": "average_post",
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def event_study_results(stacked: pd.DataFrame, controls: list[str], sample_label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    tests = []
    event_times = [e for e in range(EVENT_WINDOW[0], EVENT_WINDOW[1] + 1) if e != OMITTED_EVENT_TIME]
    for event_time in event_times:
        stacked[f"event_{event_time}"] = (
            (stacked["treated_state"].eq(1)) & (stacked["event_time"].eq(event_time))
        ).astype(int)
    event_terms = [f"event_{event_time}" for event_time in event_times]
    pre_terms = [f"event_{event_time}" for event_time in event_times if event_time < OMITTED_EVENT_TIME]
    for outcome in OUTCOMES:
        fit = fit_ols_cluster(stacked, outcome, event_terms, controls)
        if fit is None:
            continue
        for event_time in event_times:
            term = f"event_{event_time}"
            if term not in fit.names:
                continue
            row = fit.coef_row(term)
            row.update(
                {
                    "sample": sample_label,
                    "outcome": outcome,
                    "controls_spec": "core_controls",
                    "event_time": event_time,
                    "omitted_event_time": OMITTED_EVENT_TIME,
                    "model": "event_study",
                }
            )
            rows.append(row)
        kept_pre_terms = [term for term in pre_terms if term in fit.names]
        if kept_pre_terms:
            indices = [fit.names.index(term) for term in kept_pre_terms]
            beta = fit.beta[indices]
            vcov = fit.vcov[np.ix_(indices, indices)]
            wald = float(beta.T @ np.linalg.pinv(vcov) @ beta)
            df = len(indices)
            p_value = float(stats.chi2.sf(wald, df))
            tests.append(
                {
                    "sample": sample_label,
                    "outcome": outcome,
                    "controls_spec": "core_controls",
                    "pre_periods_tested": ";".join(term.replace("event_", "") for term in kept_pre_terms),
                    "wald_chi2": wald,
                    "df": df,
                    "p_value_chi2": p_value,
                    "nobs": fit.nobs,
                    "clusters": fit.clusters,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(tests)


def svg_line(x1: float, y1: float, x2: float, y2: float, stroke: str = "#333333", width: float = 1.0) -> str:
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{width:.2f}" />'


def svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "middle", color: str = "#222222") -> str:
    escaped = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escaped}</text>'


def plot_event_studies(event_rows: pd.DataFrame) -> list[Path]:
    plot_paths: list[Path] = []
    for outcome, group in event_rows.groupby("outcome"):
        group = group.sort_values("event_time")
        width, height = 900, 560
        left, right, top, bottom = 92, 32, 58, 74
        plot_w = width - left - right
        plot_h = height - top - bottom
        y_values = pd.concat(
            [
                group["ci95_low"],
                group["ci95_high"],
                pd.Series([0.0]),
            ],
            ignore_index=True,
        )
        y_min = float(y_values.min())
        y_max = float(y_values.max())
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0
        y_pad = 0.08 * (y_max - y_min)
        y_min -= y_pad
        y_max += y_pad

        event_min, event_max = EVENT_WINDOW

        def scale_x(value: float) -> float:
            return left + ((value - event_min) / (event_max - event_min)) * plot_w

        def scale_y(value: float) -> float:
            return top + ((y_max - value) / (y_max - y_min)) * plot_h

        pieces = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff" />',
            svg_text(width / 2, 28, outcome.replace("_", " ").title(), 18),
            svg_line(left, top, left, top + plot_h, "#222222", 1.1),
            svg_line(left, top + plot_h, left + plot_w, top + plot_h, "#222222", 1.1),
            svg_line(left, scale_y(0), left + plot_w, scale_y(0), "#777777", 1.0),
            svg_line(scale_x(-0.5), top, scale_x(-0.5), top + plot_h, "#999999", 1.0),
        ]
        for tick in np.linspace(y_min, y_max, 5):
            y = scale_y(float(tick))
            pieces.append(svg_line(left - 5, y, left + plot_w, y, "#dddddd", 0.7))
            pieces.append(svg_text(left - 10, y + 4, f"{tick:.3g}", 11, "end", "#333333"))
        for event_time in range(EVENT_WINDOW[0], EVENT_WINDOW[1] + 1):
            x = scale_x(event_time)
            pieces.append(svg_line(x, top + plot_h, x, top + plot_h + 5, "#222222", 1.0))
            pieces.append(svg_text(x, top + plot_h + 22, str(event_time), 11))
        points = []
        for _, row in group.iterrows():
            x = scale_x(float(row["event_time"]))
            y = scale_y(float(row["coefficient"]))
            low = scale_y(float(row["ci95_low"]))
            high = scale_y(float(row["ci95_high"]))
            pieces.append(svg_line(x, low, x, high, "#7BA7C4", 1.4))
            pieces.append(svg_line(x - 4, low, x + 4, low, "#7BA7C4", 1.2))
            pieces.append(svg_line(x - 4, high, x + 4, high, "#7BA7C4", 1.2))
            points.append((x, y))
        if points:
            path_data = " ".join(("M" if i == 0 else "L") + f" {x:.2f} {y:.2f}" for i, (x, y) in enumerate(points))
            pieces.append(f'<path d="{path_data}" fill="none" stroke="#125E8A" stroke-width="2" />')
            for x, y in points:
                pieces.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#125E8A" />')
        pieces.append(svg_text(left + plot_w / 2, height - 28, "Event time relative to permitless-carry adoption", 12))
        pieces.append(
            f'<text x="20" y="{top + plot_h / 2:.2f}" font-family="Arial, sans-serif" font-size="12" fill="#222222" text-anchor="middle" transform="rotate(-90 20 {top + plot_h / 2:.2f})">Coefficient relative to event time -1</text>'
        )
        pieces.append("</svg>")
        path = OUTPUT_DIR / "figures" / f"event_study_{sanitize_name(outcome)}.svg"
        path.write_text("\n".join(pieces), encoding="utf-8")
        plot_paths.append(path)
    return plot_paths


def cohort_year_results(panel: pd.DataFrame, adoption_table: pd.DataFrame, controls: list[str]) -> pd.DataFrame:
    rows = []
    for cohort_year in sorted(adoption_table.loc[adoption_table["included_in_mortality_sample"], "adoption_year"].dropna().unique()):
        cohort_year = int(cohort_year)
        sample = build_cohort_year_sample(panel, adoption_table, cohort_year)
        if sample.empty:
            continue
        for outcome in OUTCOMES:
            fit = fit_ols_cluster(sample, outcome, ["post"], controls)
            if fit is None or "post" not in fit.names:
                continue
            row = fit.coef_row("post")
            row.update(
                {
                    "cohort_year": cohort_year,
                    "treated_states": sample["treated_unit_state"].iloc[0],
                    "outcome": outcome,
                    "controls_spec": "core_controls",
                    "model": "cohort_year_average_post",
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def treated_state_results(stacked: pd.DataFrame, controls: list[str]) -> pd.DataFrame:
    rows = []
    for stack_id, sample in stacked.groupby("stack_id"):
        for outcome in OUTCOMES:
            fit = fit_ols_cluster(sample, outcome, ["post"], controls)
            if fit is None or "post" not in fit.names:
                continue
            row = fit.coef_row("post")
            row.update(
                {
                    "stack_id": stack_id,
                    "treated_state": sample["treated_unit_state"].iloc[0],
                    "adoption_year": int(sample["adoption_year"].iloc[0]),
                    "outcome": outcome,
                    "controls_spec": "core_controls",
                    "model": "treated_state_average_post",
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_panel(panel: pd.DataFrame, stacked: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"metric": "analysis_panel_rows", "value": len(panel), "detail": "50 states x 1979-2023 after mortality merge"},
        {"metric": "analysis_panel_states", "value": panel["state"].nunique(), "detail": "DC excluded because the core law panel is 50 states"},
        {"metric": "analysis_panel_years", "value": panel["year"].nunique(), "detail": f"{ANALYSIS_START_YEAR}-{ANALYSIS_END_YEAR}"},
        {
            "metric": "missing_firearm_suicides",
            "value": int(panel["firearm_suicides"].isna().sum()),
            "detail": "Required for suicide outcomes",
        },
        {
            "metric": "missing_total_suicides",
            "value": int(panel["total_suicides"].isna().sum()),
            "detail": "Required for suicide outcomes",
        },
        {"metric": "stacked_rows", "value": len(stacked), "detail": "Main stacked sample"},
        {"metric": "stacked_distinct_states", "value": stacked["state"].nunique(), "detail": "States appearing in any stack"},
        {"metric": "included_treated_units", "value": int(membership["included"].sum()), "detail": "Treated state adoption stacks"},
        {
            "metric": "post_bruen_calendar_years_included",
            "value": int(stacked["year"].ge(BRUEN_YEAR).any()),
            "detail": "1 means 2022-2023 are included in the main analysis",
        },
    ]
    return pd.DataFrame(rows)


def outcome_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome in OUTCOMES:
        series = panel[outcome]
        rows.append(
            {
                "outcome": outcome,
                "nonmissing": int(series.notna().sum()),
                "zeros": int(series.eq(0).sum()) if pd.api.types.is_numeric_dtype(series) else "",
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
            }
        )
    return pd.DataFrame(rows)


def write_config() -> None:
    config = {
        "treatment_variable": TREATMENT_VARIABLE,
        "treatment_interpretation": "permitless concealed carry; permitconcealed switches from 1 to 0",
        "adoption_rule": "first observed 1-to-0 switch in permitconcealed",
        "absorbing_assumption": "estimated as absorbing after the first 1-to-0 switch; reversals are audited in treatment_adoption_table.csv",
        "partial_year_handling": "annual Tufts coding is used as given; the switch year is treated as event time 0 with no within-year proration",
        "analysis_years": [ANALYSIS_START_YEAR, ANALYSIS_END_YEAR],
        "event_window": list(EVENT_WINDOW),
        "omitted_event_time": OMITTED_EVENT_TIME,
        "dc_excluded": True,
        "post_bruen_years_in_main": "2022 and 2023 are included; 2024 is excluded because suicide outcomes end in 2023",
        "comparison_group": (
            "For each treated-state stack, controls must retain permitconcealed==1 and mayissue==0 "
            "for every year in the event window; later adopters can be controls only if untreated throughout that stack window."
        ),
        "controls": {
            "no_controls": [],
            "core_controls": CORE_CONTROLS,
            "core_plus_alcohol": [*CORE_CONTROLS, ALCOHOL_CONTROL],
        },
        "weights": "none",
        "clustering": "state_abbr",
        "log_rate_offset": LOG_RATE_OFFSET,
        "share_logit_continuity_correction": "firearm_suicides + 0.5 divided by nonfirearm_suicides + 0.5",
    }
    (OUTPUT_DIR / "analysis_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "figures").mkdir(parents=True, exist_ok=True)

    core_full = pd.read_csv(CORE_PANEL_PATH)
    panel = load_analysis_panel()
    adoption_table = build_treatment_table(core_full)
    adoption_table.to_csv(OUTPUT_DIR / "treatment_adoption_table.csv", index=False)

    stacked, membership = build_stacked_sample(panel, adoption_table)
    stacked.to_csv(OUTPUT_DIR / "stacked_sample_main.csv", index=False)
    membership.to_csv(OUTPUT_DIR / "sample_membership_by_treated_state.csv", index=False)

    summarize_panel(panel, stacked, membership).to_csv(OUTPUT_DIR / "analysis_panel_summary.csv", index=False)
    outcome_summary(panel).to_csv(OUTPUT_DIR / "outcome_summary.csv", index=False)
    write_config()

    controls_by_spec = {
        "no_controls": [],
        "core_controls": CORE_CONTROLS,
        "core_plus_alcohol": [*CORE_CONTROLS, ALCOHOL_CONTROL],
    }

    avg_main = average_post_results(stacked, controls_by_spec, "main")
    avg_main.to_csv(OUTPUT_DIR / "average_post_results.csv", index=False)

    event_rows, pretrend_tests = event_study_results(stacked.copy(), CORE_CONTROLS, "main")
    event_rows.to_csv(OUTPUT_DIR / "event_study_coefficients.csv", index=False)
    pretrend_tests.to_csv(OUTPUT_DIR / "joint_pretrend_tests.csv", index=False)
    plot_paths = plot_event_studies(event_rows)
    pd.DataFrame({"figure_path": [str(path) for path in plot_paths]}).to_csv(OUTPUT_DIR / "figure_index.csv", index=False)

    cohort_year_results(panel, adoption_table, CORE_CONTROLS).to_csv(OUTPUT_DIR / "cohort_year_estimates.csv", index=False)
    treated_state_results(stacked, CORE_CONTROLS).to_csv(OUTPUT_DIR / "treated_state_estimates.csv", index=False)

    restricted_rows = []
    restrictions = [
        ("exclude_2020_2023", {"exclude_years": {2020, 2021, 2022, 2023}}),
        ("exclude_post_bruen_years", {"max_year": BRUEN_YEAR - 1}),
    ]
    for label, kwargs in restrictions:
        restricted_stack, restricted_membership = build_stacked_sample(panel, adoption_table, **kwargs)
        restricted_membership.to_csv(OUTPUT_DIR / f"sample_membership_{label}.csv", index=False)
        if restricted_stack.empty:
            continue
        result = average_post_results(restricted_stack, {"no_controls": [], "core_controls": CORE_CONTROLS}, label)
        restricted_rows.append(result)
    if restricted_rows:
        pd.concat(restricted_rows, ignore_index=True).to_csv(OUTPUT_DIR / "calendar_restriction_results.csv", index=False)

    early_adopters = adoption_table.loc[
        adoption_table["included_in_mortality_sample"] & adoption_table["adoption_year"].le(EARLY_ADOPTER_CUTOFF),
        "state",
    ].tolist()
    loo_rows = []
    for state in early_adopters:
        loo_stack, _ = build_stacked_sample(panel, adoption_table, exclude_states={state})
        if loo_stack.empty:
            continue
        result = average_post_results(loo_stack, {"no_controls": [], "core_controls": CORE_CONTROLS}, f"exclude_{state}")
        result["excluded_early_adopter"] = state
        loo_rows.append(result)
    if loo_rows:
        pd.concat(loo_rows, ignore_index=True).to_csv(OUTPUT_DIR / "leave_one_early_adopter_out_results.csv", index=False)

    print(f"Wrote permitless-carry suicide audit outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
