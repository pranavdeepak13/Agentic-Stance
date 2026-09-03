"""
scripts/generate_explanation_doc.py: build the methods/reference PDF:
how the analysis is computed, what each of the four conditions means and how
it is implemented, and a transparent note on data issues found and fixed.

This is reference material, not the results themselves. See
scripts/generate_results_pdf.py for the results and their interpretation.

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_explanation_doc.py \
        --output reports/methodology_and_conditions.pdf
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages

from report_common import text_pages


def how_this_works_page(pdf: PdfPages) -> None:
    lines = [
        "How the analysis is computed",
        "",
        "Each condition ran the same 140-agent population through the same",
        "simulation, differing only in what memory the agents carry between",
        "conversations. Every exchange between two agents is logged as one",
        "row: who talked to whom, what each believed before, and what each",
        "believed after.",
        "",
        "Exchange cadence in the delivered data",
        "",
        "Each agent exchanges once per simulated hour, not once per day:",
        "100,800 rows over 30 days works out to 140 agents x 24 hours x 30",
        "days. The raw 'iteration' column in the delivered file is a running",
        "exchange counter, not a day index. The import step",
        "(scripts/import_condition_results.py) reindexes it to the day",
        "number (iteration = day_id) before this analysis runs, preserving",
        "the original counter as 'exchange_id'.",
        "",
        "Four things get computed, per condition:",
        "",
        "  1. Entropy: how spread out opinions are across the population on",
        "     a given day. High means diverse, low means the population is",
        "     converging on one view. Computed from a full-day population",
        "     snapshot: each agent's most recent stance as of the end of",
        "     that day, not a single hourly exchange.",
        "",
        "  2. Left-leaning share: percent of the population holding a LEFT",
        "     or FAR LEFT stance, at the start and end. Tracks directional",
        "     drift specifically, separate from overall diversity. Same",
        "     day-level snapshot as entropy.",
        "",
        "  3. Effective clusters: an estimate of how many distinct opinion",
        "     groups remain at the end. Near 1 means everyone converged to",
        "     the same view. Near 5 means the population stayed spread",
        "     across the full range. Computed as 1 / sum(p_i^2), where p_i",
        "     is each stance's share of the day-level population snapshot.",
        "     This was previously computed by counting every hourly",
        "     exchange separately rather than resolving each agent to a",
        "     single end-of-day stance first; that undercounted agreement",
        "     and inflated the apparent number of clusters. Fixed before",
        "     any of the numbers in the results document were produced.",
        "",
        "  4. Acceptance rate by stance distance: the probability an agent",
        "     shifts toward its partner's stance, split out by how far",
        "     apart the two agents started. Computed on every individual",
        "     hourly exchange, not the day-level snapshot, since this is",
        "     about single conversations, not population state. Sample",
        "     sizes range from about 1,600 to 37,500 exchanges per cell for",
        "     stance distances of 1 to 3 steps; the +-4 step cells have only",
        "     17 to 45 exchanges each and should not be treated as reliable.",
        "",
        "Data verification performed before producing results",
        "",
        "Day 1 coverage: confirmed all 140 agents appear at least once on",
        "day 1 in every condition, so the first-day entropy and left-share",
        "snapshot is a complete population read, not a partial one.",
        "",
        "Row-order assumption: the day-level 'most recent stance' resolution",
        "assumes rows are already in chronological order within a day. This",
        "holds because the import step never reorders rows, but it is not",
        "independently re-verified from the sim_clock column; noted here as",
        "a documented precondition, not a proven invariant.",
    ]
    text_pages(pdf, "How this analysis works", lines)


def open_discrepancy_page(pdf: PdfPages) -> None:
    lines = [
        "Open item: exchange cadence needs source confirmation",
        "",
        "The delivered data shows an hourly exchange cadence (see previous",
        "page). This differs from the day-based, once-per-agent-per-day loop",
        "this repository's own src/simulation.py implements. Rossetti",
        "mentioned fixing 'a few minor issues' before the DGX run; the",
        "actual code diff has not been shared or pulled into this repo yet.",
        "",
        "What the data alone can confirm: within a day, hour_id runs 0",
        "through 23, and all 140 agents appear once per hour_id, in order,",
        "before the hour advances. This is consistent with a nested day/hour",
        "loop where every agent exchanges once per simulated hour, 24 times",
        "a day. This is an inference from the row shape and ordering, not a",
        "confirmed read of the actual loop structure.",
        "",
        "What is not yet known: whether CLOCK_ADVANCE_HOURS changed, whether",
        "checkpointing cadence changed to match, and whether partner",
        "selection still draws uniformly at random the way the day-based",
        "loop did. None of this affects whether the numbers in the results",
        "document are computed correctly from the data as delivered, but it",
        "does affect how the methodology section of any eventual paper",
        "should describe the loop. Ask for the diff before writing that",
        "section.",
    ]
    text_pages(pdf, "Open item: exchange cadence", lines)


def conditions_pages(pdf: PdfPages) -> None:
    md_path = Path(__file__).resolve().parent.parent / "paper" / "context" / "conditions_and_implementation.md"
    raw = md_path.read_text()

    lines: list[str] = []
    for raw_line in raw.splitlines():
        raw_line = raw_line.replace("`", "")
        if raw_line.startswith("# "):
            continue  # top-level title becomes the PDF page title instead
        if raw_line.startswith("## "):
            lines.append("")
            lines.append(raw_line[3:].upper())
            lines.append("")
        elif raw_line.startswith("### "):
            lines.append("")
            lines.append(raw_line[4:])
            lines.append("")
        else:
            lines.append(raw_line)

    text_pages(pdf, "Conditions and implementation", lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the methodology/conditions reference PDF.")
    parser.add_argument("--output", required=True, help="Path to write the PDF")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(out_path) as pdf:
        how_this_works_page(pdf)
        open_discrepancy_page(pdf)
        conditions_pages(pdf)

    print(f"Explanation doc written to {out_path}")


if __name__ == "__main__":
    main()
