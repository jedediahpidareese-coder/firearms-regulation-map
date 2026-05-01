# Working Paper — Permitless Carry and Total Suicide

**Target journal:** Contemporary Economic Policy
**Compilation:** local (tectonic + biber) or Overleaf (pdfLaTeX + biber).

## Files

- `main.tex` — paper body
- `references.bib` — BibTeX. Chicago author-date format via `biblatex-chicago`.
- `figures/` — SVG figures (canonical) plus PDF copies (used by `\includegraphics` for tectonic builds).
- `tables/` — auto-generated `.tex` table fragments included in `main.tex` via `\input{tables/...}`.
- `build_paper_assets.py` — copies the relevant figures from
  `outputs/{policy}_cs/`, `outputs/{policy}_rdd/`, `outputs/{policy}_scm/`
  into `figures/`, and emits `tables/*.tex` from the underlying CSVs.
- `build_paper.py` — local PDF build orchestration: SVG→PDF then tectonic.
- `main.pdf` — compiled output (committed).
- `lit_foundation.md` — 11K-word literature scan that grounded the drafting.

## Local build (recommended)

One-time setup of the two binaries (both single-file, no installer):

1. **tectonic** — XeTeX-based engine that downloads packages on demand.
   Grab `tectonic-X.Y.Z-x86_64-pc-windows-msvc.zip` from
   <https://github.com/tectonic-typesetting/tectonic/releases> and unzip
   to `~/bin/tectonic/tectonic.exe`.

2. **biber 2.17** — must match tectonic's bundled `biblatex` 3.17 (which
   produces `bcf` v3.8). Newer biber versions will fail with a
   "control file version mismatch" error. Download from
   <https://sourceforge.net/projects/biblatex-biber/files/biblatex-biber/2.17/binaries/Windows/biber-MSWIN64.zip>
   and unzip to `~/bin/biber.exe`.

3. **Python deps** — `pip install svglib reportlab pypdf` (pure-Python
   SVG→PDF converter; no Cairo dependency).

Then build:

```sh
python build_paper.py
```

Output: `main.pdf` (≈190 KiB, 36 pages).

To force re-conversion of all SVGs even if PDFs are current:

```sh
python build_paper.py --force-svg
```

To switch the source back to `\includesvg{X.svg}` (for SVG-direct
Overleaf compile):

```sh
python build_paper.py --swap-to-svg
# then manually un-comment \usepackage{svg} in main.tex
```

## Overleaf build (alternative)

1. Zip everything in this directory (`outputs/paper/`).
2. Upload to Overleaf as a new project ("New Project" → "Upload Project").
3. Set compiler to **pdfLaTeX** and bibliography backend to **Biber**
   (Menu → Settings → Compiler / TeX Live version recent enough for
   `biblatex-chicago`).
4. Compile. The figures are already PDFs so `\includegraphics` works
   without Inkscape. (If you prefer SVG-direct compilation, run
   `python build_paper.py --swap-to-svg` first and uncomment
   `\usepackage{svg}` in the preamble.)

## Local rebuild of figures + tables (from upstream pipelines)

```sh
python build_paper_assets.py
```

This copies the relevant figures from `outputs/{policy}_*` into
`figures/` and regenerates `tables/*.tex` from the corresponding
output CSVs. Re-run after any pipeline change, then re-run
`build_paper.py` to rebuild the PDF.

## Style

- Body 12pt, 1.5 spacing, 1-inch margins
- Chicago author-date in-text citations (`\citep`, `\citet`)
- Specific page references via `\citepg{key}{42}` (custom macro)
- Tables in `threeparttable` for table notes
- Figures via `\includegraphics`; subfigures via `subcaption`
