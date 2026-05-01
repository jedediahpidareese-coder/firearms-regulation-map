"""Local PDF build for the working paper.

Tectonic (XeTeX-based, single binary) compiles main.tex to main.pdf with
all packages downloaded on demand and biber called externally for the
Chicago author-date bibliography.

Pre-requisites (one-time setup, all installable to ~/bin):
  - tectonic.exe   from https://github.com/tectonic-typesetting/tectonic/releases
  - biber.exe      v2.17 (matches tectonic's bundled biblatex 3.17 -> bcf 3.8)
                   from https://sourceforge.net/projects/biblatex-biber/
  - Python 3.10+ with `svglib` and `reportlab` (`pip install svglib reportlab`)

Build steps performed by this script:
  1. Convert every figures/*.svg to figures/*.pdf via svglib (pure-Python,
     no Cairo dep). Skips already-current PDFs.
  2. Run tectonic with biber on PATH. Tectonic handles the multi-pass
     LaTeX-biber-LaTeX-LaTeX cycle automatically.
  3. Report final main.pdf path, page count, and any non-trivial warnings.

main.tex itself uses \\includegraphics{figures/X.pdf} so it compiles
identically on Overleaf if the .pdf figures are uploaded alongside the
.svg sources. To compile direct from .svg on Overleaf (using the `svg`
LaTeX package + Inkscape), uncomment the `\\usepackage{svg}` line in
main.tex and run `swap_to_includesvg()` below.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PAPER_DIR = Path(__file__).parent.resolve()
FIG_DIR = PAPER_DIR / "figures"
MAIN_TEX = PAPER_DIR / "main.tex"
MAIN_PDF = PAPER_DIR / "main.pdf"


# --------------------------------------------------------------------- #
# Step 1: SVG -> PDF (svglib is pure-Python, doesn't need Cairo)
# --------------------------------------------------------------------- #

def svg_to_pdf(svg_path: Path, pdf_path: Path) -> None:
    """Convert one SVG to PDF using svglib + reportlab."""
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF

    drawing = svg2rlg(str(svg_path))
    renderPDF.drawToFile(drawing, str(pdf_path))


def convert_svgs(force: bool = False) -> int:
    """Convert all figures/*.svg to figures/*.pdf if missing or stale.

    Returns the number of files actually converted.
    """
    n = 0
    for svg in sorted(FIG_DIR.glob("*.svg")):
        pdf = svg.with_suffix(".pdf")
        if not force and pdf.exists() and pdf.stat().st_mtime >= svg.stat().st_mtime:
            print(f"  skip  {svg.name} (PDF current)")
            continue
        svg_to_pdf(svg, pdf)
        print(f"  conv  {svg.name} -> {pdf.name} ({pdf.stat().st_size} B)")
        n += 1
    return n


# --------------------------------------------------------------------- #
# Step 2: tectonic
# --------------------------------------------------------------------- #

def find_tectonic() -> str:
    """Locate the tectonic binary."""
    for candidate in [
        shutil.which("tectonic"),
        os.path.expanduser("~/bin/tectonic/tectonic.exe"),
        os.path.expanduser("~/bin/tectonic.exe"),
    ]:
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit(
        "ERROR: tectonic.exe not found on PATH or in ~/bin/. "
        "Download from https://github.com/tectonic-typesetting/tectonic/releases."
    )


def find_biber_dir() -> str | None:
    """Locate biber.exe's directory so we can put it on PATH for tectonic."""
    for candidate in [
        shutil.which("biber"),
        os.path.expanduser("~/bin/biber.exe"),
    ]:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).parent)
    return None


def run_tectonic() -> None:
    tectonic = find_tectonic()
    biber_dir = find_biber_dir()
    if biber_dir is None:
        print(
            "WARNING: biber.exe not found. tectonic will fail at the "
            "bibliography step. Download biber 2.17 from "
            "https://sourceforge.net/projects/biblatex-biber/"
        )

    env = os.environ.copy()
    if biber_dir:
        env["PATH"] = biber_dir + os.pathsep + env.get("PATH", "")

    cmd = [tectonic, "-X", "compile", str(MAIN_TEX)]
    print(f"\n>>> {' '.join(cmd)}")
    proc = subprocess.run(
        cmd, cwd=PAPER_DIR, env=env, capture_output=True, text=True
    )

    # tectonic writes most output to stderr; print it
    if proc.stderr:
        # filter to errors/warnings only, drop "downloading X" noise
        for line in proc.stderr.splitlines():
            if line.startswith("note: downloading "):
                continue
            if "Fontconfig error" in line:
                continue  # benign on Windows
            print(line)

    if proc.returncode != 0:
        print(f"\nERROR: tectonic exited with code {proc.returncode}")
        sys.exit(proc.returncode)


# --------------------------------------------------------------------- #
# Step 3: report
# --------------------------------------------------------------------- #

def report() -> None:
    if not MAIN_PDF.exists():
        sys.exit("ERROR: main.pdf was not produced.")
    size_kb = MAIN_PDF.stat().st_size / 1024
    page_count: int | None = None
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(str(MAIN_PDF))
        page_count = len(reader.pages)
    except ImportError:
        pass
    print(f"\nOK  main.pdf  ({size_kb:.1f} KiB"
          + (f", {page_count} pages" if page_count else "") + ")")


# --------------------------------------------------------------------- #
# Optional: switch back to \includesvg for SVG-direct Overleaf compile
# --------------------------------------------------------------------- #

def swap_to_includesvg() -> None:
    """Restore \\includesvg{X.svg} from \\includegraphics{X.pdf} in main.tex.

    Use this if you want main.tex to compile directly from SVG on Overleaf
    (which has Inkscape pre-installed). After running, also un-comment
    \\usepackage{svg} in the preamble manually.
    """
    import re

    txt = MAIN_TEX.read_text(encoding="utf-8")
    new, n = re.subn(
        r"\\includegraphics(\[[^\]]*\])?\{(figures/[A-Za-z0-9_]+)\.pdf\}",
        r"\\includesvg\1{\2.svg}",
        txt,
    )
    MAIN_TEX.write_text(new, encoding="utf-8")
    print(f"Swapped {n} \\includegraphics with \\includesvg.")
    print("Reminder: also un-comment \\usepackage{svg} in the preamble.")


# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #

def main() -> None:
    if "--swap-to-svg" in sys.argv:
        swap_to_includesvg()
        return

    print("=== Step 1: SVG -> PDF ===")
    convert_svgs(force="--force-svg" in sys.argv)

    print("\n=== Step 2: tectonic compile ===")
    run_tectonic()

    print("\n=== Step 3: report ===")
    report()


if __name__ == "__main__":
    main()
