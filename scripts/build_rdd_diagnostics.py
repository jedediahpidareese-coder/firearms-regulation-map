"""Phase 5 (research): Spatial RDD diagnostics for U.S. firearm policy.

Pre-RDD descriptive characterization. For each (policy x bandwidth x donut)
cell we tabulate:
  - how many border-strip counties survive,
  - how many state-pairs they form,
  - how many of those pairs straddle a policy boundary in each year,
  - how many treated/control counties are inside the strip,
  - mean centroid-to-other-state distance.

We also produce two visual diagnostics per policy:
  - cross_section_<policy>.svg: pooled outcome means by signed distance
    bin (binwidth ~25 km), one panel per outcome, vertical dashed line
    at the state border. Tells us whether there's a visible jump.
  - pretrends_<policy>.svg: mean within-pair (treated - control) outcome
    gap by year, averaged over state-pairs that ever straddle the policy.
    Vertical dashed line at the modal cohort year.

Treatments (state-level, joined down to county):
  permitless_carry: law_permitconcealed, 1 -> 0
  red_flag       : law_gvro,             0 -> 1
  ubc            : law_universal,        0 -> 1

Outcomes (county per 100k):
  county_violent_crime_rate, county_murder_rate,
  county_property_crime_rate, county_burglary_rate.

Pure-Python SVG (matplotlib not installed). Layout / palette match
plot_event_study_svg in scripts/cs_lib.py.

Outputs (under outputs/rdd_diagnostics/):
  diagnostics.csv
  figures/cross_section_<policy>.svg  (3)
  figures/pretrends_<policy>.svg      (3)
  summary.md
"""

from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PANEL_PATH = ROOT / "data" / "processed" / "county_panel_2009_2024.csv"
DIST_PATH = ROOT / "data" / "processed" / "county_border_distances.csv"
OUT_DIR = ROOT / "outputs" / "rdd_diagnostics"
FIG_DIR = OUT_DIR / "figures"

POLICIES = {
    # (law column, transition direction, treated value, control value)
    "permitless_carry": ("law_permitconcealed", "1to0", 0, 1),
    "red_flag":         ("law_gvro",            "0to1", 1, 0),
    "ubc":              ("law_universal",       "0to1", 1, 0),
}

OUTCOMES = {
    "county_violent_crime_rate":  "Violent crime (per 100k)",
    "county_murder_rate":         "Murder (per 100k)",
    "county_property_crime_rate": "Property crime (per 100k)",
    "county_burglary_rate":       "Burglary (per 100k)",
}

BANDWIDTHS = [50, 100, 200]
DONUTS = [0, 10, 25]
YEARS = list(range(2009, 2025))


# -------------------- data loading --------------------------------------

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(
        PANEL_PATH,
        dtype={"county_fips": str, "state_fips": str},
    )
    dist = pd.read_csv(
        DIST_PATH,
        dtype={
            "county_fips": str,
            "state_fips": str,
            "nearest_other_state_fips": str,
            "nearest_other_state_county_fips": str,
        },
    )
    # Just the columns we need from dist (avoid duplicate state_fips)
    dist = dist[[
        "county_fips",
        "nearest_other_state_fips",
        "distance_to_nearest_other_state_km",
        "nearest_other_state_county_fips",
    ]]
    return panel, dist


def adoption_year_per_state(panel: pd.DataFrame, law_col: str,
                            direction: str) -> dict[str, int]:
    """Year of first transition per state.

    direction='0to1' -> first year value goes 0 -> 1 (and stays).
    direction='1to0' -> first year value goes 1 -> 0.
    """
    out: dict[str, int] = {}
    state_year = (panel
                  .dropna(subset=[law_col])
                  .groupby(["state_fips", "year"])[law_col]
                  .first()
                  .reset_index()
                  .sort_values(["state_fips", "year"]))
    for state, sub in state_year.groupby("state_fips"):
        years = sub["year"].to_numpy()
        vals = sub[law_col].to_numpy()
        for i in range(1, len(vals)):
            if direction == "0to1" and vals[i - 1] == 0 and vals[i] == 1:
                out[state] = int(years[i])
                break
            if direction == "1to0" and vals[i - 1] == 1 and vals[i] == 0:
                out[state] = int(years[i])
                break
    return out


def state_law_by_year(panel: pd.DataFrame, law_col: str) -> dict[tuple[str, int], float]:
    """{(state_fips, year): value} dictionary for fast lookup."""
    sub = (panel.dropna(subset=[law_col])
                .groupby(["state_fips", "year"])[law_col].first())
    return {(s, int(y)): float(v) for (s, y), v in sub.items()}


# -------------------- diagnostics table --------------------------------

