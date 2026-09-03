"""
scripts/report_common.py: shared PDF page-building helpers for the two
ablation report scripts (generate_results_pdf.py and
generate_explanation_doc.py). No metric logic lives here, only rendering.

Importing this module (or analysis.plots, which this also imports) applies
the project's seaborn publication theme globally via analysis/plots.py, so
any matplotlib figure created after the import inherits it.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

import analysis.plots  # noqa: F401,E402  (import applies the seaborn theme as a side effect)

TOP_Y = 0.90
BOTTOM_Y = 0.07
LINE_STEP = 0.026
BLANK_STEP = 0.018
FONT_FAMILY = "serif"


def text_pages(pdf: PdfPages, title: str, body_lines: list[str]) -> None:
    """Paginate body_lines across as many pages as needed. Each logical line
    in body_lines is wrapped to the page width first, preserving a leading-
    space indent (used for numbered/lettered sub-points) as a hanging indent
    on wrapped continuation lines."""
    wrapped_lines: list[str] = []
    for line in body_lines:
        if line == "":
            wrapped_lines.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")
        hang = indent + 3 if stripped[:2].rstrip(".").isdigit() else indent
        wrapped_lines.extend(
            textwrap.wrap(
                stripped,
                width=90,
                initial_indent=" " * indent,
                subsequent_indent=" " * hang,
            )
            or [""]
        )

    pages: list[list[str]] = []
    current: list[str] = []
    y = TOP_Y
    for w in wrapped_lines:
        step = BLANK_STEP if w == "" else LINE_STEP
        if y - step < BOTTOM_Y:
            pages.append(current)
            current = []
            y = TOP_Y
        current.append(w)
        y -= step
    if current:
        pages.append(current)
    if not pages:
        pages = [[]]

    for i, page_lines in enumerate(pages):
        fig = plt.figure(figsize=(8.5, 11))
        page_title = title if i == 0 else f"{title} (continued)"
        fig.text(0.08, 0.95, page_title, fontsize=15, fontweight="bold",
                  va="top", family=FONT_FAMILY)
        y = TOP_Y
        for w in page_lines:
            step = BLANK_STEP if w == "" else LINE_STEP
            if w != "":
                weight = "bold" if w and not w.startswith(" ") and w.isupper() else "normal"
                fig.text(0.08, y, w, fontsize=10, va="top", family=FONT_FAMILY, weight=weight)
            y -= step
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)


def table_page(pdf: PdfPages, title: str, col_labels: list[str], rows: list[list[str]],
                col_widths: list[float] | None = None, figsize: tuple[float, float] | None = None) -> None:
    n_rows = max(len(rows), 1)
    fig, ax = plt.subplots(figsize=figsize or (12, 3.5 + 0.5 * n_rows))
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=20, family=FONT_FAMILY)

    kwargs = dict(cellText=rows, colLabels=col_labels, loc="center", cellLoc="center")
    if col_widths:
        kwargs["colWidths"] = col_widths
    table = ax.table(**kwargs)
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.2)
    pdf.savefig(fig)
    plt.close(fig)


def figure_page(pdf: PdfPages, image_path: Path, caption: str, title: str | None = None) -> None:
    import matplotlib.image as mpimg

    img = mpimg.imread(image_path)
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.imshow(img)
    ax.axis("off")
    fig.suptitle(title or image_path.name, fontsize=11, fontweight="bold", y=0.98, family=FONT_FAMILY)
    wrapped = textwrap.wrap(caption, width=110)
    fig.text(0.06, 0.03, "\n".join(wrapped), fontsize=9, va="bottom", family=FONT_FAMILY)
    pdf.savefig(fig)
    plt.close(fig)
