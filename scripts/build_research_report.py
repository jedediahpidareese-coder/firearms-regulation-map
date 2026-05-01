"""Compile a single self-contained research report HTML with everything
the user needs to read, print, and share.

The output is `outputs/research_report/index.html` -- one file, all
figures embedded as inline SVG, all styling inline. The user opens it
in any browser and uses File -> Print -> Save as PDF for a
publication-style PDF.

Sections:
  1. Executive summary (one printed page)
  2. Data and panel construction (summarised; full version is data_appendix.md)
  3. Methodology  (CS21 ATT(g,t), stacked DiD, entropy balancing, Roth-SA bounds, substitution test)
  4. Per-policy results (Permitless carry, Civil red-flag, UBC), each with:
       - cohort table
       - CS21 4-spec table (per outcome)
       - Stacked-DD 3-spec table (per outcome)
       - Embedded event-study SVGs
       - Roth-SA bounds table where computed
  5. Cross-estimator + cross-policy synthesis
  6. Limitations and caveats
  7. Appendix: code map, reproduction steps, file index
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "outputs" / "research_report"
OUTDIR.mkdir(parents=True, exist_ok=True)

# Base URL for documentation links inside the report. We use absolute
# GitHub URLs because the report is served from BOTH the local outputs/
# folder (where ../red_flag_cs/methodology.md works) and from
# docs/research/ on GitHub Pages (where the .md files don't exist
# alongside index.html). GitHub also renders .md files nicely in the
# browser, so the link goes to a styled view by default.
GH_BASE = "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main"


# ---------------------- helpers ----------------------------------------

def fmt(val, fmt_str):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return fmt_str.format(val)


def read_csv(path: Path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def embed_svg(path: Path, max_width: str = "100%") -> str:
    """Inline an SVG file, stripping its XML declaration if present."""
    if not path.exists():
        return f'<p class="missing">[figure missing: {path.name}]</p>'
    text = path.read_text(encoding="utf-8")
    if text.startswith("<?xml"):
        text = text[text.index("?>") + 2:]
    return f'<div class="figure" style="max-width:{max_width};">{text}</div>'


def sig_stars(z) -> str:
    """Return significance stars for a two-tailed z-statistic.
    *** p<0.01, ** p<0.05, * p<0.10. Empty string if not significant.
    """
    if pd.isna(z):
        return ""
    az = abs(z)
    if az >= 2.576:
        return '<span class="sig sig3">***</span>'
    if az >= 1.96:
        return '<span class="sig sig2">**</span>'
    if az >= 1.645:
        return '<span class="sig sig1">*</span>'
    return ""


# Baseline outcome means computed once at module init from the augmented
# state panel; used to express significant ATTs as a percentage of the
# pre-period baseline ("economic interpretation"). For state-joined-down
# county outcomes the state mean is the right denominator. For true
# county-level outcomes (county_*) we compute the population-weighted
# mean across counties from the county panel.
def _compute_baselines() -> dict[str, float]:
    bases: dict[str, float] = {}
    try:
        sp = pd.read_csv(ROOT / "data" / "processed" / "panel_core_augmented.csv")
        # Derive nonfirearm_suicide_rate the same way cs_lib.load_panel_core_augmented does.
        if ("total_suicide_rate" in sp.columns and "firearm_suicide_rate" in sp.columns
                and "nonfirearm_suicide_rate" not in sp.columns):
            sp["nonfirearm_suicide_rate"] = sp["total_suicide_rate"] - sp["firearm_suicide_rate"]
        for c in ("firearm_suicide_rate", "nonfirearm_suicide_rate",
                  "total_suicide_rate", "firearm_homicide_rate",
                  "homicide_rate", "motor_vehicle_theft_rate",
                  "state_firearm_suicide_rate", "state_total_suicide_rate",
                  "state_firearm_homicide_rate", "state_nonfirearm_suicide_rate"):
            if c in sp.columns:
                v = sp[c].dropna().mean()
                if not pd.isna(v):
                    bases[c] = float(v)
                    bases[f"state_{c}"] = float(v)
    except Exception:
        pass
    try:
        cp = pd.read_csv(
            ROOT / "data" / "processed" / "county_panel_2009_2024.csv",
            usecols=lambda c: c.startswith("county_") and c.endswith("_rate"),
        )
        for c in cp.columns:
            v = cp[c].dropna().mean()
            if not pd.isna(v):
                bases[c] = float(v)
    except Exception:
        pass
    return bases


_BASELINES: dict[str, float] = _compute_baselines()


def pct_of_baseline(beta, outcome: str) -> str:
    """Return a "(±X% of base)" annotation if we have a baseline mean."""
    if pd.isna(beta) or outcome not in _BASELINES:
        return ""
    base = _BASELINES[outcome]
    if base == 0 or pd.isna(base):
        return ""
    pct = 100.0 * beta / base
    return f' <span class="pct">({pct:+.1f}% of base)</span>'


def coef_cell(att, se, z, outcome: str | None = None):
    """One cell of a coef table — value + SE + significance stars +
    optional economic-percent annotation."""
    if pd.isna(att) or pd.isna(se):
        return "—"
    stars = sig_stars(z)
    pct = pct_of_baseline(att, outcome) if outcome else ""
    return f"<span class='att'>{att:+.3f}</span> {stars}{pct}<br><span class='se'>SE {se:.3f}, z {z:+.2f}</span>"


# ---------------------- per-policy table builders ----------------------

def cs21_table_html(policy_dir: Path) -> str:
    """4-spec table for CS21: rows = outcomes, columns = (control_rule, spec)."""
    df = read_csv(policy_dir / "overall_att.csv")
    if df.empty:
        return "<p>(no CS21 results)</p>"

    # columns to show (in order)
    spec_combos = [
        ("broad", "or", "Broad / OR"),
        ("broad", "ra", "Broad / RA"),
        ("strict", "or", "Strict / OR"),
        ("strict", "ra", "Strict / RA"),
    ]
    available_outcomes = list(df["outcome"].unique())
    # Order outcomes consistently
    outcome_order = [
        "firearm_suicide_rate", "nonfirearm_suicide_rate", "total_suicide_rate",
        "firearm_homicide_rate", "homicide_rate", "motor_vehicle_theft_rate",
    ]
    outcomes = [o for o in outcome_order if o in available_outcomes]
    # New 2026-05-01: each (outcome, spec, control_rule) cell now has up
    # to three rows (one per tier: minimal, headline, expanded). Default
    # the main 4-spec table to the HEADLINE tier; the tier multiverse is
    # shown in a separate sensitivity sub-table beneath.
    if "tier" in df.columns:
        # OR has tier="all"; RA has tier ∈ {minimal, headline, expanded}.
        df = df[((df["spec"] == "or") & (df["tier"] == "all")) |
                ((df["spec"] == "ra") & (df["tier"] == "headline"))]
    rows = []
    for o in outcomes:
        cells = [f'<td class="row-name">{o.replace("_", " ")}</td>']
        for cr, sp, _ in spec_combos:
            r = df[(df["outcome"] == o) & (df["control_rule"] == cr) & (df["spec"] == sp)]
            if r.empty:
                cells.append("<td>—</td>")
                continue
            row = r.iloc[0]
            att = row["att_overall_post"]; se = row["se_overall_post"]; z = row["z"]
            pre = row["z_pretrends"]
            stars = sig_stars(z)
            pct = pct_of_baseline(att, o)
            pre_clean = "✓" if abs(pre) < 1.96 else "✗"
            cells.append(
                f'<td class="num"><span class="att">{att:+.3f}</span> {stars}{pct}'
                f'<br><span class="se">SE {se:.3f}, z {z:+.2f}</span>'
                f'<br><span class="pre">pre-z {pre:+.2f} {pre_clean}</span></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    headers = "".join(f'<th class="num">{label}</th>' for _, _, label in spec_combos)
    return (
        '<table class="coef">'
        f'<thead><tr><th>Outcome</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '<p class="caption">'
        'Stars: <span class="sig sig1">*</span> p&lt;0.10, '
        '<span class="sig sig2">**</span> p&lt;0.05, '
        '<span class="sig sig3">***</span> p&lt;0.01 (two-tailed, state-clustered). '
        '"% of base" expresses the ATT as a percentage of the all-state mean of that outcome over the analysis window. '
        '✓ / ✗ on the third line indicates whether the pre-trend test '
        '(avg ATT for e ∈ [-5, -2]) does NOT / DOES reject zero. '
        'Outcomes are per 100,000 residents.'
        '</p>'
    )


def covariate_sensitivity_table_html(policy_dir: Path) -> str:
    """Three-tier (Minimal / Headline / Expanded) sensitivity sub-table
    showing how the broad/RA estimate moves under different literature-
    backed covariate sets, per Donohue-Aneja-Weber 2019 multiverse
    convention. Only RA spec; broad control rule (the headline cell).
    """
    df = read_csv(policy_dir / "overall_att.csv")
    if df.empty or "tier" not in df.columns:
        return ""
    sub = df[(df["spec"] == "ra") & (df["control_rule"] == "broad")
             & (df["tier"].isin(["minimal", "headline", "expanded"]))].copy()
    if sub.empty:
        return ""
    outcome_order = [
        "firearm_suicide_rate", "nonfirearm_suicide_rate", "total_suicide_rate",
        "firearm_homicide_rate", "homicide_rate", "motor_vehicle_theft_rate",
    ]
    outcomes = [o for o in outcome_order if o in sub["outcome"].unique()]
    rows = []
    for o in outcomes:
        cells = [f'<td class="row-name">{o.replace("_", " ")}</td>']
        for tier in ("minimal", "headline", "expanded"):
            r = sub[(sub["outcome"] == o) & (sub["tier"] == tier)]
            if r.empty:
                cells.append("<td>—</td>")
                continue
            row = r.iloc[0]
            att = row["att_overall_post"]; se = row["se_overall_post"]; z = row["z"]
            stars = sig_stars(z)
            pct = pct_of_baseline(att, o)
            cells.append(
                f'<td class="num"><span class="att">{att:+.3f}</span> {stars}{pct}'
                f'<br><span class="se">SE {se:.3f}, z {z:+.2f}</span></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    headers = '<th class="num">Minimal</th><th class="num">Headline</th><th class="num">Expanded</th>'
    return (
        '<details class="tier-block"><summary>Covariate sensitivity (multiverse: Minimal / Headline / Expanded covariate sets) — broad pool, RA spec</summary>'
        '<table class="coef">'
        f'<thead><tr><th>Outcome</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '<p class="caption">'
        'Each column uses a different literature-backed covariate set (see §3 methodology preamble for definitions). '
        'Stars: <span class="sig sig1">*</span> p&lt;0.10, <span class="sig sig2">**</span> p&lt;0.05, <span class="sig sig3">***</span> p&lt;0.01. '
        'A coefficient that flips sign or loses significance across tiers is sensitive to covariate choice — interpret with care, per Donohue-Aneja-Weber 2019.'
        '</p>'
        '</details>'
    )


def balance_table_html(name: str, defn: dict) -> str:
    """Per-policy "Table 1" balance table: for each headline-tier covariate,
    compute treated-vs-control means at each cohort's g-1 anchor year, plus
    Imbens-Rubin normalized differences. Flags |norm_diff| > 0.25 as
    Imbens-Rubin's threshold for "imbalance worth worrying about".
    """
    try:
        from cs_lib import (load_panel_core_augmented, derive_cohorts,
                            covariates_for, classify_outcome)
    except Exception:
        return ""
    coh_csv = read_csv(defn["cs_dir"] / "cohort_n.csv")
    if coh_csv.empty:
        return ""
    treatment_var = defn["treatment_var"]
    direction = "1to0" if "permitconcealed" in treatment_var else "0to1"
    if treatment_var == "nosyg":
        direction = "1to0"
    try:
        panel = load_panel_core_augmented()
        cohorts, never_treated, _ = derive_cohorts(panel, treatment_var, direction)
    except Exception:
        return ""
    if not cohorts:
        return ""
    # Use the lethal-violence headline covariate set as the canonical
    # balance-check basis (largest set; covers most modal lit choices).
    cov_list = covariates_for("homicide_rate", "headline")
    rows = []
    for c in cov_list:
        if c not in panel.columns:
            continue
        treated_vals = []
        control_vals = []
        for g in sorted(cohorts):
            base = g - 1
            tr_states = cohorts[g]
            co_states = sorted(never_treated)
            tr_sub = panel[(panel.state_abbr.isin(tr_states)) & (panel.year == base)]
            co_sub = panel[(panel.state_abbr.isin(co_states)) & (panel.year == base)]
            tv = tr_sub[c].dropna()
            cv = co_sub[c].dropna()
            treated_vals.extend(tv.tolist())
            control_vals.extend(cv.tolist())
        if not treated_vals or not control_vals:
            continue
        import numpy as _np
        tm = _np.mean(treated_vals); cm = _np.mean(control_vals)
        ts = _np.std(treated_vals, ddof=1) if len(treated_vals) > 1 else 0.0
        cs_ = _np.std(control_vals, ddof=1) if len(control_vals) > 1 else 0.0
        pooled = _np.sqrt((ts**2 + cs_**2) / 2.0) if (ts > 0 or cs_ > 0) else 1.0
        norm_diff = (tm - cm) / pooled if pooled > 0 else float("nan")
        flag = ("<span style='color:#b9461a;font-weight:600;'>⚠</span>"
                if abs(norm_diff) > 0.25 else "")
        rows.append(f"<tr><td>{c}</td>"
                    f"<td class='num'>{tm:.3f}</td>"
                    f"<td class='num'>{cm:.3f}</td>"
                    f"<td class='num'>{norm_diff:+.3f} {flag}</td></tr>")
    if not rows:
        return ""
    return f"""
