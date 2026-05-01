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
SCM_CASES = [("TX_2021", "Texas (2021)"), ("FL_2023", "Florida (2023)")]

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
    # CS21 main event study (broad / RA, headline tier — already filtered
    # by the cs_lib plot fix from earlier today)
    (OUTPUTS / f"{POLICY_SHORT}_cs" / "figures" / "event_study_broad_ra_4panel.svg",
     "fig2_cs21_event_study.svg",
     "Callaway-Sant'Anna ATT(g, t) — broad pool, RA headline",
     "Callaway-Sant'Anna ATT(g,t), permitless carry (RA, broad pool)"),
    # Stacked-DiD event study (EB headline)
    (OUTPUTS / f"{POLICY_SHORT}_stackdd" / "figures" / "event_study_eb_4panel.svg",
     "fig3_stackdd_event_study.svg",
     "Stacked-DiD ATT — entropy-balanced headline",
     "Stacked-DiD ATT, permitless carry (entropy-balanced controls)"),
    # Spatial RDD event study (secondary outcomes — state-joined mortality)
    (OUTPUTS / f"{POLICY_SHORT}_rdd" / "figures" / "event_study_secondary.svg",
     "fig5_rdd_event_study.svg",
     "Spatial-RDD ATT (border counties, state-pair x year FE)",
     "Spatial RDD event study, permitless carry (contiguous county pairs)"),
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
        "Adoption year (g) & N states & States \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Source: Tufts State Firearm Laws Database; cross-checked against the RAND State Firearm Laws Database. Cohort = first year the state's \\texttt{permitconcealed} indicator switches from 1 to 0.\n"
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
        "\\caption{Permitless carry: headline ATT estimates across estimators (per 100,000 residents)}\n"
        "\\label{tab:headline}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & CS21 (broad/RA) & Stacked-DD (EB) & Spatial RDD \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Standard errors in parentheses. $^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$ (two-sided).\n"
        "\\item CS21 = Callaway and Sant'Anna (2021) ATT(g,t) with literature-backed Headline covariate set; broad never-treated control pool. Standard errors via state-cluster Rademacher bootstrap (B = 2,000).\n"
        "\\item Stacked-DD = Cengiz et al.\\ (2019) with Hainmueller (2012) entropy balancing on baseline covariates; cluster-robust SE at the state level.\n"
        "\\item Spatial RDD = Dube, Lester and Reich (2010) contiguous-county-pair design; bandwidth 100 km; county FE + state-pair $\\times$ year FE; state-clustered SE.\n"
        "\\item RDD outcomes are state-joined-down to the county panel (no within-state variation by construction).\n"
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
        "\\caption{Multiverse: covariate-set sensitivity of the CS21 ATT (broad/RA spec)}\n"
        "\\label{tab:multiverse}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Outcome & Minimal set & Headline set & Expanded set \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Standard errors in parentheses. $^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$ (two-sided).\n"
        "\\item Three literature-backed covariate sets per Donohue, Aneja and Weber (2019). Minimal: ln(pop), poverty, unemployment, demographics (Lott-Mustard floor). Headline: + imprisonment rate, sworn officers per 100k, alcohol per capita (DAW set + alcohol). Expanded: + drug overdose mortality, religion, police expenditure (kitchen sink for robustness).\n"
        "\\end{tablenotes}\n"
        "\\end{threeparttable}\n"
    )
    print(f"  wrote {out.name}")


# Table 5: SCM per-state results.
def write_scm_table():
    rows = []
    for case_dir, case_label in SCM_CASES:
        placebo = pd.read_csv(OUTPUTS / f"{POLICY_SHORT}_scm" / case_dir / "placebo.csv")
        for ocol, olabel in [("firearm_suicide_rate", "Firearm suicide"),
                             ("total_suicide_rate", "Total suicide"),
                             ("motor_vehicle_theft_rate", "MV theft (placebo)")]:
            r = placebo[placebo["outcome"] == ocol]
            if r.empty:
                continue
            r = r.iloc[0]
            p = r["p_value_two_sided"]
            sig = (r"$^{***}$" if p <= 0.01 else
                   r"$^{**}$"  if p <= 0.05 else
                   r"$^{*}$"   if p <= 0.10 else "")
            rows.append(
                f"  {latex_escape(case_label)} & {latex_escape(olabel)} & "
                f"{r['actual_post_effect']:+.3f}{sig} & "
                f"{p:.3f} & {int(r['n_placebo'])} \\\\"
            )
    body = "\n".join(rows)
    out = TBL / "table_scm.tex"
    out.write_text(
        "\\begin{threeparttable}\n"
        "\\caption{Synthetic-control per-state results (post-period mean ATT, per 100,000)}\n"
        "\\label{tab:scm}\n"
        "\\begin{tabular}{llccc}\n"
        "\\toprule\n"
        "Case & Outcome & Post ATT & Permutation $p$ & Donor pool \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item Synthetic control method per Abadie, Diamond and Hainmueller (2010). Donor pool: shall-issue + permit-required states throughout each cohort's $[g-12, g+H]$ window. Inference: refit SCM on every donor as if treated; report two-sided permutation $p$-value as the share of placebo $|\\textrm{ATT}|$ at least as extreme as the actual.\n"
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
        "\\caption{Roth-Sant'Anna pre-trend honest bounds at $e = +1$ (firearm suicide rate, per 100k)}\n"
        "\\label{tab:rs_bounds}\n"
        "\\begin{tabular}{lccc}\n"
        "\\toprule\n"
        "Spec & $M$ & Lower bound & Upper bound \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\begin{tablenotes}\\footnotesize\n"
        "\\item $M$ = sensitivity parameter from Rambachan and Roth (2023): allowed deviation of the post-trend from a linear extrapolation of the observed pre-trend, expressed as a multiple of the pre-trend slope. $M = 0$ assumes parallel trends; $M = 1$ allows the post-trend to deviate by one pre-trend slope; $M = 2$ allows two. Bounds that exclude zero indicate the headline coefficient survives that level of pre-trend extrapolation.\n"
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
    print("\nDone. Re-run after pipeline changes.")


if __name__ == "__main__":
    main()
