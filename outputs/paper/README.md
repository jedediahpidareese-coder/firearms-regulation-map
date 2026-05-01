# Working Paper — Permitless Carry and Total Suicide

**Target journal:** Contemporary Economic Policy
**Compilation:** Overleaf (pdfLaTeX + biber).

## Files

- `main.tex` — paper body
- `references.bib` — BibTeX. Chicago author-date format via `biblatex-chicago`.
- `figures/` — SVG figures rendered via `\includesvg` (Overleaf has Inkscape).
- `tables/` — auto-generated `.tex` table fragments included in `main.tex` via `\input{tables/...}`.
- `build_paper_assets.py` — copies the relevant figures from
  `outputs/{policy}_cs/`, `outputs/{policy}_rdd/`, `outputs/{policy}_scm/`
  into `figures/`, and emits `tables/*.tex` from the underlying CSVs.

## Compile on Overleaf

1. Zip everything in this directory (`outputs/paper/`).
2. Upload to Overleaf as a new project ("New Project" → "Upload Project").
3. Set compiler to **pdfLaTeX** and bibliography backend to **Biber**
   (Menu → Settings → Compiler / TeX Live version recent enough for `biblatex-chicago`).
4. Compile. The first build will take longer because it processes the SVGs.

If the `svg` package fails on your Overleaf instance (rare), convert
the SVGs to PDF locally with `cairosvg` (`pip install cairosvg`) and
swap the `\includesvg` calls for `\includegraphics`.

## Local rebuild of figures + tables

```sh
python build_paper_assets.py
```

This copies the relevant figures from `outputs/{policy}_*` into
`figures/` and regenerates `tables/*.tex` from the corresponding
output CSVs. Re-run after any pipeline change.

## Style

- Body 12pt, 1.5 spacing, 1-inch margins
- Chicago author-date in-text citations (`\citep`, `\citet`)
- Specific page references via `\citepg{key}{42}` (custom macro)
- Tables in `threeparttable` for table notes
- Figures via `\includesvg`; subfigures via `subcaption`