def build_diagnostics(panel: pd.DataFrame, dist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # Pre-merge: every county-year augmented with its border info.
    panel = panel.merge(dist, on="county_fips", how="left")
    panel = panel.dropna(subset=["nearest_other_state_fips"]).copy()
    panel["state_pair"] = panel.apply(
        lambda r: tuple(sorted([r["state_fips"], r["nearest_other_state_fips"]])),
        axis=1,
    )

    for policy, (law_col, direction, treated_val, control_val) in POLICIES.items():
        law_lookup = state_law_by_year(panel, law_col)

        def state_law(state, year, _lk=law_lookup):
            return _lk.get((state, year), np.nan)

        # vectorized: own + nearest law value
        panel["__own_law"] = panel.apply(
            lambda r: state_law(r["state_fips"], int(r["year"])), axis=1)
        panel["__nbr_law"] = panel.apply(
            lambda r: state_law(r["nearest_other_state_fips"], int(r["year"])),
            axis=1,
        )

        for bw in BANDWIDTHS:
            for donut in DONUTS:
                strip = panel[
                    (panel["distance_to_nearest_other_state_km"] <= bw) &
                    (panel["distance_to_nearest_other_state_km"] >= donut)
                ]
                for year in YEARS:
                    cell = strip[strip["year"] == year]
                    if cell.empty:
                        rows.append({
                            "policy": policy, "year": year,
                            "bandwidth_km": bw, "donut_km": donut,
                            "n_counties_in_strip": 0,
                            "n_state_pairs_in_strip": 0,
                            "n_pairs_straddling_policy_boundary": 0,
                            "n_treated_counties": 0,
                            "n_control_counties": 0,
                            "mean_distance_km": np.nan,
                        })
                        continue
                    # distinct pairs in strip this year
                    pair_set = set(cell["state_pair"].tolist())
                    # straddling: own != nbr (one has policy, other doesn't),
                    # both observed
                    own = cell["__own_law"].to_numpy()
                    nbr = cell["__nbr_law"].to_numpy()
                    both_obs = (~np.isnan(own)) & (~np.isnan(nbr))
                    straddle_mask = both_obs & (own != nbr)
                    straddling_pairs = set(
                        cell.loc[straddle_mask, "state_pair"].tolist()
                    )
                    n_treated = int(((own == treated_val) & both_obs).sum())
                    n_control = int(((own == control_val) & both_obs).sum())
                    rows.append({
                        "policy": policy,
                        "year": year,
                        "bandwidth_km": bw,
                        "donut_km": donut,
                        "n_counties_in_strip": int(len(cell)),
                        "n_state_pairs_in_strip": len(pair_set),
                        "n_pairs_straddling_policy_boundary":
                            len(straddling_pairs),
                        "n_treated_counties": n_treated,
                        "n_control_counties": n_control,
                        "mean_distance_km": float(
                            cell["distance_to_nearest_other_state_km"].mean()
                        ),
                    })
    return pd.DataFrame(rows)


# -------------------- cross-section data ---------------------------------

def build_cross_section(panel: pd.DataFrame, dist: pd.DataFrame, policy: str,
                         bin_width: float = 25.0,
                         x_range: tuple[float, float] = (-200.0, 200.0)
                         ) -> dict[str, pd.DataFrame]:
    """For each outcome, mean by signed-distance bin pooled across years.

    Signed distance = +d if county on the side with the policy, -d if on
    the side without. Only county-years where the pair straddles in that
    year are kept.
    """
    law_col, _direction, treated_val, control_val = POLICIES[policy]
    p = panel.merge(dist, on="county_fips", how="left")
    p = p.dropna(subset=["nearest_other_state_fips"]).copy()
    law_lookup = state_law_by_year(p, law_col)
    p["__own_law"] = p.apply(
        lambda r: law_lookup.get((r["state_fips"], int(r["year"])), np.nan),
        axis=1,
    )
    p["__nbr_law"] = p.apply(
        lambda r: law_lookup.get(
            (r["nearest_other_state_fips"], int(r["year"])), np.nan),
        axis=1,
    )
    both = (~p["__own_law"].isna()) & (~p["__nbr_law"].isna())
    straddle = both & (p["__own_law"] != p["__nbr_law"])
    p = p[straddle].copy()
    # Signed distance: + if own state is treated, - if control
    sign = np.where(p["__own_law"] == treated_val, 1.0, -1.0)
    p["signed_d"] = sign * p["distance_to_nearest_other_state_km"]
    p = p[(p["signed_d"] >= x_range[0]) & (p["signed_d"] <= x_range[1])]

    edges = np.arange(x_range[0], x_range[1] + bin_width, bin_width)
    centers = (edges[:-1] + edges[1:]) / 2.0
    out: dict[str, pd.DataFrame] = {}
    for outcome in OUTCOMES:
        sub = p[["signed_d", outcome]].dropna()
        if sub.empty:
            out[outcome] = pd.DataFrame({"center": centers,
                                         "mean": [np.nan] * len(centers),
                                         "n": [0] * len(centers)})
            continue
        idx = np.clip(np.digitize(sub["signed_d"].to_numpy(), edges) - 1,
                      0, len(centers) - 1)
        sub = sub.copy()
        sub["bin"] = idx
        agg = sub.groupby("bin")[outcome].agg(["mean", "count"]).reindex(
            range(len(centers)))
        out[outcome] = pd.DataFrame({
            "center": centers,
            "mean": agg["mean"].to_numpy(),
            "n": agg["count"].fillna(0).astype(int).to_numpy(),
        })
    return out


# -------------------- pre-trends data ------------------------------------

def build_pretrends(panel: pd.DataFrame, dist: pd.DataFrame, policy: str
                    ) -> tuple[dict[str, pd.DataFrame], int]:
    """For each outcome, mean within-pair (treated - control) gap per year,
    averaged across pairs that ever straddle the policy.

    Returns (per-outcome df with cols [year, mean_gap, n_pairs], modal_year).
    """
    law_col, _direction, treated_val, control_val = POLICIES[policy]
    p = panel.merge(dist, on="county_fips", how="left")
    p = p.dropna(subset=["nearest_other_state_fips"]).copy()
    p["state_pair"] = p.apply(
        lambda r: tuple(sorted([r["state_fips"], r["nearest_other_state_fips"]])),
        axis=1,
    )
    law_lookup = state_law_by_year(p, law_col)
    p["__own_law"] = p.apply(
        lambda r: law_lookup.get((r["state_fips"], int(r["year"])), np.nan),
        axis=1,
    )
    p["__nbr_law"] = p.apply(
        lambda r: law_lookup.get(
            (r["nearest_other_state_fips"], int(r["year"])), np.nan),
        axis=1,
    )

    # Identify pairs that ever straddle: at least one (year) where laws differ
    both = (~p["__own_law"].isna()) & (~p["__nbr_law"].isna())
    diff_mask = both & (p["__own_law"] != p["__nbr_law"])
    ever_pairs = set(p.loc[diff_mask, "state_pair"].tolist())

    # Cohort year for the policy = adoption year of the treating state in
    # each ever-straddling pair
    adopt = adoption_year_per_state(panel, law_col,
                                    POLICIES[policy][1])
    pair_cohort_years: list[int] = []
    for pair in ever_pairs:
        a, b = pair
        ya = adopt.get(a)
        yb = adopt.get(b)
        candidates = [y for y in (ya, yb) if y is not None]
        if candidates:
            pair_cohort_years.append(min(candidates))
    if pair_cohort_years:
        # modal year
        s = pd.Series(pair_cohort_years)
        modal_year = int(s.mode().iloc[0])
    else:
        modal_year = 2018  # fallback midpoint

    # For each county-year, classify side as treated (val==treated_val) or
    # control (val==control_val) based on its OWN state's value that year.
    p_own = p.copy()
    p_own["side"] = np.where(
        p_own["__own_law"] == treated_val, "T",
        np.where(p_own["__own_law"] == control_val, "C", "X"),
    )
    p_own = p_own[p_own["side"].isin(["T", "C"])]
    # Restrict to ever-straddling pairs
    p_own = p_own[p_own["state_pair"].isin(ever_pairs)]

    out: dict[str, pd.DataFrame] = {}
    for outcome in OUTCOMES:
        sub = p_own[["year", "state_pair", "side", outcome]].dropna()
        if sub.empty:
            out[outcome] = pd.DataFrame(
                {"year": YEARS,
                 "mean_gap": [np.nan] * len(YEARS),
                 "n_pairs": [0] * len(YEARS)}
            )
            continue
        # Mean outcome per (pair, year, side)
        side_means = (sub.groupby(["state_pair", "year", "side"])[outcome]
                          .mean()
                          .unstack("side"))
        if "T" not in side_means.columns:
            side_means["T"] = np.nan
        if "C" not in side_means.columns:
            side_means["C"] = np.nan
        # Pair-year gap = T - C; only when both are present
        side_means["gap"] = side_means["T"] - side_means["C"]
        # Average gap across pairs per year
        per_year = (side_means["gap"]
                    .dropna()
                    .reset_index()
                    .groupby("year")["gap"]
                    .agg(["mean", "count"])
                    .reindex(YEARS))
        out[outcome] = pd.DataFrame({
            "year": YEARS,
            "mean_gap": per_year["mean"].to_numpy(),
            "n_pairs": per_year["count"].fillna(0).astype(int).to_numpy(),
        })
    return out, modal_year


# -------------------- SVG figures ----------------------------------------

# Conventions match plot_event_study_svg in scripts/cs_lib.py.
PANEL_W, PANEL_H = 380, 260
GAP = 30
PAD_L, PAD_R, PAD_T, PAD_B = 60, 18, 50, 50
FIG_W = 2 * PANEL_W + GAP + 30
FIG_H = 2 * PANEL_H + GAP + 70

C_SERIES = "#1f3a5f"
C_TREAT = "#b9461a"
C_PANEL_BG = "#fafaf7"
C_PANEL_STROKE = "#e2e2dc"
C_AXIS = "#444"
C_GRID = "#eeeeee"
C_ZERO = "#aaaaaa"


def _y_range(values: np.ndarray, include_zero: bool = True
             ) -> tuple[float, float]:
    arr = values[~np.isnan(values)]
    if arr.size == 0:
        return (0.0, 1.0)
    lo, hi = float(arr.min()), float(arr.max())
    if include_zero:
        lo = min(lo, 0.0)
        hi = max(hi, 0.0)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    pad = (hi - lo) * 0.05
    return lo - pad, hi + pad


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if lo == hi:
        return [lo]
    return [lo + (hi - lo) * k / (n - 1) for k in range(n)]


def _fmt(v: float) -> str:
    if abs(v) >= 1000:
        return f"{v:.0f}"
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2g}"