<details class="tier-block"><summary>Covariate balance check (Table 1) — treated vs broad control pool at each cohort's g−1 baseline</summary>
<table class="coef">
  <thead><tr><th>Covariate</th><th class="num">Treated mean</th><th class="num">Control mean</th><th class="num">Normalized diff</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>
<p class="caption">
  Treated and control means pooled across cohorts at each cohort's g−1 anchor year.
  Normalized difference = (mean_T − mean_C) / sqrt((sd_T² + sd_C²)/2). Per Imbens &amp; Rubin (2015),
  |normalized diff| &gt; 0.25 (⚠) indicates covariate imbalance worth flagging — RA / EB
  reweighting is the standard remedy.
</p>
</details>
"""


def observation_window_html(name: str, defn: dict) -> str:
    """Per-policy box stating the observation period and pre/post window
    choices with literature citations. The DiD/RDD literature has converged
    on certain window conventions; we disclose ours and justify them."""
    short = defn.get("policy_short", name.lower())
    # Pull cohort years from cohort_n.csv to summarize the actual window.
    coh = read_csv(defn["cs_dir"] / "cohort_n.csv")
    cohort_years = sorted(coh["g_cohort"].astype(int).unique().tolist()) if not coh.empty else []
    cohort_str = (f"{cohort_years[0]}–{cohort_years[-1]}"
                  if len(cohort_years) >= 2 else
                  (str(cohort_years[0]) if cohort_years else "—"))
    return f"""
<div class="cov-box">
  <h3>Observation window and pre/post specification</h3>
  <p>
    <strong>Analysis window:</strong> 1999–2023 (state panel post-NICS;
    last year with v2 firearm-mortality data). Treated-cohort adoptions
    span {cohort_str}.
  </p>
  <p>
    <strong>Event window:</strong> [−5, +5] years around adoption
    (5 leads, 5 lags). This follows the modal modern DiD convention
    (Roth, Sant'Anna, Bilinski, Poe 2023, J Econometrics; the canonical
    Callaway–Sant'Anna 2021 framework defaults to symmetric leads/lags).
    The 5-year window is wide enough to detect dynamic treatment effects
    that build over time (Cheng-Hoekstra 2013 SYG; McClellan-Tekin 2017),
    but narrow enough that small-sample inference for the most recent
    cohorts remains feasible. Pre-trend test averages event-times [−5, −2]
    so the omitted year (−1) and the immediate post-period (+0, +1) do
    not contaminate the parallel-trends check (per Borusyak-Jaravel-Spiess
    2024 and the Roth-SA bounds methodology).
  </p>
  <p>
    <strong>Strict-pool window:</strong> control states must satisfy the
    policy's no-contamination rule for every year in [g−5, g+5] (the same
    window as the event study). This avoids "drifting" controls — states
    that are close to but not yet adopting the policy at g but adopt soon
    after, which would bias the comparison toward zero (Goodman-Bacon 2021,
    Sun-Abraham 2021).
  </p>
