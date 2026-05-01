# Child-Access Prevention (CAP) pipeline -- SKIPPED at Phase 1

**Policy slug:** `cap`
**Decision:** STOP after Phase 1; do not run CS21 / Stacked-DiD / Roth-Sant'Anna.
**Reason:** Tufts adoption history in this project's panel is too sparse to support
the Callaway-Sant'Anna design (<3 cohorts; only 1 cohort fits a `[g-5, g+5]`
event window).

---

## What we looked for

The task brief named several candidate Tufts columns for CAP:
`capliable` (negligent-storage criminal liability -- STRICT),
`capaccess` (general CAP statute -- BROADER),
`capuses`, `capunloaded`, `cap14`, `cap16`, `cap18`. The strict-CAP literature
(Webster, Vernick, et al.) focuses on `capliable`.

## What this project actually has

The Tufts panel embedded in this project is the **Siegel / Boston University**
codebook (RWJ Foundation Evidence for Action grant #73337, Westlaw-derived,
included as `data/tufts_state_firearm_laws.xlsx`). It uses a different
taxonomy than the Webster/Vernick CAP-variant set named in the brief.

Inspecting `data/tufts_state_firearm_laws_codebook.xlsx` (Sheet1, 72 variables)
and confirming against `data/processed/panel_core_augmented.csv` (110 columns),
the candidate columns named in the brief are **not present**:

| Brief's column | Present in Tufts panel? |
|---|---|
| `capliable`   | No |
| `capaccess`   | No |
| `capuses`     | No |
| `capunloaded` | No |
| `cap14`       | No |
| `cap16`       | No |
| `cap18`       | No |

The only column that lives in Tufts' "Child access prevention" category is:

- **`locked`** -- "All firearms in a household must be stored securely
  (locked away) at all times." Codebook explicitly notes this is the
  *mandatory secure-storage* rule and is "different from child access
  prevention laws that establish liability for failure to store weapons
  properly under certain conditions."

The other plausibly relevant column, `liability`, is **not** a CAP variable:
the codebook defines it under "Dealer regulations / Liability" -- it codes
whether **dealers** are civilly liable for damages from illegal sales. It is
unrelated to negligent-storage criminal liability of adult gun owners.

The project's own documentation confirms this mapping:

- `data/processed/highlight_law_variables.csv`:
  `locked,State has child access prevention / locked storage requirement`
- `firearms_us_data_inventory.md`:
  Tufts is described as covering "child access prevention" via this single
  column.

So `locked` is the only Tufts variable in this project that maps (broadly)
to the CAP family.

## Why `locked` cannot drive a CS21 design here

Adoption history of `locked` (first 0->1 transition per state, 1979-2024):

| State | Adoption year | Fits `[g-5, g+5]` in 1999-2023 window? |
|---|---|---|
| MA  | 1998 | No -- adoption is 1 year before panel start (`g-5` = 1993, outside) |
| OR  | 2021 | No -- only `g+0`..`g+2` observed before outcome end (2023) |
| CT  | 2023 | No -- no post-treatment years before outcome end |
| RI  | 2024 | No -- adoption is after outcomes end |

That is **4 states ever**, **0 cohorts** that satisfy the `cs_lib`
default `min_pre_k=5` and `exclude_after=2023` rules used for the other
three pipelines.

Per the brief's stop rule:

> If Tufts adoption history is too sparse (<3 cohorts) or messy (>30%
> disagree with RAND), STOP, document why ... and reply with "skipped
> because X."

Zero usable cohorts is well below the 3-cohort floor.

A second-best run on `locked` is also inadvisable because the construct
mismatch is severe:

- `locked` is a **mandatory** secure-storage rule that applies to every
  firearm in the household at all times. The CAP literature (Webster,
  Vernick, et al.) studies **negligence-based** statutes that attach
  *conditional* criminal liability (only if a minor accesses the gun, or
  uses it, etc.), and finds the strongest effects for the criminal-liability
  variant (`capliable`). Treating `locked` as a CAP proxy would conflate
  two qualitatively different policies.
- Even setting that aside, the four `locked` states are highly atypical
  (CT, MA, OR, RI -- all small Northeast/Pacific states with strong baseline
  gun-control regimes), so causal identification against never-treated
  controls would be confounded by region/baseline policy stacking.

## What would make this pipeline runnable

To run the strict-CAP analysis the brief envisions, the project would need
to import an external CAP coding (e.g., the **RAND State Firearm Laws
Database**, which codes `Child-Access Prevention Laws` with a sub-coding
distinguishing negligence/recklessness liability and minor-access trigger;
or the **Giffords Law Center** state-level CAP coding) and add columns
analogous to `capliable` and `capaccess` to `panel_core_augmented.csv`.
That data-augmentation step is out of scope for this run (the brief forbids
new pip installs and does not authorize a new data ingest), so we stop
cleanly here.

## Decision: skipped

- Phase 1 stop rule met (<3 cohorts).
- No CS21, Stacked-DiD, Roth-Sant'Anna, or appendix run.
- No files written under `outputs/cap_cs/`, `outputs/cap_stackdd/`,
  `outputs/roth_sa_bounds/cap_*`.
- Worktree is otherwise untouched.