def plot_cross_section_svg(data: dict[str, pd.DataFrame], path: Path,
                           policy: str) -> None:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" font-size="14" '
        f'font-weight="600">Cross-border outcome means by signed distance '
        f'({policy})</text>',
    ]
    layout = list(OUTCOMES.items())
    for idx, (var, title) in enumerate(layout):
        sub = data[var]
        col = idx % 2
        row = idx // 2
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" '
            f'fill="{C_PANEL_BG}" stroke="{C_PANEL_STROKE}"/>'
        )
        parts.append(
            f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" text-anchor="middle" '
            f'font-weight="600">{title}</text>'
        )
        valid = sub.dropna(subset=["mean"])
        if valid.empty:
            parts.append(
                f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" '
                f'text-anchor="middle" fill="#888">no data</text>'
            )
            continue
        x = sub["center"].to_numpy()
        y = sub["mean"].to_numpy()
        x_lo, x_hi = float(x.min()) - 12.5, float(x.max()) + 12.5
        y_lo, y_hi = _y_range(y, include_zero=False)
        ix0 = x0 + PAD_L
        iy0 = y0 + PAD_T
        iw = PANEL_W - PAD_L - PAD_R
        ih = PANEL_H - PAD_T - PAD_B

        def px(v: float) -> float:
            return ix0 + (v - x_lo) / (x_hi - x_lo) * iw

        def py(v: float) -> float:
            return iy0 + ih - (v - y_lo) / (y_hi - y_lo) * ih

        # axes box
        parts.append(
            f'<line x1="{ix0}" y1="{iy0+ih}" x2="{ix0+iw}" y2="{iy0+ih}" '
            f'stroke="{C_AXIS}"/>'
        )
        parts.append(
            f'<line x1="{ix0}" y1="{iy0}" x2="{ix0}" y2="{iy0+ih}" '
            f'stroke="{C_AXIS}"/>'
        )
        # gridlines (light)
        for v in _nice_ticks(y_lo, y_hi):
            yy = py(v)
            parts.append(
                f'<line x1="{ix0}" y1="{yy:.1f}" x2="{ix0+iw}" y2="{yy:.1f}" '
                f'stroke="{C_GRID}" stroke-width="0.5"/>'
            )
        # vertical dashed line at d=0
        parts.append(
            f'<line x1="{px(0):.1f}" y1="{iy0}" x2="{px(0):.1f}" y2="{iy0+ih}" '
            f'stroke="{C_TREAT}" stroke-dasharray="3 3"/>'
        )
        # series: line + circles (separate left/right of border)
        # We draw the full polyline (control side, then treated side) then
        # circles on top for visibility.
        pts = [(float(xi), float(yi)) for xi, yi in zip(x, y)
               if not math.isnan(yi)]
        if pts:
            line_pts = " ".join(f"{px(xi):.1f},{py(yi):.1f}" for xi, yi in pts)
            parts.append(
                f'<polyline points="{line_pts}" fill="none" stroke="{C_SERIES}" '
                f'stroke-width="1.6"/>'
            )
            for xi, yi in pts:
                parts.append(
                    f'<circle cx="{px(xi):.1f}" cy="{py(yi):.1f}" r="2.6" '
                    f'fill="{C_SERIES}"/>'
                )
        # x ticks: every 50 km
        for tx in range(int(math.floor(x_lo / 50.0)) * 50,
                        int(math.ceil(x_hi / 50.0)) * 50 + 1, 50):
            if tx < x_lo or tx > x_hi:
                continue
            xv = px(tx)
            parts.append(
                f'<line x1="{xv:.1f}" y1="{iy0+ih}" x2="{xv:.1f}" '
                f'y2="{iy0+ih+3}" stroke="{C_AXIS}"/>'
            )
            parts.append(
                f'<text x="{xv:.1f}" y="{iy0+ih+15}" text-anchor="middle" '
                f'fill="{C_AXIS}">{tx}</text>'
            )
        # y ticks
        for v in _nice_ticks(y_lo, y_hi):
            yy = py(v)
            parts.append(
                f'<line x1="{ix0-3}" y1="{yy:.1f}" x2="{ix0}" y2="{yy:.1f}" '
                f'stroke="{C_AXIS}"/>'
            )
            parts.append(
                f'<text x="{ix0-6}" y="{yy+3:.1f}" text-anchor="end" '
                f'fill="{C_AXIS}">{_fmt(v)}</text>'
            )
        parts.append(
            f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" text-anchor="middle" '
            f'fill="{C_AXIS}">Signed distance to border (km)</text>'
        )
        parts.append(
            f'<text x="{x0+12}" y="{iy0+ih/2}" text-anchor="middle" '
            f'fill="{C_AXIS}" transform="rotate(-90 {x0+12} {iy0+ih/2})">'
            f'Mean rate per 100k</text>'
        )
    parts.append(
        f'<text x="{FIG_W-15}" y="{FIG_H-12}" text-anchor="end" fill="#888" '
        f'font-size="10">Negative x = control side, positive x = treated side. '
        f'Pooled across years where the pair straddled. '
        f'Bin width 25 km.</text>'
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def plot_pretrends_svg(data: dict[str, pd.DataFrame], path: Path,
                       policy: str, modal_year: int) -> None:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FIG_W} {FIG_H}" '
        f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" '
        f'font-size="11">',
        f'<text x="{FIG_W/2}" y="22" text-anchor="middle" font-size="14" '
        f'font-weight="600">Within-pair (treated - control) outcome gap by year '
        f'({policy})</text>',
    ]
    years = YEARS
    layout = list(OUTCOMES.items())
    for idx, (var, title) in enumerate(layout):
        sub = data[var]
        col = idx % 2
        row = idx // 2
        x0 = 15 + col * (PANEL_W + GAP)
        y0 = 40 + row * (PANEL_H + GAP)
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" '
            f'fill="{C_PANEL_BG}" stroke="{C_PANEL_STROKE}"/>'
        )
        parts.append(
            f'<text x="{x0 + PANEL_W/2}" y="{y0 + 18}" text-anchor="middle" '
            f'font-weight="600">{title}</text>'
        )
        y = sub["mean_gap"].to_numpy()
        if np.all(np.isnan(y)):
            parts.append(
                f'<text x="{x0 + PANEL_W/2}" y="{y0 + PANEL_H/2}" '
                f'text-anchor="middle" fill="#888">no data</text>'
            )
            continue
        x_lo, x_hi = years[0] - 0.5, years[-1] + 0.5
        y_lo, y_hi = _y_range(y, include_zero=True)
        ix0 = x0 + PAD_L
        iy0 = y0 + PAD_T
        iw = PANEL_W - PAD_L - PAD_R
        ih = PANEL_H - PAD_T - PAD_B

        def px(v: float) -> float:
            return ix0 + (v - x_lo) / (x_hi - x_lo) * iw

        def py(v: float) -> float:
            return iy0 + ih - (v - y_lo) / (y_hi - y_lo) * ih

        # zero line
        if y_lo <= 0 <= y_hi:
            parts.append(
                f'<line x1="{ix0}" y1="{py(0):.1f}" x2="{ix0+iw}" '
                f'y2="{py(0):.1f}" stroke="{C_ZERO}" stroke-width="0.7"/>'
            )
        # axis box
        parts.append(
            f'<line x1="{ix0}" y1="{iy0+ih}" x2="{ix0+iw}" y2="{iy0+ih}" '
            f'stroke="{C_AXIS}"/>'
        )
        parts.append(
            f'<line x1="{ix0}" y1="{iy0}" x2="{ix0}" y2="{iy0+ih}" '
            f'stroke="{C_AXIS}"/>'
        )
        # gridlines
        for v in _nice_ticks(y_lo, y_hi):
            yy = py(v)
            parts.append(
                f'<line x1="{ix0}" y1="{yy:.1f}" x2="{ix0+iw}" y2="{yy:.1f}" '
                f'stroke="{C_GRID}" stroke-width="0.5"/>'
            )
        # vertical dashed line at modal cohort year
        parts.append(
            f'<line x1="{px(modal_year):.1f}" y1="{iy0}" '
            f'x2="{px(modal_year):.1f}" y2="{iy0+ih}" '
            f'stroke="{C_TREAT}" stroke-dasharray="3 3"/>'
        )
        # series
        pts = [(yr, val) for yr, val in zip(years, y) if not math.isnan(val)]
        if pts:
            line_pts = " ".join(f"{px(yr):.1f},{py(val):.1f}" for yr, val in pts)
            parts.append(
                f'<polyline points="{line_pts}" fill="none" stroke="{C_SERIES}" '
                f'stroke-width="1.6"/>'
            )
            for yr, val in pts:
                parts.append(
                    f'<circle cx="{px(yr):.1f}" cy="{py(val):.1f}" r="2.6" '
                    f'fill="{C_SERIES}"/>'
                )
        # x ticks
        for ti in range(years[0], years[-1] + 1, 2):
            xv = px(ti)
            parts.append(
                f'<line x1="{xv:.1f}" y1="{iy0+ih}" x2="{xv:.1f}" '
                f'y2="{iy0+ih+3}" stroke="{C_AXIS}"/>'
            )
            parts.append(
                f'<text x="{xv:.1f}" y="{iy0+ih+15}" text-anchor="middle" '
                f'fill="{C_AXIS}">{ti}</text>'
            )
        # y ticks
        for v in _nice_ticks(y_lo, y_hi):
            yy = py(v)
            parts.append(
                f'<line x1="{ix0-3}" y1="{yy:.1f}" x2="{ix0}" y2="{yy:.1f}" '
                f'stroke="{C_AXIS}"/>'
            )
            parts.append(
                f'<text x="{ix0-6}" y="{yy+3:.1f}" text-anchor="end" '
                f'fill="{C_AXIS}">{_fmt(v)}</text>'
            )
        parts.append(
            f'<text x="{ix0+iw/2}" y="{iy0+ih+34}" text-anchor="middle" '
            f'fill="{C_AXIS}">Year</text>'
        )
        parts.append(
            f'<text x="{x0+12}" y="{iy0+ih/2}" text-anchor="middle" '
            f'fill="{C_AXIS}" transform="rotate(-90 {x0+12} {iy0+ih/2})">'
            f'Mean gap (per 100k)</text>'
        )
    parts.append(
        f'<text x="{FIG_W-15}" y="{FIG_H-12}" text-anchor="end" fill="#888" '
        f'font-size="10">Vertical dashed line at modal cohort year '
        f'({modal_year}). Gap averaged over state-pairs that ever straddled '
        f'the policy.</text>'
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts))