</div>
"""


def covariate_disclosure_box_html(name: str) -> str:
    """Show the literature-backed covariate sets used by this policy's
    Headline RA spec. Pulled from cs_lib.COVARIATES_BY_OUTCOME."""
    try:
        from cs_lib import COVARIATES_BY_OUTCOME
    except Exception:
        return ""
    fams = [("Lethal violence (homicide, firearm homicide, total homicide)",
             "lethal_violence"),
            ("Suicide (firearm, total, non-firearm)", "suicide"),
            ("Property / placebo (MV theft)", "property_placebo")]
    pieces = ['<div class="cov-box"><h3>Covariates used (literature-backed; see §3)</h3>']
    pieces.append('<p>Three tiers per outcome family — Minimal / Headline / Expanded — '
                  'shown in the covariate-sensitivity sub-table below.</p>')
    for label, key in fams:
        h = COVARIATES_BY_OUTCOME[key]["headline"]
        pieces.append(f'<p><strong>{label} — Headline:</strong> '
                      f'<code>{", ".join(h)}</code></p>')
    pieces.append('</div>')
    return "\n".join(pieces)


def stackdd_table_html(policy_dir: Path) -> str:
    df = read_csv(policy_dir / "att_post.csv")
    if df.empty:
        return "<p>(no stacked-DD results)</p>"
    # Tier-aware: unweighted uses tier="all"; ra/eb use tier="headline"
    if "tier" in df.columns:
        df = df[((df["spec"] == "unweighted") & (df["tier"] == "all")) |
                ((df["spec"].isin(["ra", "eb"])) & (df["tier"] == "headline"))]
    spec_combos = [
        ("unweighted", "Unweighted"),
        ("ra", "Regression-adjusted"),
        ("eb", "Entropy-balanced"),
    ]
    outcome_order = [
        "firearm_suicide_rate", "nonfirearm_suicide_rate", "total_suicide_rate",
        "firearm_homicide_rate", "homicide_rate", "motor_vehicle_theft_rate",
    ]
    available_outcomes = list(df["outcome"].unique())
    outcomes = [o for o in outcome_order if o in available_outcomes]
    rows = []
    for o in outcomes:
        cells = [f'<td class="row-name">{o.replace("_", " ")}</td>']
        for sp, _ in spec_combos:
            r = df[(df["outcome"] == o) & (df["spec"] == sp)]
            if r.empty:
                cells.append("<td>—</td>")
                continue
            row = r.iloc[0]
            att = row["att"]; se = row["se"]; z = row["z"]
            stars = sig_stars(z)
            pct = pct_of_baseline(att, o)
            cells.append(
                f'<td class="num"><span class="att">{att:+.3f}</span> {stars}{pct}'
                f'<br><span class="se">SE {se:.3f}, z {z:+.2f}</span></td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    headers = "".join(f'<th class="num">{label}</th>' for _, label in spec_combos)
    return (
        '<table class="coef">'
        f'<thead><tr><th>Outcome</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '<p class="caption">'
        'Stars: <span class="sig sig1">*</span> p&lt;0.10, '
        '<span class="sig sig2">**</span> p&lt;0.05, '
        '<span class="sig sig3">***</span> p&lt;0.01 (two-tailed, state-clustered). '
        '"% of base" expresses the ATT as a percentage of the all-state mean of that outcome. '
        'Outcomes per 100,000 residents.'
        '</p>'
    )


def cohort_table_html(policy_dir: Path) -> str:
    df = read_csv(policy_dir / "cohort_n.csv")
    if df.empty:
        return ""
    rows = "".join(
        f'<tr><td>{int(r["g_cohort"])}</td><td>{int(r["n_states"])}</td>'
        f'<td><code>{r["states"]}</code></td></tr>'
        for _, r in df.iterrows()
    )
    return (
        '<table class="cohort">'
        '<thead><tr><th>Cohort year</th><th>n states</th><th>States</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def bounds_summary_html(policy_name: str) -> str:
    """Roth-SA bounds at e = +1, both estimators, all specs."""
    summary = read_csv(ROOT / "outputs" / "roth_sa_bounds" / "summary_e1.csv")
    if summary.empty:
        return "<p>(bounds summary not computed)</p>"
    rows_html = []
    sub = summary[summary["policy"] == policy_name].sort_values(["estimator", "control_rule", "spec"])
    if sub.empty:
        return "<p>(no bounds for this policy)</p>"
    for _, r in sub.iterrows():
        row = (
            f'<tr>'
            f'<td>{r["estimator"]}</td>'
            f'<td>{r["control_rule"]} / {r["spec"]}</td>'
            f'<td class="num">{r["att_e1_original"]:+.3f}</td>'
            f'<td class="num">{r["ci_e1_M0"]}</td>'
            f'<td class="num">{r["att_e1_M1"]:+.3f}</td>'
            f'<td class="num">{r["ci_e1_M1"]}</td>'
            f'<td>{"<b>survives</b>" if not r["ci_M1_includes_zero"] else "fails"}</td>'
            f'</tr>'
        )
        rows_html.append(row)
    return (
        '<table class="bounds">'
        '<thead><tr>'
        '<th>Estimator</th><th>Spec</th>'
        '<th>ATT(+1)</th><th>95% CI (M=0)</th>'
        '<th>ATT(+1) trend-adj</th><th>95% CI (M=1)</th>'
        '<th>M=1 verdict</th></tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table>'
        '<p class="caption">Roth-Sant\'Anna sensitivity bounds at event time +1. M = post-trend deviation as a multiple of the linear extrapolation of the observed pre-trend. M=1 = "post-trend looks like more of the same"; M=2 = "post-trend could be twice the pre-trend magnitude".</p>'
    )


# ---------------------- per-policy section ------------------------------

POLICY_DEFINITIONS = {
    "Permitless carry": {
        "treatment_var": "permitconcealed",
        "direction": "1 → 0 (state stops requiring a permit to carry concealed)",
        "cs_dir": ROOT / "outputs" / "permitless_carry_cs",
        "stack_dir": ROOT / "outputs" / "permitless_carry_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/permitless_carry_cs/methodology.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "permitless_carry",
    },
    "Civil-petition red-flag (ERPO)": {
        "treatment_var": "gvro",
        "direction": "0 → 1 (state allows civilian petition for an extreme risk protection order)",
        "cs_dir": ROOT / "outputs" / "red_flag_cs",
        "stack_dir": ROOT / "outputs" / "red_flag_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/red_flag_cs/methodology.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "red_flag",
    },
    "Universal background checks (UBC)": {
        "treatment_var": "universal",
        "direction": "0 → 1 (state requires UBC at point of purchase for all firearms)",
        "cs_dir": ROOT / "outputs" / "ubc_cs",
        "stack_dir": ROOT / "outputs" / "ubc_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/ubc_cs/methodology.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "ubc",
    },
    # Track A additions (2026-05-01)
    "Stand-your-ground (SYG)": {
        "treatment_var": "nosyg",
        "direction": "1 → 0 (state adopts SYG / removes duty-to-retreat outside the home)",
        "cs_dir": ROOT / "outputs" / "stand_your_ground_cs",
        "stack_dir": ROOT / "outputs" / "stand_your_ground_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/stand_your_ground_audit/appendix_section_draft.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "stand_your_ground",
    },
    "Large-capacity magazine ban": {
        "treatment_var": "magazine",
        "direction": "0 → 1 (state prohibits magazines above 10 or 15 rounds)",
        "cs_dir": ROOT / "outputs" / "magazine_ban_cs",
        "stack_dir": ROOT / "outputs" / "magazine_ban_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/magazine_ban_audit/appendix_section_draft.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "magazine_ban",
    },
    "Minimum age 21 for handgun purchase": {
        "treatment_var": "age21handgunsale",
        "direction": "0 → 1 (state raises minimum handgun-purchase age above the federal 18 floor)",
        "cs_dir": ROOT / "outputs" / "age21_handgun_cs",
        "stack_dir": ROOT / "outputs" / "age21_handgun_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/age21_handgun_audit/appendix_section_draft.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "age21_handgun",
    },
    "Assault weapons ban": {
        "treatment_var": "assault",
        "direction": "0 → 1 (state prohibits long-gun assault weapons; HI-style pistols-only bans excluded per Tufts coding)",
        "cs_dir": ROOT / "outputs" / "assault_weapons_ban_cs",
        "stack_dir": ROOT / "outputs" / "assault_weapons_ban_stackdd",
        "cs_methodology_link": f"{GH_BASE}/outputs/assault_weapons_ban_audit/appendix_section_draft.md",
        "stack_methodology_link": "https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/outputs/stacked_dd_comparison.md",
        "policy_short": "assault_weapons_ban",
    },
}


def _sig_phrase(z) -> str:
    az = abs(z) if not pd.isna(z) else 0
    if az >= 2.576:
        return "p &lt; 0.01"
    if az >= 1.96:
        return "p &lt; 0.05"
    if az >= 1.645:
        return "p &lt; 0.10"
    return "not significant"


def interpretation_block(name: str, cs_dir: Path, stack_dir: Path) -> str:
    """Generate plain-language headline interpretation prose for the
    significant findings in this policy's broad/RA CS21 spec. We focus
    on broad/RA because that's the figure-headline spec; readers can
    cross-reference the full 4-spec table for the strict pool and OR
    variants. Each significant outcome gets one bullet describing
    direction, magnitude (per-100k + %-of-base), significance level,
    and whether the pre-trend test passes.
    """
    df = read_csv(cs_dir / "overall_att.csv")
    if df.empty:
        return ""
    sub = df[(df.get("control_rule") == "broad") & (df.get("spec") == "ra")].copy()
    if sub.empty:
        return ""
    # Sort by absolute z so the most decisive results lead.
    sub["abs_z"] = sub["z"].abs()
    sub = sub.sort_values("abs_z", ascending=False)
    bullets = []
    for _, r in sub.iterrows():
        z = r["z"]
        if pd.isna(z) or abs(z) < 1.645:
            continue  # not even marginally significant; skip
        outcome = r["outcome"]
        att = r["att_overall_post"]
        se = r["se_overall_post"]
        pre_z = r["z_pretrends"]
        direction_word = "rises" if att > 0 else "falls"
        outcome_pretty = outcome.replace("_", " ").replace("rate", "rate")
        # Economic %.
        base = _BASELINES.get(outcome)
        if base and base != 0 and not pd.isna(base):
            pct = 100.0 * att / base
            pct_phrase = f"≈ {pct:+.1f}% of the all-state mean of {base:.2f}/100k"
        else:
            pct_phrase = "(no baseline available)"
        # Pre-trend caveat.
        if pd.isna(pre_z):
            pre_phrase = "Pre-trend test not available."
        elif abs(pre_z) < 1.645:
            pre_phrase = f"Pre-trend test passes (z = {pre_z:+.2f})."
        elif abs(pre_z) < 1.96:
            pre_phrase = f"Pre-trend test marginal (z = {pre_z:+.2f}); read with mild caution."
        else:
            pre_phrase = (f"<strong>Pre-trend test rejects (z = {pre_z:+.2f})</strong> — "
                          f"the post-period coefficient may partly reflect "
                          f"pre-existing trend differences rather than the policy.")
        bullets.append(
            f"<li><strong>{outcome_pretty}</strong> {direction_word} by approximately "
            f"<strong>{abs(att):.2f} per 100,000 residents per year</strong> "
            f"({pct_phrase}; SE = {se:.3f}, z = {z:+.2f}, {_sig_phrase(z)}). "
            f"{pre_phrase}</li>"
        )
    if not bullets:
        return (
            '<div class="interpretation"><h3>Headline interpretation (broad / RA)</h3>'
            '<p><em>No outcome is statistically significant at the 10% level in the broad/RA spec '
            'for this policy. See the full 4-spec table below for results under the other specifications, '
            'where some outcomes do reach significance under tighter control pools or simpler estimators.</em></p>'
            '</div>'
        )
    return (
        '<div class="interpretation">'
        f'<h3>Headline interpretation ({name}, broad / RA)</h3>'
        '<p>Reading the broad-pool, regression-adjusted Callaway–Sant\'Anna spec '
        '(the same spec the figure beneath the CS21 table reports), the statistically '
        'significant outcomes are:</p>'
        f'<ul>{"".join(bullets)}</ul>'
        '<p class="caption">'
        '"% of base" expresses the coefficient as a fraction of the all-state mean of '
        'the outcome over the analysis window — useful for an economic-magnitude read. '
        'A pre-trend rejection means the treated and control groups were already on '
        'diverging paths before the policy took effect, which weakens the causal claim. '
        'See §3 for an explanation of the spec grid (broad/strict, OR/RA) and the full '
        '4-spec table below for results under the other specifications.'
        '</p>'
        '</div>'
    )


def policy_section_html(name: str, defn: dict, section_num: int) -> str:
    cs_dir = defn["cs_dir"]
    stack_dir = defn["stack_dir"]
    short = defn["policy_short"]

    # Pick a representative event-study figure (broad / RA for CS21,
    # entropy-balanced for stacked-DD).
    cs_fig = cs_dir / "figures" / "event_study_broad_ra_4panel.svg"
    stack_fig_eb = stack_dir / "figures" / "event_study_eb_4panel.svg"
    stack_fig_unwt = stack_dir / "figures" / "event_study_unweighted_4panel.svg"

    return f"""
    <section class="policy">
      <h2>{section_num}. {name}</h2>
      <p class="lead">
        <strong>Treatment:</strong> {defn['treatment_var']} ({defn['direction']}).<br>
        Detailed write-up: <a href="{defn['cs_methodology_link']}" target="_blank" rel="noopener">CS21 methodology</a>
        and <a href="{defn['stack_methodology_link']}" target="_blank" rel="noopener">stacked-DiD comparison</a>.
      </p>

      {interpretation_block(name, cs_dir, stack_dir)}

      <h3>Treatment cohorts</h3>
      {cohort_table_html(cs_dir)}

      {observation_window_html(name, defn)}

      {covariate_disclosure_box_html(name)}

      {balance_table_html(name, defn)}

      <h3>Callaway-Sant'Anna ATT(g, t) — overall post-treatment</h3>
      {cs21_table_html(cs_dir)}
      {covariate_sensitivity_table_html(cs_dir)}

      <h3>Stacked DiD (Cengiz et al. 2019) — overall post-treatment</h3>
      {stackdd_table_html(stack_dir)}

      <h3>CS21 event study (broad / RA spec)</h3>
      {embed_svg(cs_fig)}

      <h3>Stacked-DiD event study (unweighted spec)</h3>
      {embed_svg(stack_fig_unwt)}

      <h3>Stacked-DiD event study (entropy-balanced spec)</h3>
      {embed_svg(stack_fig_eb)}

      <h3>Roth-Sant'Anna pre-trend bounds — firearm suicide, e = +1</h3>
      {bounds_summary_html(short)}
    </section>
    """


def rdd_section_html(section_num: int) -> str:
    """Cross-policy spatial RDD section (Track B). Each of the 3 RDD'd
    policies (permitless carry, red flag, UBC) gets a small headline
    table; methodology lives at outputs/border_rdd/methodology.md."""
    pieces = [f'<section id="rdd"><h2>{section_num}. Spatial regression discontinuity on county borders</h2>']
    pieces.append("""
    <p class="lead">
      Border-county pair design adapted from Dube, Lester &amp; Reich (2010, RESTAT)
      to firearm policy. County FE + state-pair × year FE; iterative within-FE
      Frisch-Waugh-Lovell. Identifying variation comes from differential outcomes
      between adjacent counties on opposite sides of a state border. Bandwidth =
      100 km (centroid distance to nearest other-state population centroid; geometry
      layer documented in §2.12 of <a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/data_appendix.md">data_appendix.md</a>).
      Per-policy estimator detail and the 10-spec robustness battery: see
      <a href="{GH_BASE}/outputs/border_rdd/methodology.md">outputs/border_rdd/methodology.md</a>.
    </p>
    <p class="lead">
      Outcomes are stratified into <strong>primary</strong> (true county-level
      Kaplan UCR rates: violent crime, murder, property crime, burglary, motor
      vehicle theft) and <strong>secondary</strong> (state-joined-down mortality —
      no within-state variation by construction; reported only as a sanity check
      against the existing CS21 results restricted to the border subsample).
    </p>
    """)
    for policy_short, policy_label in [
        ("permitless_carry", "Permitless carry"),
        ("red_flag", "Civil-petition red-flag (ERPO)"),
        ("ubc", "Universal background checks"),
        ("stand_your_ground", "Stand-your-ground (SYG)"),
        ("magazine_ban", "Large-capacity magazine ban"),
        ("age21_handgun", "Minimum age 21 for handgun purchase"),
        ("assault_weapons_ban", "Assault weapons ban"),
    ]:
        headline = read_csv(ROOT / "outputs" / f"{policy_short}_rdd" / "headline.csv")
        if headline.empty:
            continue
        rows = []
        for _, r in headline.iterrows():
            sig = "*" if abs(r.get("z") or 0) > 1.96 else ""
            stratum = r.get("outcome_stratum", "")
            rows.append(
                f"<tr><td>{r.get('outcome','')}</td>"
                f"<td>{stratum}</td>"
                f"<td>{coef_cell(r['beta'], r['se'], r['z'], r.get('outcome'))}</td>"
                f"<td>{int(r['n'])}</td>"
                f"<td>{int(r.get('n_pairs', 0))}</td></tr>"
            )
        pieces.append(f"""
        <h3>{policy_label} — RDD headline (B = 100 km, FE = pair × year, cluster = state)</h3>
        <table>
          <thead><tr><th>Outcome</th><th>Stratum</th><th>β (per 100k) [SE, z]</th><th>n</th><th>state pairs</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        """)
        es_fig = ROOT / "outputs" / f"{policy_short}_rdd" / "figures" / "event_study_primary.svg"
        pieces.append(f"<h4>Event study (primary outcomes only)</h4>{embed_svg(es_fig)}")
    pieces.append("</section>")
    return "\n".join(pieces)


def county_section_html(section_num: int) -> str:
    """Cross-policy county-level CS21 section (Track C). Each of the 3
    policies gets a headline table from its outputs/{policy}_cs_county/
    overall_att.csv. Methodology lives in scripts/lib_cs_county.py."""
    pieces = [f'<section id="county-cs21"><h2>{section_num}. County-level Callaway-Sant&#8217;Anna ATT(g, t)</h2>']
    pieces.append("""
    <p class="lead">
      A county-grain adaptation of the existing state-level Callaway-Sant'Anna
      pipeline. Unit of observation is <code>county_fips</code>; cohorts are
      constructed by state (since treatment is state-level law adoption); the
      cluster-bootstrap clusters at <em>state</em> because counties within a
      state share the policy assignment. Many counties per cohort = much tighter
      SEs than the state-level pipeline. Outcomes are the true county-level
      Kaplan UCR rates plus the state-joined-down mortality variables (the
      latter, again, identified at state grain — included only for cross-method
      consistency). Estimator: <a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/scripts/lib_cs_county.py"><code>scripts/lib_cs_county.py</code></a>.
    </p>
    """)
    for policy_short, policy_label in [
        ("permitless_carry", "Permitless carry"),
        ("red_flag", "Civil-petition red-flag (ERPO)"),
        ("ubc", "Universal background checks"),
    ]:
        df = read_csv(ROOT / "outputs" / f"{policy_short}_cs_county" / "overall_att.csv")
        if df.empty:
            continue
        # Show RA broad spec (the project's headline convention)
        sub = df[(df.get("spec") == "ra") & (df.get("control_rule") == "broad")]
        rows = []
        for _, r in sub.iterrows():
            rows.append(
                f"<tr><td>{r['outcome']}</td>"
                f"<td>{coef_cell(r['att_overall_post'], r['se_overall_post'], r['z'], r.get('outcome'))}</td>"
                f"<td>{r['att_pretrends_avg']:+.3f} (z={r['z_pretrends']:+.2f})</td>"
                f"<td>{int(r['n_post_cells'])}</td></tr>"
            )
        pieces.append(f"""
        <h3>{policy_label} — county CS21 headline (RA / broad)</h3>
        <table>
          <thead><tr><th>Outcome</th><th>ATT post (per 100k) [SE, z]</th><th>Pre-trend avg (z)</th><th>n post cells</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        """)
    pieces.append("""
    <p>
      Cross-method check: the county-grain CS21 should produce point estimates
      that broadly agree with the state-level CS21 once weighted to comparable
      population. Where signs disagree, that is informative — it suggests the
      effect is concentrated in particular counties rather than uniform across
      the adopting state.
    </p>
    </section>""")
    return "\n".join(pieces)


# ---------------------- top-level page ----------------------------------

def build_html() -> str:
    style = """
    <style>
      :root {
        --primary: #1f3a5f;
        --accent: #b9461a;
        --muted: #6b7280;
        --border: #d4d4cc;
        --light: #f7f6f1;
      }
      * { box-sizing: border-box; }
      body {
        max-width: 880px;
        margin: 0 auto;
        padding: 32px 38px 100px;
        font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
        line-height: 1.55;
        color: #111;
      }
      h1 { font-size: 28px; margin: 0 0 4px; color: var(--primary); }
      h2 { font-size: 22px; margin: 36px 0 8px; padding-bottom: 4px; border-bottom: 2px solid var(--primary); color: var(--primary); }
      h3 { font-size: 16px; margin: 20px 0 6px; color: var(--accent); }
      h4 { font-size: 14px; margin: 14px 0 4px; }
      p, li { font-size: 14px; }
      .meta { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
      .lead { font-size: 14px; background: var(--light); padding: 10px 14px; border-left: 3px solid var(--primary); margin: 8px 0 18px; }
      .summary-box { border: 1px solid var(--border); padding: 12px 16px 4px; background: #fcfcf8; margin: 14px 0 24px; }
      .summary-box h3 { margin-top: 0; color: var(--primary); }
      table { border-collapse: collapse; width: 100%; margin: 8px 0 6px; font-size: 12.5px; font-family: -apple-system, "Segoe UI", sans-serif; }
      th, td { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
      th { background: #efeee5; font-weight: 600; }
      td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
      td.row-name { font-weight: 600; }
      td .att { font-weight: 600; color: var(--primary); }
      td .se { color: var(--muted); font-size: 11px; }
      td .pre { color: var(--muted); font-size: 11px; display: block; }
      .sig { font-weight: 700; }
      .sig1 { color: #999; }
      .sig2 { color: #b9461a; }
      .sig3 { color: #8c1d04; }
      .pct { color: var(--muted); font-size: 11px; font-style: italic; }
      .cov-box {
        background: #f4f6f9;
        border-left: 3px solid #1f3a5f;
        padding: 12px 18px;
        margin: 14px 0 18px;
        font-size: 13px;
      }
      .cov-box h3 { margin-top: 0; font-size: 14px; color: #1f3a5f; }
      .cov-box code { font-size: 11px; color: #444; }
      details.tier-block {
        margin: 12px 0 18px;
        padding: 10px 14px;
        background: #fdfdfb;
        border: 1px solid var(--border);
        border-radius: 4px;
      }
      details.tier-block summary {
        cursor: pointer;
        font-weight: 600;
        color: #1f3a5f;
        margin-bottom: 8px;
      }
      details.tier-block[open] summary { margin-bottom: 12px; }
      .interpretation {
        background: #fcfaf2;
        border-left: 4px solid #b9461a;
        padding: 14px 20px;
        margin: 18px 0 24px;
        border-radius: 4px;
      }
      .interpretation h3 { margin-top: 0; color: #b9461a; }
      .interpretation ul { margin: 8px 0 8px 0; }
      .interpretation li { margin: 8px 0; line-height: 1.55; }
      .interpretation .caption { color: var(--muted); font-size: 12px; margin-bottom: 0; }
      .caption { font-size: 11.5px; color: var(--muted); margin: 2px 0 18px; }
      .figure { margin: 8px 0 14px; }
      .figure svg { width: 100%; height: auto; }
      .missing { color: var(--accent); font-style: italic; font-size: 12px; }
      code { background: #f3f3eb; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
      table.cohort, table.bounds { font-size: 12px; }
      ul.findings { padding-left: 20px; margin: 6px 0 18px; }
      ul.findings li { margin-bottom: 6px; }
      .badge { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; margin-left: 4px; vertical-align: middle; }
      .badge-robust { background: #dcfce7; color: #14532d; }
      .badge-fragile { background: #fef3c7; color: #92400e; }
      .badge-unidentified { background: #fee2e2; color: #991b1b; }
      a { color: var(--primary); text-decoration: underline; text-decoration-thickness: 1px; }
      .toc { font-size: 13px; background: var(--light); padding: 14px 18px; border-radius: 6px; }
      .toc h3 { color: var(--primary); margin: 0 0 6px; }
      .toc ol { padding-left: 18px; margin: 0; }
      .toc li { margin: 2px 0; }
      @media print {
        body { max-width: none; padding: 0.5in 0.6in 0.6in; font-size: 11.5pt; }
        h1 { font-size: 22pt; }
        h2 { font-size: 14pt; page-break-before: always; padding-top: 0; }
        h2:first-of-type { page-break-before: auto; }
        h3 { font-size: 11pt; }
        .figure svg { max-height: 4.2in; }
        .lead, .summary-box { page-break-inside: avoid; }
        table { page-break-inside: avoid; }
        .toc { page-break-after: always; }
      }
    </style>
    """

    perm_section = policy_section_html("Permitless carry", POLICY_DEFINITIONS["Permitless carry"], 4)
    rf_section   = policy_section_html("Civil-petition red-flag (ERPO)", POLICY_DEFINITIONS["Civil-petition red-flag (ERPO)"], 5)
    ubc_section  = policy_section_html("Universal background checks (UBC)", POLICY_DEFINITIONS["Universal background checks (UBC)"], 6)
    syg_section  = policy_section_html("Stand-your-ground (SYG)", POLICY_DEFINITIONS["Stand-your-ground (SYG)"], 7)
    mag_section  = policy_section_html("Large-capacity magazine ban", POLICY_DEFINITIONS["Large-capacity magazine ban"], 8)
    age_section  = policy_section_html("Minimum age 21 for handgun purchase", POLICY_DEFINITIONS["Minimum age 21 for handgun purchase"], 9)
    awb_section  = policy_section_html("Assault weapons ban", POLICY_DEFINITIONS["Assault weapons ban"], 10)
    rdd_block    = rdd_section_html(11)
    county_block = county_section_html(12)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>State firearm policy effects: research report</title>
{style}
</head>
<body>

<h1>State firearm policy effects: a multi-estimator research report</h1>
<p class="meta">
  Generated {pd.Timestamp.now().strftime('%Y-%m-%d')} from
  <code>scripts/build_research_report.py</code>. All numbers reproducible from the
  scripts and CSV outputs in this repository.
  Companion data inventory: <a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/data_appendix.md"><code>data_appendix.md</code></a>.
  Source code: <a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map">github.com/jedediahpidareese-coder/firearms-regulation-map</a>.
  Public map: <a href="https://jedediahpidareese-coder.github.io/firearms-regulation-map/">jedediahpidareese-coder.github.io/firearms-regulation-map</a>.
</p>

<div class="toc">
  <h3>Contents</h3>
  <ol>
    <li><a href="#executive-summary">Executive summary</a></li>
    <li><a href="#data">Data and panel construction</a></li>
    <li><a href="#methodology">Methodology</a></li>
    <li><a href="#permitless-carry">Permitless carry</a></li>
    <li><a href="#red-flag">Civil-petition red-flag (ERPO)</a></li>
    <li><a href="#ubc">Universal background checks</a></li>
    <li><a href="#stand-your-ground">Stand-your-ground (SYG)</a></li>
    <li><a href="#magazine-ban">Large-capacity magazine ban</a></li>
    <li><a href="#age21-handgun">Minimum age 21 for handgun purchase</a></li>
    <li><a href="#assault-weapons-ban">Assault weapons ban</a></li>
    <li><a href="#rdd">Spatial regression discontinuity on county borders</a></li>
    <li><a href="#county-cs21">County-level Callaway-Sant'Anna ATT(g, t)</a></li>
    <li><a href="#synthesis">Cross-policy synthesis</a></li>
    <li><a href="#limitations">Limitations and caveats</a></li>
    <li><a href="#appendix">Appendix: code map and reproduction</a></li>
  </ol>
</div>

<section id="executive-summary">
<h2>1. Executive summary</h2>

<p>
We estimate the causal effect of three U.S. state firearm policies — permitless concealed carry,
civil-petition extreme risk protection orders ("red-flag laws"), and universal background checks
(UBC) — on six outcomes: firearm suicide rate, non-firearm suicide rate, total suicide rate,
firearm homicide rate, total homicide rate, and motor vehicle theft rate (placebo). Each policy is
estimated by two modern staggered-adoption DiD estimators — Callaway-Sant'Anna (2021) ATT(g, t) and
Cengiz et al. (2019) stacked DiD — under multiple specifications including regression adjustment
and Hainmueller (2012) entropy balancing. We also report Roth-Sant'Anna (2019) honest pre-trend
sensitivity bounds for the firearm-suicide outcome.
</p>

<div class="summary-box">
  <h3>Two findings most defensible for publication</h3>
  <ul class="findings">
    <li>
      <strong>Permitless concealed carry adoption is associated with about +0.6 additional total
      suicides per 100,000 residents per year</strong> in the average treated state.
      <span class="badge badge-robust">robust</span>
      <br>
      <em>CS21 broad/RA: +0.64; stacked-DiD: +0.51 to +0.69. Substitution test passes
      (firearm-suicide rises, non-firearm essentially flat, total rises by approximately the
      firearm amount). Roth-Sant'Anna bounds: CS21 RA specs survive M = 1 trend adjustment.</em>
    </li>
    <li>
      <strong>Civil-petition red-flag laws are associated with reduced firearm homicide</strong>:
      about −0.14 per 100,000 in the cleanest CS21 specification, and −0.50 to −0.73 in the
      stacked-DiD specifications.
      <span class="badge badge-robust">direction robust</span>
      <br>
      <em>Pre-trend test does not reject in CS21 broad/RA (z = −0.58). Stacked-DiD agrees on
      direction; magnitude is uncertain (the EB spec produces an extreme estimate due to limited
      treated/control covariate overlap).</em>
    </li>
  </ul>
</div>

<div class="summary-box">
  <h3>Three findings clearly NOT identified in this design</h3>
  <ul class="findings">
    <li>
      <strong>Civil red-flag → firearm suicide.</strong> Apparent reductions in every spec, but
      pre-trends reject at z ≈ +4–5 across all CS21 and stacked-DD specs.
      Roth-Sant'Anna bounds at M = 1 fail in every specification; OR specs flip sign positive at
      M = 2. Most plausible explanation: Ashenfelter's dip — adopting states had rising
      firearm-suicide rates before adoption, which is part of the political story that
      motivated the law.
      <span class="badge badge-unidentified">unidentified</span>
    </li>
    <li>
      <strong>UBC → firearm suicide.</strong> Significant in CS21 RA (−0.48) but essentially zero
      at e = +1 in stacked DiD across all three weighting specs. Estimator-dependent and bound-
      fragile.
      <span class="badge badge-fragile">fragile</span>
    </li>
    <li>
      <strong>Permitless carry → firearm or total homicide.</strong> Direction is mixed across
      specs and the macroeconomic covariates (population scale, unemployment, real income) used
      in the RA spec do not absorb the property-crime trend gap that breaks the placebo.
      <span class="badge badge-unidentified">unidentified</span>
    </li>
  </ul>
</div>

<p>
The motor vehicle theft placebo is significant in several specs across all three policies, which
is a persistent identification challenge. For permitless carry the placebo failure is severe (and
shows up in pre-trends too); for red-flag and UBC the stacked-DiD placebo CIs include zero, which
is a meaningfully better identification position than CS21 alone suggested.
</p>
</section>


<section id="data">
<h2>2. Data and panel construction</h2>
<p>
Estimates use a balanced state-year panel covering 50 U.S. states (DC excluded throughout) from
1979 through 2024 (suicide / homicide outcomes from a long-run firearm suicide / homicide v2
file end in 2023). The augmented variant of the panel adds granular FBI / OpenCrime crime
components (homicide, robbery, rape, aggravated assault, burglary, larceny, motor vehicle theft),
firearm and total suicide and homicide counts, the firearm-suicide-share ownership proxy, and the
RAND TL-354 household firearm ownership rate (1980–2016).
</p>
<p>
The full prose-language data documentation lives in
<a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/data_appendix.md"><code>data_appendix.md</code></a>. Every variable, source, and
manipulation is documented there in plain English. The same panel powers the public choropleth
map at
<a href="https://jedediahpidareese-coder.github.io/firearms-regulation-map/">jedediahpidareese-coder.github.io/firearms-regulation-map</a>.
</p>
<h3>Sources used in the research analyses</h3>
<table>
  <thead><tr><th>Variable family</th><th>Source</th><th>Window</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td>Firearm laws (treatments)</td><td>Tufts CTSI State Firearm Laws Database (Siegel et al.)</td><td>1976–2024</td><td>72 binary indicators across 11 categories.</td></tr>
    <tr><td>Firearm suicides / homicides (counts and per-100k rates)</td><td>Firearm-suicide / homicide v2 dataset (Kalesan-style)</td><td>1949–2023</td><td>50 states; DC excluded; non-firearm suicide derived as total − firearm.</td></tr>
    <tr><td>Total homicide rate, motor vehicle theft rate</td><td>FBI UCR / OpenCrime extraction</td><td>1979–2024</td><td>Same NC↔ND 2022 reassignment as the website build.</td></tr>
    <tr><td>Macro controls</td><td>BLS LAUS unemployment, BEA per-capita personal income, Census state population</td><td>1979–2024</td><td>Real income deflated to 2024 USD via CPI-U.</td></tr>
  </tbody>
</table>
<p class="caption">All inputs are public. Reproduce the panel via <code>scripts/build_firearms_panel.py</code> and <code>scripts/augment_panels.py</code>.</p>
</section>


<section id="methodology">
<h2>3. Methodology</h2>

<div class="summary-box">
<h3>How to read the result tables (broad/strict, OR/RA, stars)</h3>
<p>
  Every per-policy section has a table with up to 4 columns for CS21 and 3 for stacked-DiD.
  The columns vary along two axes: which control states the comparison uses
  (<strong>broad</strong> vs <strong>strict</strong>) and which estimator
  spec (<strong>OR</strong> vs <strong>RA</strong>; for stacked-DiD additionally <strong>EB</strong>).
</p>
<ul>
  <li>
    <strong>Broad control pool</strong> = every state that <em>never</em> adopted the policy in our
    1979–2024 window. This is the Callaway–Sant'Anna (2021) default — the largest available
    counterfactual sample.
  </li>
  <li>
    <strong>Strict control pool</strong> = the broad pool further restricted by a policy-specific
    "no contamination" rule. For permitless carry, the strict rule requires the control state to
    have <em>both</em> a concealed-permit requirement <em>and</em> may-issue discretion throughout
    each cohort's [g−5, g+5] window — so the control hasn't drifted toward the treatment. For
    civil-petition red-flag, strict additionally excludes states with the older
    law-enforcement-only ERPO. The strict rule trades sample size for cleaner
    identification (fewer "almost-adopter" controls).
  </li>
  <li>
    <strong>OR (outcome regression / unconditional DiD):</strong> the basic two-way DiD; just
    average treated minus average control. No covariates.
  </li>
  <li>
    <strong>RA (regression-adjusted, Sant'Anna &amp; Zhao 2020):</strong> projects the treated
    states' baseline covariates onto the control states' outcome model and adjusts the comparison.
    Doubly robust under modest covariate overlap. RA is preferred to OR whenever the treated and
    control states differ on observables (which they almost always do).
  </li>
  <li>
    <strong>EB (entropy balancing, Hainmueller 2012):</strong> stacked-DiD only. Per-cohort
    reweighting of controls so their baseline covariate moments exactly match the treated
    unit's. The most aggressive reweighting; useful as an outer bound on how much the headline
    moves under aggressive covariate adjustment.
  </li>
</ul>
<p>
  <strong>Project recommended default:</strong> <em>strict / RA</em> when the strict pool is large
  enough (≥ 15 states), <em>broad / RA</em> otherwise. RA over OR almost always; broad over strict
  only if strict drops too many cohorts. The headline figure shown after each table is the
  broad/RA spec for CS21 and the unweighted spec for stacked-DiD; we picked these for visual
  consistency across policies, not because they're more identified than the others. Read the
  full 4-spec table.
</p>
<p>
  <strong>Significance stars:</strong> <span class="sig sig1">*</span> p&lt;0.10,
  <span class="sig sig2">**</span> p&lt;0.05, <span class="sig sig3">***</span> p&lt;0.01,
  two-tailed, state-clustered. <strong>"% of base"</strong> next to each significant
  estimate expresses the ATT as a percentage of the all-state mean of that outcome over the
  analysis window — so a coefficient of −0.14 firearm homicide on a baseline mean of 4.5
  per 100,000 reads as roughly −3% of base, which is a more interpretable size than the raw
  number.
</p>
<p>
  <strong>Pre-trend test:</strong> the third line of each cell shows the average ATT over the
  pre-period (e ∈ [−5, −2]) and a "✓ / ✗" indicating whether that average is far from zero
  (✗ at |z| ≥ 1.96). Two equally-sized headline estimates can have very different credibility
  if one's pre-trend rejects and the other's doesn't — that's why we report it inline.
</p>
</div>

<h3>3.1 Callaway-Sant'Anna ATT(g, t)</h3>
<p>
For each treatment cohort g (year of first 0→1 or 1→0 switch in the policy variable, depending
on policy) and each calendar year t in the analysis window:
</p>
<p style="text-align:center; font-style:italic;">
  ATT(g, t) = E[Y<sub>t</sub> − Y<sub>g−1</sub> | treated, cohort g] − E[Y<sub>t</sub> − Y<sub>g−1</sub> | comparison group]
</p>
<p>
We use the never-treated comparison group (no states ever switch in the panel window). Two specifications:
<strong>OR</strong> = basic outcome regression, no covariates; <strong>RA</strong> = regression-adjusted
(Sant'Anna & Zhao 2020) with <code>ln_population</code>, <code>unemployment_rate</code>, and
<code>ln_pcpi_real_2024</code> measured at year g−1. Two control rules: <strong>broad</strong> uses every
never-treated state; <strong>strict</strong> applies a policy-specific filter (e.g., for permitless
carry, controls must be shall-issue and permit-required throughout [g−5, g+5]).
Standard errors via state-cluster Rademacher multiplier bootstrap (B = 2,000).
</p>
<p>
Aggregations: event-study ATT(e) is a treated-state-count-weighted average of ATT(g, g+e) across
cohorts; overall post-treatment ATT is the same average for e ≥ 0.
</p>

<h3>3.2 Cengiz-Dube-Lindner-Zipperer stacked DiD</h3>
<p>
For each treatment cohort g, we build a stack: the treated state(s) plus all clean controls
observed across [g−5, g+5]. We concatenate all stacks and run TWFE with stack-by-state and
stack-by-event-time fixed effects:
</p>
<p style="text-align:center; font-style:italic;">
  Y = β · (treated × post) + α<sub>stack,state</sub> + δ<sub>stack,event</sub> + ε
</p>
<p>
β is the average post-treatment ATT. We estimate via Frisch-Waugh-Lovell within-FE partialling.
Standard errors are state-clustered (since the same state can appear in multiple stacks as a
control). Three weighting specifications:
</p>
<ul>
  <li><strong>Unweighted:</strong> plain stacked DiD, no covariate adjustment.</li>
  <li><strong>Regression-adjusted (RA):</strong> TWFE with covariates as linear controls.</li>
  <li><strong>Entropy-balanced (EB, Hainmueller 2012):</strong> per-stack reweighting of controls
      so their baseline (g−1) covariate moments exactly match the treated unit's. Doubly robust.
      Implementation: Newton's method on the convex dual of Hainmueller's optimization problem.
      <em>Caveat:</em> EB max weights reach 31–33 in some stacks, indicating the treated and
      control covariate distributions barely overlap. In those cases, EB amplifies variance and
      should be read as the most aggressive bound on what reweighting can buy you, not as a
      definitive estimate.</li>
</ul>

<h3>3.3 Roth-Sant'Anna pre-trend sensitivity bounds</h3>
<p>
For event-study coefficients with potentially problematic pre-trends, we report Roth-Sant'Anna
(2019) honest sensitivity bounds. We fit a weighted linear regression of pre-period
(e ∈ [−5, −2]) ATT coefficients on event time, recover the slope b̂ and its SE, then for each
post-period e ≥ 0:
</p>
<p style="text-align:center; font-style:italic;">
  ATT<sub>adj</sub>(e) = ATT(e) − M · (e + 1) · b̂
</p>
<p>
with the CI half-width inflated by M·(e+1)·SE(b̂). M is the sensitivity parameter:
<strong>M = 0</strong> corresponds to the strict parallel-trends assumption;
<strong>M = 1</strong> means "post-trend deviation is at most as large as the linear extrapolation
of the observed pre-trend"; <strong>M = 2</strong> is a conservative "I don't trust the pre-trend
at all" choice. Reported M ∈ {0, 0.5, 1.0, 2.0}.
</p>

<h3>3.4 Substitution test</h3>
<p>
For policies whose primary outcome is firearm suicide, we add non-firearm suicide rate (derived
as <code>total_suicide_rate − firearm_suicide_rate</code>) and total suicide rate as outcomes.
The test:
</p>
<ul>
  <li>If firearm suicide moves and non-firearm stays flat, total moves by the firearm amount —
    the policy changes total suicidal deaths.</li>
  <li>If firearm and non-firearm move in opposite directions of similar magnitudes, the policy
    just shifts methods and total is unchanged.</li>
  <li>If both move in the same direction, the substitution interpretation breaks down and points
    to confounding by other co-occurring policies / cultural changes.</li>
</ul>

<h3>3.5 Placebo: motor vehicle theft</h3>
<p>
None of the three policies has a direct mechanism for affecting motor vehicle theft. A clean
identification design should produce ATT ≈ 0 for it. Persistent placebo failure tells us about
unobserved trend differences between treated and control states.
</p>
</section>


{perm_section.replace('<section class="policy">', '<section class="policy" id="permitless-carry">')}

{rf_section.replace('<section class="policy">', '<section class="policy" id="red-flag">')}

{ubc_section.replace('<section class="policy">', '<section class="policy" id="ubc">')}

{syg_section.replace('<section class="policy">', '<section class="policy" id="stand-your-ground">')}

{mag_section.replace('<section class="policy">', '<section class="policy" id="magazine-ban">')}

{age_section.replace('<section class="policy">', '<section class="policy" id="age21-handgun">')}

{awb_section.replace('<section class="policy">', '<section class="policy" id="assault-weapons-ban">')}

{rdd_block}

{county_block}


<section id="synthesis">
<h2>13. Cross-policy synthesis</h2>
<p>
Across three policies × two estimators × multiple specifications, two findings are robust enough
to be the lede of a paper:
</p>
<ol>
  <li>
    <strong>Permitless carry adoption raises total suicide by about 0.6 per 100,000.</strong>
    Direction agrees in both estimators; magnitude in (+0.5, +0.7); substitution test passes;
    Roth-SA bounds at M = 1 survive in CS21 RA specs. The MVT placebo fails so this isn't a
    pure causal claim, but the substitution-test pattern is hard to explain by trend-gap
    confounding alone.
  </li>
  <li>
    <strong>Civil-petition red-flag laws reduce firearm homicide.</strong> Direction agrees in
    both estimators; magnitude is uncertain (CS21 broad/RA −0.14; stacked-DiD spans −0.50 to
    −0.73; EB pushes to −2.13 but is fragile); pre-trend test does not reject in the cleanest
    CS21 spec (z = −0.58); placebo CIs from stacked-DiD include zero (much milder placebo
    failure than CS21).
  </li>
</ol>
<p>
The other six "headline" cells (red-flag suicide, UBC suicide, UBC homicide, permitless-carry
homicide, all of which were significant in some specifications) do not survive the joint set of
robustness checks documented in this report. That is itself a finding — most published
single-estimator results on these questions probably overstate what the data identify.
</p>
</section>


<section id="limitations">
<h2>14. Limitations and caveats</h2>
<ul>
  <li>The motor vehicle theft placebo continues to fail in some specifications across all three
    policies. The reweighting (RA, EB, strict control rule) helps but does not fully eliminate
    the property-crime trend gap between treated and control states. Outcome-specific covariates
    or county-level identification with border discontinuity designs would be the natural next
    response.</li>
  <li>For UBC the strict-rule control pool collapses to the same set as the broad rule, so we
    only have two effective specifications (OR and RA). The other policies have four.</li>
  <li>Single-state cohorts (AZ 2010 and WY 2011 for permitless carry; VT 2023 for red-flag)
    contribute very noisy ATT(g, t) cells. They are kept in the pooled CS21 estimates but
    deserve separate-cohort robustness checks.</li>
  <li>Outcomes from the firearm suicide / homicide v2 file end in 2023. UBC and red-flag 2024
    adopters cannot be analyzed yet.</li>
  <li>Entropy balancing can be unstable when covariate overlap between treated and control is
    poor. The EB column in stacked-DiD tables should be treated as a robustness range, not a
    definitive estimate. Maximum per-stack EB weights of 31–33 indicate that one or two
    control states are doing nearly all the work; estimates from such stacks should be
    interpreted with caution.</li>
  <li>Roth-Sant'Anna bounds reported here use the linear-extrapolation form. The full
    Rambachan-Roth (2023) procedure with non-linear bounds (their HonestDiD R package) would
    provide tighter inference where pre-trends are non-linear.</li>
  <li>True county-level firearm-mortality identification (a natural follow-up given the
    county-level crime data we have) is blocked by CDC public-data policy. See
    <a href="https://github.com/jedediahpidareese-coder/firearms-regulation-map/blob/main/data_appendix.md">Section 2.10 of the data appendix</a> for the documented
    paths and their constraints.</li>
</ul>
</section>


<section id="appendix">
<h2>15. Appendix: code map and reproduction</h2>
<table>
  <thead><tr><th>Component</th><th>Script</th><th>Output</th></tr></thead>
  <tbody>
    <tr><td>Shared CS21 machinery</td><td><code>scripts/cs_lib.py</code></td><td>—</td></tr>
    <tr><td>Shared stacked-DiD machinery</td><td><code>scripts/lib_stacked_dd.py</code></td><td>—</td></tr>
    <tr><td>Permitless carry: CS21</td><td><code>scripts/run_cs_permitless_carry.py</code></td><td><code>outputs/permitless_carry_cs/</code></td></tr>
    <tr><td>Permitless carry: stacked DiD</td><td><code>scripts/run_stacked_dd.py</code></td><td><code>outputs/permitless_carry_stackdd/</code></td></tr>
    <tr><td>Red-flag: CS21</td><td><code>scripts/run_cs_red_flag.py</code></td><td><code>outputs/red_flag_cs/</code></td></tr>
    <tr><td>Red-flag: stacked DiD</td><td><code>scripts/run_stacked_dd.py</code></td><td><code>outputs/red_flag_stackdd/</code></td></tr>
    <tr><td>UBC: CS21</td><td><code>scripts/run_cs_ubc.py</code></td><td><code>outputs/ubc_cs/</code></td></tr>
    <tr><td>UBC: stacked DiD</td><td><code>scripts/run_stacked_dd.py</code></td><td><code>outputs/ubc_stackdd/</code></td></tr>
    <tr><td>Synthetic control (TX 2021, FL 2023)</td><td><code>scripts/run_scm_permitless_carry.py</code></td><td><code>outputs/permitless_carry_scm/</code></td></tr>
    <tr><td>Roth-Sant'Anna bounds</td><td><code>scripts/run_roth_sa_bounds.py</code></td><td><code>outputs/roth_sa_bounds/</code></td></tr>
    <tr><td>This report</td><td><code>scripts/build_research_report.py</code></td><td><code>outputs/research_report/index.html</code></td></tr>
  </tbody>
</table>
<p>
To reproduce the entire research portion of the project from scratch:
</p>
<pre style="background:#f7f6f1; padding:10px; font-size:11px; line-height:1.4; overflow-x:auto;">
# Build state panels first (see data_appendix.md and the README for upstream
# raw-input requirements):
python scripts/build_firearms_panel.py
python scripts/audit_panels.py
python scripts/augment_panels.py

# Run all three CS21 analyses:
python scripts/run_cs_permitless_carry.py
python scripts/run_cs_red_flag.py
python scripts/run_cs_ubc.py

# Run the synthetic-control case studies:
python scripts/run_scm_permitless_carry.py

# Run the parallel stacked-DiD implementation across all three policies:
python scripts/run_stacked_dd.py

# Run Roth-Sant'Anna pre-trend bounds for both estimators:
python scripts/run_roth_sa_bounds.py

# Build this report:
python scripts/build_research_report.py
</pre>
<p>
Print this page to PDF: in any modern browser, File &rarr; Print &rarr; Save as PDF.
The print stylesheet at the top of this document handles page breaks and font sizing
appropriately for letter-paper output.
</p>
</section>

</body>
</html>
"""
    return html


def main():
    html = build_html()
    out_path = OUTDIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}  ({out_path.stat().st_size/1024:,.0f} KB)")
    print()
    print("Open in any browser, then File -> Print -> Save as PDF for a publication-style PDF.")


if __name__ == "__main__":
    main()
