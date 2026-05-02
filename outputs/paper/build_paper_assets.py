"""Build the paper's figures/ and tables/ directories from the existing
project outputs. Run after any change to the underlying CSV/SVG outputs;
re-run before each Overleaf upload.

Figures are SVG (rendered on Overleaf via the `svg` package, which calls
Inkscape). Tables are LaTeX `tabular` fragments included in main.tex via
`\input{tables/...}`. All numbers are pulled directly from the existing
CSVs so the paper auto-updates when the analysis pipeline reruns.

POLICY = permitless carry. Adapt POLICY_SHORT and the SCM_CASES list
to extend to other policies later.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
PAPER = ROOT / "outputs" / "paper"
FIG = PAPER / "figures"
TBL = PAPER / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TBL.mkdir(parents=True, exist_ok=True)

POLICY_SHORT = "permitless_carry"
POLICY_LABEL = "Permitless concealed carry"
SCM_CASES = [("TX_2021", "Texas (2021)")]
# Florida (2023) is intentionally excluded: with one year of post-policy
# mortality data, an SCM falls below the multi-year post-period standard
# of the published synthetic-control literature (ADH 2010, DAW 2019,
# Crifasi 2015, Rudolph 2015, McCourt 2020).

# --------------------------------------------------------------------------
# 1) Figures: copy the SVGs we'll cite from the existing pipeline outputs.
# --------------------------------------------------------------------------

# Each entry is (source path, destination filename, caption note,
# title_override). title_override replaces the SVG's top-level title text
# at copy time -- the upstream plotting scripts use a single template that
# mislabels some figures (e.g. the stacked-DD event study inherits a
# "Callaway-Sant'Anna" title from a shared header). The override is the
# title shown in the rendered PDF figure itself; the LaTeX caption is set
# separately in main.tex.
FIGURE_SOURCES = [
    # Event-study DiD main figure (broad / RA, headline tier).
    (OUTPUTS / f"{POLICY_SHORT}_cs" / "figures" / "event_study_broad_ra_4panel.svg",
     "fig2_cs21_event_study.svg",
     "Event-study DiD - headline specification",
     "Event-study estimates of permitless carry's effect, by years since adoption"),
    # Stacked DiD event study (entropy-balanced headline).
    (OUTPUTS / f"{POLICY_SHORT}_stackdd" / "figures" / "event_study_eb_4panel.svg",
     "fig3_stackdd_event_study.svg",
     "Stacked DiD - entropy-balanced headline",
     "Stacked event-study estimates with entropy-balanced controls"),
    # Border-county event study (secondary outcomes - state-joined mortality).
    (OUTPUTS / f"{POLICY_SHORT}_rdd" / "figures" / "event_study_secondary.svg",
     "fig5_rdd_event_study.svg",
     "Border-county comparison (contiguous-county pairs)",
     "Border-county event study: differences within contiguous county pairs"),
]
for case_dir, case_label in SCM_CASES:
    for outcome, label in [("firearm_suicide_rate",
                            f"{case_label} firearm suicide"),
                           ("total_suicide_rate",
                            f"{case_label} total suicide")]:
        src = OUTPUTS / f"{POLICY_SHORT}_scm" / case_dir / "figures" / f"{outcome}.svg"
        dst_name = f"fig4_scm_{case_dir}_{outcome}.svg"
        # SCM titles are correct upstream — pass None to skip rewrite.
        FIGURE_SOURCES.append((src, dst_name, label, None))


def _rewrite_svg_title(svg_path: Path, new_title: str) -> bool:
    """Replace the top <text font-size="14"> element's text with new_title.

    Returns True if a title was found and rewritten.
    """
    import re
    txt = svg_path.read_text(encoding="utf-8")
    # The plotting templates emit a single top-of-figure <text font-size="14"
    # font-weight="600">...</text> element. Rewrite its inner text.
    pat = r'(<text\s[^>]*font-size="14"[^>]*>)[^<]*(</text>)'
    new_txt, n = re.subn(pat, lambda m: m.group(1) + new_title + m.group(2),
                         txt, count=1)
    if n == 1:
        svg_path.write_text(new_txt, encoding="utf-8")
        return True
    return False


print("Copying figures ...")
for src, dst_name, label, title_override in FIGURE_SOURCES:
    if not src.exists():
        print(f"  ! missing source: {src.relative_to(ROOT)}")
        continue
    dst = FIG / dst_name
    shutil.copy2(src, dst)
    note = label
    if title_override:
        if _rewrite_svg_title(dst, title_override):
            note = f"{label}  [title -> {title_override!r}]"
    print(f"  {src.name:50s} -> figures/{dst_name}  ({note})")

# --------------------------------------------------------------------------
# 2) Tables (LaTeX `tabular` fragments)
# --------------------------------------------------------------------------

def latex_escape(s: str) -> str:
    return (str(s)
            .replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
            .replace("#", r"\#").replace("$", r"\$"))


def stars(z: float) -> str:
    if pd.isna(z):
        return ""
    az = abs(z)
    if az >= 2.576: return r"$^{***}$"
    if az >= 1.96:  return r"$^{**}$"
    if az >= 1.645: return r"$^{*}$"
    return ""


# Table 1: cohort table.
def write_cohort_table():
    df = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_cs" / "cohort_n.csv")
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"  {int(r['g_cohort'])} & {int(r['n_states'])} & "
            f"\\texttt{{{latex_escape(r['states'])}}} \\\\"
        )
    body = "\n".join(rows)
    out = TBL / "table_cohorts.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Permitless carry adoption cohorts, 1999--2023}\n"
        "\\label{tab:cohorts}\n"
        "\\begin{tabular}{ccp{0.6\\linewidth}}\n"
        "\\toprule\n"
        "Adoption year & States adopting & States \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Source: Tufts State Firearm Laws Database, cross-checked against the RAND State Firearm Laws Database. The adoption year is the first year in which the state no longer required a permit to carry a concealed loaded handgun in public.\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 3: headline estimates across the four estimators.
def write_headline_table():
    cs_df = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_cs" / "overall_att.csv")
    sd_df = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_stackdd" / "att_post.csv")
    rdd_df = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_rdd" / "headline.csv")

    # Filter to headline cells.
    cs_h = cs_df[(cs_df["spec"] == "ra")
                 & (cs_df["control_rule"] == "broad")
                 & (cs_df["tier"] == "headline")]
    sd_h = sd_df[(sd_df["spec"] == "eb") & (sd_df["tier"] == "headline")]

    outcomes = [
        ("firearm_suicide_rate",     "Firearm suicide rate"),
        ("nonfirearm_suicide_rate",  "Non-firearm suicide rate"),
        ("total_suicide_rate",       "Total suicide rate"),
        ("motor_vehicle_theft_rate", "Motor vehicle theft (placebo)"),
    ]
    rows = []
    for ocol, olabel in outcomes:
        # CS21
        c = cs_h[cs_h["outcome"] == ocol]
        cs_cell = "—"
        if not c.empty:
            r = c.iloc[0]
            cs_cell = (f"{r['att_overall_post']:+.3f}{stars(r['z'])}"
                       f"\\newline {{\\footnotesize ({r['se_overall_post']:.3f})}}")
        # Stacked-DD (EB headline)
        s = sd_h[sd_h["outcome"] == ocol]
        sd_cell = "—"
        if not s.empty:
            r = s.iloc[0]
            sd_cell = (f"{r['att']:+.3f}{stars(r['z'])}"
                       f"\\newline {{\\footnotesize ({r['se']:.3f})}}")
        # RDD (state-joined mortality is in the headline.csv)
        rdd_ocol = "state_" + ocol if ocol != "motor_vehicle_theft_rate" else "county_motor_vehicle_theft_rate"
        rdr = rdd_df[rdd_df["outcome"] == rdd_ocol]
        rdd_cell = "—"
        if not rdr.empty:
            r = rdr.iloc[0]
            rdd_cell = (f"{r['beta']:+.3f}{stars(r['z'])}"
                        f"\\newline {{\\footnotesize ({r['se']:.3f})}}")
        rows.append(
            f"  {latex_escape(olabel)} & {cs_cell} & {sd_cell} & {rdd_cell} \\\\"
        )
    body = "\n".join(rows)
    out = TBL / "table_headline.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Estimated effect of permitless carry adoption on suicide rates, by research design (per 100,000 residents)}\n"
        "\\label{tab:headline}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & Event-study & Stacked & Border-county \\\\\n"
        " & DiD & DiD (entropy) & comparison \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Standard errors in parentheses. $^{*}\\,p<0.10$, $^{**}\\,p<0.05$, $^{***}\\,p<0.01$ (two-sided).\n"
        "\\item Event-study DiD: Callaway and Sant'Anna (2021) heterogeneity-robust event-study estimator with the headline covariate specification and the never-treated states as the control pool. Standard errors via state-cluster wild bootstrap (2,000 replications).\n"
        "\\item Stacked DiD (entropy): Cengiz et al.\\ (2019) cohort-specific stacking with Hainmueller (2012) entropy balancing on pre-policy covariates; state-clustered standard errors.\n"
        "\\item Border-county comparison: contiguous-county-pair design adapted from Dube, Lester, and Reich (2010); 100 km bandwidth; county fixed effects and pair-by-year fixed effects; state-clustered standard errors.\n"
        "\\item In the border-county design, suicide-rate outcomes are joined down from the state level to the county panel; the substantive variation comes from contrasts within border pairs.\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 4: multiverse sensitivity (Minimal / Headline / Expanded).
def write_multiverse_table():
    df = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_cs" / "overall_att.csv")
    sub = df[(df["spec"] == "ra") & (df["control_rule"] == "broad")
             & (df["tier"].isin(["minimal", "headline", "expanded"]))]
    outcomes = [
        ("firearm_suicide_rate",    "Firearm suicide"),
        ("nonfirearm_suicide_rate", "Non-firearm suicide"),
        ("total_suicide_rate",      "Total suicide"),
    ]
    rows = []
    for ocol, olabel in outcomes:
        cells = [latex_escape(olabel)]
        for tier in ("minimal", "headline", "expanded"):
            r = sub[(sub["outcome"] == ocol) & (sub["tier"] == tier)]
            if r.empty:
                cells.append("—")
                continue
            r = r.iloc[0]
            cells.append(f"{r['att_overall_post']:+.3f}{stars(r['z'])}"
                         f"\\newline {{\\footnotesize ({r['se_overall_post']:.3f})}}")
        rows.append("  " + " & ".join(cells) + " \\\\")
    body = "\n".join(rows)
    out = TBL / "table_multiverse.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Sensitivity of the event-study estimate to covariate specification}\n"
        "\\label{tab:multiverse}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & Minimal set & Headline set & Expanded set \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Standard errors in parentheses. $^{*}\\,p<0.10$, $^{**}\\,p<0.05$, $^{***}\\,p<0.01$ (two-sided).\n"
        "\\item Estimates are from the Callaway and Sant'Anna (2021) event-study estimator under three literature-motivated covariate specifications. Minimal: log population, poverty rate, unemployment rate, and demographic shares (after Lott and Mustard 1997). Headline: minimal set plus imprisonment per 100,000, sworn officers per 100,000, and per capita alcohol consumption (after Donohue, Aneja, and Weber 2019, augmented with alcohol following McClellan and Tekin 2017). Expanded: headline set plus drug-overdose mortality, religious adherence, and police expenditure per capita.\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 5: SCM per-state results (Texas only; see SCM_CASES filter above).
def write_scm_table():
    rows = []
    for case_dir, _case_label in SCM_CASES:
        placebo = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_scm" / case_dir / "placebo.csv")
        for ocol, olabel in [("firearm_suicide_rate", "Firearm suicide"),
                             ("total_suicide_rate", "Total suicide"),
                             ("motor_vehicle_theft_rate", "Motor-vehicle theft (placebo)")]:
            r = placebo[placebo["outcome"] == ocol]
            if r.empty:
                continue
            r = r.iloc[0]
            p = r["p_value_two_sided"]
            sig = (r"$^{***}$" if p <= 0.01 else
                   r"$^{**}$"  if p <= 0.05 else
                   r"$^{*}$"   if p <= 0.10 else "")
            rows.append(
                f"  {latex_escape(olabel)} & "
                f"{r['actual_post_effect']:+.3f}{sig} & "
                f"{p:.3f} & {int(r['n_placebo'])} \\\\"
            )
    body = "\n".join(rows)
    out = TBL / "table_scm.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Synthetic-control case study of Texas (2021 adoption): average post-policy gap between Texas and its synthetic counterpart (per 100,000)}\n"
        "\\label{tab:scm}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & Post-policy gap & Placebo $p$ & Donors \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Synthetic control follows Abadie, Diamond, and Hainmueller (2010). The donor pool is the set of shall-issue and permit-required states throughout the case study's twelve-year pre-period and three-year post-period. Inference follows Abadie (2021): we re-estimate the synthetic control treating each donor state in turn as if it were treated, and report the share of placebo gaps at least as large in magnitude as the actual gap. Florida (2023 adoption) is excluded: with one year of post-policy mortality data, the design falls below the multi-year post-period standard of the published synthetic-control literature \\citep{abadie2010, donohue2019, crifasi2015, rudolph2015, mccourt2020}.\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 6: Roth-Sant'Anna pre-trend bounds.
def write_rs_bounds_table():
    rows = []
    bounds_files = sorted((OUTPUTS / "roth_sa_bounds").glob(
        f"cs21_{POLICY_SHORT}_*_firearm_suicide_rate_bounds.csv"))
    for f in bounds_files:
        # filename: cs21_permitless_carry_<rule>_<spec>_firearm_suicide_rate_bounds.csv
        # parts:    [cs21, permitless, carry, <rule>, <spec>, firearm, suicide, rate, bounds]
        parts = f.stem.split("_")
        spec = parts[-5]   # 'or' or 'ra'
        rule = parts[-6]   # 'broad' or 'strict'
        df = pd.read_csv(f)
        e1 = df[df["event_time"] == 1]
        if e1.empty:
            continue
        for _, r in e1.iterrows():
            M = r.get("M_sensitivity")
            if pd.isna(M):
                continue
            # CSV columns are ci_low / ci_high (not bound_low / bound_high).
            lo = r.get("ci_low", float("nan"))
            hi = r.get("ci_high", float("nan"))
            rows.append(
                f"  {rule}/{spec.upper()} & {M:.1f} & "
                f"{lo:+.3f} & {hi:+.3f} \\\\"
            )
    body = "\n".join(rows) if rows else "  \\multicolumn{4}{c}{\\textit{(no bounds CSVs found; run scripts/run\\_roth\\_sa\\_bounds.py)}} \\\\"
    out = TBL / "table_rs_bounds.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Sensitivity to violations of parallel trends: bounds on the firearm-suicide effect one year after adoption (per 100,000)}\n"
        "\\label{tab:rs_bounds}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Spec. & Allowed deviation $M$ & Lower bound & Upper bound \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Bounds follow Rambachan and Roth (2023). The allowed deviation $M$ is the hypothetical drift of the post-policy counterfactual away from a continuation of the observed pre-policy trend, expressed as a multiple of the pre-trend slope: $M = 0$ corresponds to exactly parallel trends, $M = 1$ allows one pre-trend slope of unobserved drift, and so on. A lower bound that excludes zero indicates the firearm-suicide effect remains positive under that level of allowed deviation. ``Spec.'' indicates the control pool (broad: all never-treated states; strict: shall-issue only) and the doubly-robust adjustment (OR: outcome regression; RA: regression adjustment).\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 7: COVID-19 stringency robustness check.
# For each of the three pooled designs (event-study DiD, stacked DiD with
# entropy balancing, border-county comparison) and each of the three
# suicide outcomes (firearm, non-firearm, total), report the headline
# estimate from the original specification AND the estimate with the
# OxCGRT covid_stringency_mean covariate added, side by side.
#
# Covariate-tier choice (CS21 event-study and stacked DiD): we read the
# `minimal` tier rather than `headline` because the headline RA spec
# falls back to OR (no-covariate) for any cohort whose base year
# (g - 1) is >= 2018, due to NIAAA alcohol per capita ending in 2018
# and RAND household firearm ownership ending in 2016. Adding the COVID
# variable to a fallback OR cell has no effect because the regression
# never enters covariate-mode there. The minimal tier (log population,
# log PCPI, unemployment, poverty, share male, age 15-24, age 25-44)
# has data through 2024 for all states, so the COVID variable actually
# enters the regression there and the comparison is informative.
def write_covid_robustness_table():
    cs_dir = OUTPUTS / f"{POLICY_SHORT}_cs"
    cs_cv_dir = OUTPUTS / f"{POLICY_SHORT}_cs_with_covid"
    cs_ce_dir = OUTPUTS / f"{POLICY_SHORT}_cs_with_covid_efna"
    cs_cd_dir = OUTPUTS / f"{POLICY_SHORT}_cs_with_covid_efna_despair"
    sd_dir = OUTPUTS / f"{POLICY_SHORT}_stackdd"
    sd_cv_dir = OUTPUTS / f"{POLICY_SHORT}_stackdd_with_covid"
    sd_ce_dir = OUTPUTS / f"{POLICY_SHORT}_stackdd_with_covid_efna"
    sd_cd_dir = OUTPUTS / f"{POLICY_SHORT}_stackdd_with_covid_efna_despair"
    rdd_dir = OUTPUTS / f"{POLICY_SHORT}_rdd"
    rdd_cv_dir = OUTPUTS / f"{POLICY_SHORT}_rdd_with_covid"
    rdd_ce_dir = OUTPUTS / f"{POLICY_SHORT}_rdd_with_covid_efna"
    rdd_cd_dir = OUTPUTS / f"{POLICY_SHORT}_rdd_with_covid_efna_despair"

    cs_a = pd.read_csv(cs_dir / "overall_att.csv")
    cs_b = pd.read_csv(cs_cv_dir / "overall_att.csv") if (cs_cv_dir / "overall_att.csv").exists() else None
    cs_c = pd.read_csv(cs_ce_dir / "overall_att.csv") if (cs_ce_dir / "overall_att.csv").exists() else None
    cs_d = pd.read_csv(cs_cd_dir / "overall_att.csv") if (cs_cd_dir / "overall_att.csv").exists() else None
    sd_a = pd.read_csv(sd_dir / "att_post.csv")
    sd_b = pd.read_csv(sd_cv_dir / "att_post.csv") if (sd_cv_dir / "att_post.csv").exists() else None
    sd_c = pd.read_csv(sd_ce_dir / "att_post.csv") if (sd_ce_dir / "att_post.csv").exists() else None
    sd_d = pd.read_csv(sd_cd_dir / "att_post.csv") if (sd_cd_dir / "att_post.csv").exists() else None
    rdd_a = pd.read_csv(rdd_dir / "robustness.csv")
    rdd_b = pd.read_csv(rdd_cv_dir / "robustness.csv") if (rdd_cv_dir / "robustness.csv").exists() else None
    rdd_c = pd.read_csv(rdd_ce_dir / "headline.csv") if (rdd_ce_dir / "headline.csv").exists() else None
    rdd_d = pd.read_csv(rdd_cd_dir / "headline.csv") if (rdd_cd_dir / "headline.csv").exists() else None

    # CS21 cell: spec=ra, control_rule=broad, tier=minimal.
    def cs_cell(df, outcome):
        if df is None: return None
        s = df[(df["spec"] == "ra") & (df["control_rule"] == "broad")
               & (df["tier"] == "minimal") & (df["outcome"] == outcome)]
        return s.iloc[0] if not s.empty else None

    # Stacked DiD cell: spec=ra, tier=minimal (so COVID actually enters).
    def sd_cell(df, outcome):
        if df is None: return None
        s = df[(df["spec"] == "ra") & (df["tier"] == "minimal")
               & (df["outcome"] == outcome)]
        return s.iloc[0] if not s.empty else None

    # RDD cell: with_covariates spec for baseline; headline (forced cov)
    # for with-covid (which run_full_battery rewrites to use covariates).
    # Both have the same RA covariate set; with-covid adds covid_stringency_mean.
    def rdd_cell(df, outcome, baseline: bool):
        if df is None: return None
        spec = "with_covariates" if baseline else "headline"
        s = df[(df["spec_name"] == spec) & (df["outcome"] == outcome)]
        return s.iloc[0] if not s.empty else None

    outcomes = [
        ("firearm_suicide_rate",     "Firearm suicide rate"),
        ("nonfirearm_suicide_rate",  "Non-firearm suicide rate"),
        ("total_suicide_rate",       "Total suicide rate"),
    ]

    def fmt_cs(c):
        if c is None: return "—"
        return (f"{c['att_overall_post']:+.3f}{stars(c['z'])}"
                f"\\newline {{\\footnotesize ({c['se_overall_post']:.3f})}}")

    def fmt_sd(c):
        if c is None: return "—"
        return (f"{c['att']:+.3f}{stars(c['z'])}"
                f"\\newline {{\\footnotesize ({c['se']:.3f})}}")

    def fmt_rdd(c):
        if c is None: return "—"
        return (f"{c['beta']:+.3f}{stars(c['z'])}"
                f"\\newline {{\\footnotesize ({c['se']:.3f})}}")

    # Format four cells per design (baseline + stringency + stringency+EFNA
    # + stringency+EFNA+despair) stacked vertically. Row labels are kept
    # short to fit the column width; the table note makes the cumulative
    # meaning ("+ EFNA" includes stringency, "+ Despair" includes both)
    # explicit.
    def stacked(a, b, c, d, fmt):
        ta = fmt(a) if a is not None else "-"
        tb = fmt(b) if b is not None else "-"
        tc = fmt(c) if c is not None else "-"
        td = fmt(d) if d is not None else "-"
        return ("\\begin{tabular}{@{}c@{}}"
                f"{ta}\\\\[2pt] \\textit{{+ Str.}} {tb}"
                f"\\\\[2pt] \\textit{{+ EFNA}} {tc}"
                f"\\\\[2pt] \\textit{{+ Despair}} {td}"
                "\\end{tabular}")

    rows = []
    for ocol, olabel in outcomes:
        rdd_ocol = "state_" + ocol
        cs_a_c   = cs_cell(cs_a, ocol)
        cs_b_c   = cs_cell(cs_b, ocol)
        cs_c_c   = cs_cell(cs_c, ocol)
        cs_d_c   = cs_cell(cs_d, ocol)
        sd_a_c   = sd_cell(sd_a, ocol)
        sd_b_c   = sd_cell(sd_b, ocol)
        sd_c_c   = sd_cell(sd_c, ocol)
        sd_d_c   = sd_cell(sd_d, ocol)
        rdd_a_c  = rdd_cell(rdd_a, rdd_ocol, baseline=True)
        rdd_b_c  = rdd_cell(rdd_b, rdd_ocol, baseline=False)
        # _with_covid_efna and _with_covid_efna_despair RDD outputs only
        # have headline.csv (not robustness.csv); the headline row in those
        # already includes the cumulative covariate set.
        rdd_c_c  = rdd_cell(rdd_c, rdd_ocol, baseline=False) if rdd_c is not None else None
        rdd_d_c  = rdd_cell(rdd_d, rdd_ocol, baseline=False) if rdd_d is not None else None
        rows.append(
            f"  {latex_escape(olabel)} & "
            f"{stacked(cs_a_c, cs_b_c, cs_c_c, cs_d_c, fmt_cs)} & "
            f"{stacked(sd_a_c, sd_b_c, sd_c_c, sd_d_c, fmt_sd)} & "
            f"{stacked(rdd_a_c, rdd_b_c, rdd_c_c, rdd_d_c, fmt_rdd)} \\\\"
        )
    body = "\n\\addlinespace\n".join(rows)
    out = TBL / "table_covid_robustness.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{COVID-19 and deaths-of-despair robustness: estimated effect of permitless carry on suicide rates, baseline vs.\\ with the OxCGRT lockdown stringency index, vs.\\ with stringency plus the Fraser EFNA economic-freedom index, vs.\\ with stringency, EFNA, and the deaths-of-despair stack (synthetic-opioid death rate, frequent mental distress, any-mental-illness prevalence; per 100,000 residents)}\n"
        "\\label{tab:covid_robustness}\n"
        "\\scriptsize\n"
        "\\setlength{\\tabcolsep}{3pt}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & Event-study DiD & Stacked DiD (RA) & Border-county \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Each cell shows four estimates stacked vertically: the baseline (top); the same estimate with the \\citet{hale2021} OxCGRT state-year mean stringency index added as a covariate (``+ Str.''); the estimate with both stringency and the Fraser Institute Economic Freedom of North America index \\citep{stansel2023} added as covariates (``+ EFNA''; cumulative, also includes stringency); and the estimate with stringency, EFNA, and the deaths-of-despair stack (synthetic\\_opioid\\_death\\_rate, freq\\_mental\\_distress\\_pct, ami\\_pct) added as covariates (``+ Despair''; cumulative, also includes stringency and EFNA). Motivation for the deaths-of-despair stack: \\citet{casedeaton2015, casedeaton2017, ruhm2018, hollingsworth2017, czeisler2020}. Standard errors in parentheses. $^{*}\\,p<0.10$, $^{**}\\,p<0.05$, $^{***}\\,p<0.01$ (two-sided).\n"
        "\\item OxCGRT covers 2020-01-01 through 2022-12-31; 2023+ rows are carried forward from 2022, and pre-2020 rows are zero-filled. EFNA varies across the entire pre- and post-treatment window and captures the broader regulatory and fiscal-policy environment, with subindex movements during 2020--2022 reflecting differential state-level COVID policy responses.\n"
        "\\item Event-study DiD: Callaway--Sant'Anna RA spec with the minimal covariate tier (log population, log PCPI, unemployment, poverty, share male, age 15--24, age 25--44). The minimal tier is reported because the headline RA tier falls back to outcome regression for any cohort whose base year is $\\ge 2018$ (NIAAA alcohol per capita ends 2018; RAND household firearm ownership ends 2016), which would render the additional covariates inert in the headline tier for the post-2020 cohorts where they could matter.\n"
        "\\item Stacked DiD: Cengiz et al.\\ (2019) RA spec with the same minimal covariate tier, for the same reason.\n"
        "\\item Border-county: Dube, Lester, and Reich (2010) contiguous-county-pair design at the headline 100\\,km bandwidth. All three rows include the full RDD covariate set (county-grain demographics, state-joined CJ controls, alcohol per capita); the second adds OxCGRT covid\\_stringency\\_mean and the third also adds efna\\_overall.\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# --------------------------------------------------------------------------

def main() -> None:
    print("\nGenerating LaTeX tables ...")
    write_cohort_table()
    write_headline_table()
    write_multiverse_table()
    write_scm_table()
    write_rs_bounds_table()
    write_covid_robustness_table()
    print("\nDone. Re-run after pipeline changes.")


if __name__ == "__main__":
    main()