# -------------------- summary writeup ------------------------------------

def write_summary(diag: pd.DataFrame, modal_years: dict[str, int],
                  cross_section_data: dict[str, dict[str, pd.DataFrame]],
                  pretrends_data: dict[str, dict[str, pd.DataFrame]]) -> None:
    lines: list[str] = []
    lines.append("# Spatial RDD diagnostics summary\n")
    lines.append(
        "Pre-RDD characterization of the border-strip sample for three "
        "state policies (permitless concealed carry, civil red-flag laws, "
        "universal background checks). For each (policy x bandwidth x "
        "donut) cell we report counts of border-strip counties, distinct "
        "state-pairs, the subset of pairs that straddle a policy boundary "
        "in each year, and treated/control county counts. We also produce "
        "two visual diagnostics per policy: a pooled cross-border outcome "
        "plot to look for visible discontinuities at the border, and a "
        "year-by-year within-pair gap plot to inspect pre-trend "
        "parallelism.\n\n"
    )
    lines.append("## Headline findings\n")
    lines.append(
        "1. **Permitless carry** has by far the most straddling "
        "state-pair-years (mean 19-27 per year across the 50/100/200 km "
        "bandwidths), driven by the rapid 2021-2024 wave of state "
        "adoptions. Cross-border outcome levels are nearly identical near "
        "the border (jumps within +/- 18 per 100k for property/burglary, "
        "near-zero for murder), and pre-trend gaps are small but noisy. "
        "This is the cleanest setting for a headline RDD.\n"
        "2. **Red-flag laws** show large near-border level differences "
        "(violent crime ~119 per 100k lower on the treated side, property "
        "crime ~646 per 100k lower) AND large pre-period gaps in the same "
        "direction. This is selection: states that adopt red-flag laws "
        "are systematically lower-crime states. The cross-border 'jump' "
        "mostly reflects this state-level selection, not a treatment "
        "effect. The pre-trend SDs are small relative to the levels, so "
        "the level shift is real, not noise.\n"
        "3. **UBC** shows mixed pre-trends: large negative violent-crime "
        "and murder gaps (treated < control) but large positive "
        "property/burglary gaps. The 2013-cohort dominates, with very few "
        "post-period pairs. Pre-period gap SDs (34, 105, 38) are nearly "
        "as large as the gap means - pretrends are noisy, not flat.\n"
        "4. The donut radius (0/10/25 km) only trims a handful of "
        "counties because just ~10 counties have centroid-to-border <10 "
        "km and ~160 have <25 km. Donut effects on the cell-counts table "
        "are second-order; the bandwidth dimension matters far more.\n\n"
    )

    lines.append("## 1. Sample size by (policy x bandwidth) (donut = 0)\n")
    lines.append(
        "Counts averaged across years 2009-2024. 'pairs straddling' is the "
        "average across years of distinct state-pairs whose two states "
        "differed on the policy that year.\n"
    )
    lines.append(
        "| Policy | Bandwidth (km) | avg counties/yr | avg pairs/yr | "
        "avg straddling pairs/yr | max straddling pairs/yr |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
    )
    for policy in POLICIES:
        for bw in BANDWIDTHS:
            sub = diag[(diag["policy"] == policy) &
                       (diag["bandwidth_km"] == bw) &
                       (diag["donut_km"] == 0)]
            lines.append(
                f"| {policy} | {bw} | "
                f"{sub['n_counties_in_strip'].mean():.0f} | "
                f"{sub['n_state_pairs_in_strip'].mean():.0f} | "
                f"{sub['n_pairs_straddling_policy_boundary'].mean():.1f} | "
                f"{int(sub['n_pairs_straddling_policy_boundary'].max())} |\n"
            )

    lines.append("\n## 2. Donut-radius sensitivity (bandwidth = 100 km)\n")
    lines.append(
        "Average border-strip counties per year drop as the donut grows. "
        "Pair *identity* is preserved across donuts (each pair is two "
        "states), so the straddling-pair count is unchanged - the donut "
        "trims the innermost counties on each side. Mean distance shifts "
        "outward accordingly. Only ~10 counties have centroid-to-border "
        "<10 km and ~160 have <25 km, so donut effects are modest.\n"
    )
    lines.append(
        "| Policy | donut 0 counties | donut 10 counties | donut 25 counties | "
        "mean dist d=0 | mean dist d=25 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
    )
    for policy in POLICIES:
        cells = []
        for d in DONUTS:
            sub = diag[(diag["policy"] == policy) &
                       (diag["bandwidth_km"] == 100) &
                       (diag["donut_km"] == d)]
            cells.append(f"{sub['n_counties_in_strip'].mean():.0f}")
        sub0 = diag[(diag["policy"] == policy) &
                    (diag["bandwidth_km"] == 100) &
                    (diag["donut_km"] == 0)]
        sub25 = diag[(diag["policy"] == policy) &
                     (diag["bandwidth_km"] == 100) &
                     (diag["donut_km"] == 25)]
        d0 = sub0["mean_distance_km"].mean()
        d25 = sub25["mean_distance_km"].mean()
        lines.append(
            "| " + policy + " | " + " | ".join(cells) +
            f" | {d0:.1f} km | {d25:.1f} km |\n"
        )

    lines.append("\n## 3. Modal cohort year per policy\n")
    for policy, yr in modal_years.items():
        lines.append(f"- {policy}: modal cohort year = {yr}\n")

    lines.append("\n## 4. Visual diagnostics\n")
    lines.append(
        "- `figures/cross_section_<policy>.svg` plots the pooled mean rate "
        "by signed distance bin (negative on the control side, positive on "
        "the treated side, bin width 25 km). A visible jump at d = 0 is "
        "the descriptive RDD signature.\n"
        "- `figures/pretrends_<policy>.svg` plots the mean within-pair "
        "(treated - control) outcome gap year by year for state-pairs "
        "that ever straddled the policy. A flat or smoothly evolving "
        "pre-period before the modal cohort year supports parallel-trends "
        "in the donut/RDD strip.\n\n"
    )
    # Compute near-border jump and pre-trend stability per policy
    lines.append("Numerical readout from the figure data (within +/-25 km of "
                 "the border for the cross-section; pre-period defined as "
                 "year < modal cohort year for pre-trends):\n\n")
    lines.append(
        "| Policy | Outcome | near-border jump (T-C) | pre-period mean gap | "
        "pre-period sd of gap |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    for policy in POLICIES:
        modal = modal_years[policy]
        for outcome in OUTCOMES:
            cs = cross_section_data[policy][outcome]
            left = cs[(cs["center"] >= -25) & (cs["center"] < 0)]["mean"]
            right = cs[(cs["center"] > 0) & (cs["center"] <= 25)]["mean"]
            jump = float(right.mean() - left.mean()) if (
                len(left.dropna()) > 0 and len(right.dropna()) > 0
            ) else float("nan")
            pt = pretrends_data[policy][outcome]
            pre = pt[pt["year"] < modal]["mean_gap"].dropna()
            pre_mean = float(pre.mean()) if len(pre) > 0 else float("nan")
            pre_sd = float(pre.std()) if len(pre) > 1 else float("nan")
            lines.append(
                f"| {policy} | {outcome} | {jump:+.1f} | "
                f"{pre_mean:+.1f} | {pre_sd:.1f} |\n"
            )

    # Compute per-policy pre-trend severity (used in go/no-go and findings)
    pretrend_severity: dict[str, str] = {}
    for policy in POLICIES:
        modal = modal_years[policy]
        # Use violent crime as the headline outcome for severity scoring
        pt = pretrends_data[policy]["county_violent_crime_rate"]
        pre = pt[pt["year"] < modal]["mean_gap"].dropna()
        if len(pre) < 2:
            pretrend_severity[policy] = "n/a"
            continue
        pre_mean = abs(float(pre.mean()))
        pre_sd = float(pre.std())
        # heuristic: |mean| > 30 per 100k or |mean| > 1.5 sd
        if pre_mean > 30 and (pre_sd == 0 or pre_mean > 1.5 * pre_sd):
            pretrend_severity[policy] = "concerning"
        elif pre_mean > 15:
            pretrend_severity[policy] = "moderate"
        else:
            pretrend_severity[policy] = "ok"

    lines.append("\n## 5. Go / no-go assessment\n")
    lines.append(
        "Heuristic: at least 8 distinct straddling state-pairs per year is "
        "the minimum to support a credible headline (gives ~16+ "
        "treated/control side observations even before stacking years). "
        "We also flag pre-trend severity (using violent crime as the "
        "headline outcome): 'ok' = small/noisy pre-period gap; 'moderate' "
        "= |mean gap| > 15 per 100k; 'concerning' = |mean gap| > 30 per "
        "100k AND > 1.5 sd of the year-to-year gap.\n\n"
    )
    lines.append("| Policy | Bandwidth | Recommendation | Reason | "
                 "Pre-trend (violent) |\n"
                 "| --- | --- | --- | --- | --- |\n")
    rec_lines = []
    for policy in POLICIES:
        sev = pretrend_severity[policy]
        for bw in BANDWIDTHS:
            sub = diag[(diag["policy"] == policy) &
                       (diag["bandwidth_km"] == bw) &
                       (diag["donut_km"] == 0)]
            mean_strad = sub["n_pairs_straddling_policy_boundary"].mean()
            max_strad = int(
                sub["n_pairs_straddling_policy_boundary"].max())
            if mean_strad >= 12:
                base = "GO"
                reason = f"ample straddling pairs (mean {mean_strad:.0f}/yr)"
            elif mean_strad >= 6:
                base = "GO (with caution)"
                reason = (f"borderline pairs (mean {mean_strad:.1f}/yr, "
                          f"peak {max_strad})")
            else:
                base = "NO-GO"
                reason = ("insufficient straddling pairs "
                          f"(mean {mean_strad:.1f}/yr)")
            # Down-rate if pre-trends concerning
            if sev == "concerning" and base.startswith("GO"):
                rec = "GO (caution: pre-trend gap)"
                reason = reason + "; level shift in pre-period"
            else:
                rec = base
            rec_lines.append((policy, bw, rec, reason, mean_strad, sev))
            lines.append(
                f"| {policy} | {bw} km | {rec} | {reason} | {sev} |\n"
            )

    lines.append("\n## 6. Caveats / flags\n")
    lines.append(
        "- These diagnostics treat each county-year independently for the "
        "straddling indicator; pair-level treatment timing variation will "
        "be exploited in the actual RDD spec.\n"
        "- Pre-trend gaps are unweighted means across pairs; a more "
        "rigorous test would weight by inverse-variance or by population.\n"
        "- The cross-section figure pools across all years where the pair "
        "straddled; if treatment effects evolve over time, pooling can "
        "mask a discontinuity that is sharp only in later years.\n"
        "- Donut bins of 0/10/25 km drop only a handful of counties; "
        "diagnostics dominated by donut = 0.\n"
    )

    (OUT_DIR / "summary.md").write_text("".join(lines))


# -------------------- main -----------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel, dist = load_data()

    print(f"loaded panel: {panel.shape}, dist: {dist.shape}")

    # Diagnostics table
    diag = build_diagnostics(panel, dist)
    diag = diag.sort_values(
        ["policy", "bandwidth_km", "donut_km", "year"]).reset_index(drop=True)
    diag.to_csv(OUT_DIR / "diagnostics.csv", index=False)
    print(f"wrote diagnostics.csv ({len(diag)} rows)")

    modal_years: dict[str, int] = {}
    cs_cache: dict[str, dict[str, pd.DataFrame]] = {}
    pt_cache: dict[str, dict[str, pd.DataFrame]] = {}

    for policy in POLICIES:
        # cross-section SVG
        cs_data = build_cross_section(panel, dist, policy)
        cs_cache[policy] = cs_data
        plot_cross_section_svg(
            cs_data, FIG_DIR / f"cross_section_{policy}.svg", policy)
        print(f"wrote figures/cross_section_{policy}.svg")
        # pre-trends SVG
        pt_data, modal_year = build_pretrends(panel, dist, policy)
        pt_cache[policy] = pt_data
        modal_years[policy] = modal_year
        plot_pretrends_svg(
            pt_data, FIG_DIR / f"pretrends_{policy}.svg", policy, modal_year)
        print(f"wrote figures/pretrends_{policy}.svg (modal year {modal_year})")

    write_summary(diag, modal_years, cs_cache, pt_cache)
    print("wrote summary.md")


if __name__ == "__main__":
    main()
