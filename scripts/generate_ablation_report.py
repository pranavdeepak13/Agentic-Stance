"""
scripts/generate_ablation_report.py — Build the cross-condition comparison report as a PDF.

Reads results.csv from each condition directory under --data-dir, computes the
standard metrics via analysis/metrics.py (no metric logic is duplicated here),
and writes a single multi-page PDF: a plain-language explanation of what was
measured and how to read it, a summary table, an acceptance-by-distance table,
then one page per comparison figure (reusing analysis/plots.py's comparison
functions, which already write PNGs to --figures-dir).

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_ablation_report.py \
        --data-dir data/immigration \
        --output reports/full_ablation_comparison.pdf \
        --figures-dir reports/figures

Requires results.csv to exist for at least one condition under
data-dir/{condition}/results.csv. Conditions with no results.csv are skipped
and listed as pending in the PDF, not treated as an error.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from analysis.metrics import compute_all_metrics  # noqa: E402
from analysis.plots import compare_conditions, compare_acceptance_matrix, compare_transition_matrix, compare_effective_clusters  # noqa: E402

CONDITIONS = ["no_kg", "general_only", "tom_only", "full_kg"]
CONDITION_LABELS = {
    "no_kg": "No memory",
    "general_only": "General facts",
    "tom_only": "Theory of mind",
    "full_kg": "Full KG",
}

FIGURE_EXPLANATIONS = {
    "compare_trajectories.png": "Raw stance distribution over time, one panel per condition. Shows directional drift directly: watch whether one color grows steadily at the expense of the others.",
    "compare_entropy.png": "Population diversity over time, one line per condition. A condition that stays higher keeps opinions more spread out; a condition that drops fastest is converging toward consensus fastest.",
    "compare_acceptance_distance.png": "The central test. Each line shows how likely an agent is to shift toward its partner's stance, as a function of how far apart the two started. A flatter line means that condition resists agreement with distant partners more than the baseline does.",
    "compare_effective_clusters.png": "Estimated number of distinct opinion groups still present at the end of the run, per condition. Near 1 means the population converged to one view; near 5 means it stayed spread across the full scale.",
    "compare_acceptance_matrix.png": "Full pairwise detail behind the acceptance rate: probability of accepting a shift, broken down by the agent's own stance and the partner's stance, not just the distance between them.",
    "compare_transition_matrix.png": "Full pairwise detail on where agents actually ended up: probability of moving from each starting stance to each ending stance, per condition.",
}


def load_condition(data_dir: Path, condition: str) -> pd.DataFrame | None:
    csv_path = data_dir / condition / "results.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def summarize_condition(df: pd.DataFrame) -> dict:
    metrics = compute_all_metrics(df)
    entropy = metrics["entropy"]
    traj = metrics["trajectory"]
    accept_by_dist = metrics["acceptance_by_distance"]
    eff_clusters = metrics["effective_clusters"]

    n_days = int(df["iteration"].max())
    n_rows = len(df)
    hourly_schema = "exchange_id" in df.columns

    first_day_dist = traj.iloc[0] if len(traj) else None
    last_day_dist = traj.iloc[-1] if len(traj) else None

    left_labels = ["Strongly Against", "Against"]
    left_start = float(sum(first_day_dist.get(l, 0.0) for l in left_labels)) if first_day_dist is not None else None
    left_end = float(sum(last_day_dist.get(l, 0.0) for l in left_labels)) if last_day_dist is not None else None

    return {
        "n_days": n_days,
        "n_rows": n_rows,
        "hourly_schema": hourly_schema,
        "entropy_start": float(entropy.iloc[0]) if len(entropy) else None,
        "entropy_end": float(entropy.iloc[-1]) if len(entropy) else None,
        "left_share_start": left_start,
        "left_share_end": left_end,
        "eff_clusters_end": float(eff_clusters.iloc[-1]) if len(eff_clusters) else None,
        "accept_by_dist": accept_by_dist,
    }


# ── PDF page builders ──────────────────────────────────────────────────────

TOP_Y = 0.88
BOTTOM_Y = 0.07
LINE_STEP = 0.026
BLANK_STEP = 0.018


def _text_page(pdf: PdfPages, title: str, body_lines: list[str]) -> None:
    """Paginate body_lines across as many pages as needed, wrapping each
    logical line to the page width first so the line budget is accurate."""
    wrapped_lines: list[str] = []
    for line in body_lines:
        if line == "":
            wrapped_lines.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        hang = indent + 3 if line.lstrip(" ")[:2].rstrip(".").isdigit() else indent
        wrapped_lines.extend(
            textwrap.wrap(
                line.strip(),
                width=92,
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
        fig.text(0.08, 0.94, page_title, fontsize=15, fontweight="bold", va="top")
        y = TOP_Y
        for w in page_lines:
            step = BLANK_STEP if w == "" else LINE_STEP
            if w != "":
                fig.text(0.08, y, w, fontsize=10, va="top")
            y -= step
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)


def _procedure_page(pdf: PdfPages, present: list[str], missing: list[str], summaries: dict) -> None:
    any_hourly = any(s.get("hourly_schema") for s in summaries.values())
    sample = next(iter(summaries.values())) if summaries else None

    cadence_lines = []
    if any_hourly and sample:
        cadence_lines = [
            "Exchange cadence in this run",
            "",
            f"Each agent now exchanges once per hour, not once per day: {sample['n_rows']:,}",
            f"rows over {sample['n_days']} days works out to 140 agents x 24 hours x",
            f"{sample['n_days']} days. The original 'iteration' column in the raw file was",
            "a running exchange counter, not a day index. This report reindexes it to",
            "the day number (iteration = day_id) before computing entropy, left-leaning",
            "share, and effective clusters, so those three numbers describe a full-day",
            "population snapshot, not a single hourly exchange. Acceptance rate by",
            "stance distance and the transition/acceptance matrices are computed on",
            "every hourly exchange directly, since those are about individual",
            "conversations, not population state, and using every exchange gives more",
            "statistical power rather than less.",
            "",
        ]

    lines = [
        f"Conditions included: {', '.join(CONDITION_LABELS.get(c, c) for c in present) if present else 'none yet'}",
        f"Conditions pending: {', '.join(CONDITION_LABELS.get(c, c) for c in missing)}" if missing else "",
        "",
        *cadence_lines,
        "What this report measures",
        "",
        "Each condition ran the same 140-agent population through the same",
        "simulation length, differing only in what memory the agents carry",
        "between conversations. Every exchange between two agents is logged",
        "as one row: who talked to whom, what each believed before, and what",
        "each believed after. This report reads those rows and computes four",
        "things, per condition:",
        "",
        "  1. Entropy: how spread out opinions are across the population on a",
        "     given day. High means diverse, low means the population is",
        "     converging on one view. Reported at the first and last day.",
        "",
        "  2. Left-leaning share: percent of the population holding a LEFT or",
        "     FAR LEFT stance, at the start and end. This tracks directional",
        "     drift specifically, separate from overall diversity.",
        "",
        "  3. Effective clusters: an estimate of how many distinct opinion",
        "     groups remain at the end. Near 1 means everyone converged to",
        "     roughly the same view. Near 5 means the population stayed",
        "     spread across the full range.",
        "",
        "  4. Acceptance rate by stance distance: the probability an agent",
        "     shifts toward its partner's stance, split out by how far apart",
        "     the two agents started. This is the main test in this project:",
        "     if memory reduces agreement bias, this rate should fall off",
        "     faster as distance increases, compared to the no-memory",
        "     condition.",
        "",
        "How to read the tables and figures that follow",
        "",
        "The summary table gives one row per condition with the four numbers",
        "above. The acceptance table breaks the fourth number out by exact",
        "stance distance, one column per condition, so the shapes of the",
        "curves can be compared directly. The figure pages after that show",
        "the same information as plots, which is usually the fastest way to",
        "spot a difference between conditions.",
        "",
        "This report only computes and tabulates. It does not state whether",
        "the hypothesis is supported. Comparing these numbers against the",
        "hypothesis criteria is a separate, deliberate step, done by reading",
        "paper/context/hypothesis_and_scope.md alongside this report.",
    ]
    _text_page(pdf, "Full ablation comparison — how this analysis works", lines)


def _summary_table_page(pdf: PdfPages, summaries: dict) -> None:
    fig, ax = plt.subplots(figsize=(12, 4 + 0.5 * len(summaries)))
    ax.axis("off")
    ax.set_title("Summary", fontsize=14, fontweight="bold", loc="left", pad=20)

    col_labels = ["Condition", "Days", "Rows", "Entropy\nstart", "Entropy\nend",
                  "Left\nstart", "Left\nend", "Eff. clusters\n(end)"]
    col_widths = [0.16, 0.08, 0.09, 0.12, 0.12, 0.11, 0.11, 0.14]
    rows = []
    for cond, s in summaries.items():
        rows.append([
            CONDITION_LABELS.get(cond, cond),
            str(s["n_days"]),
            str(s["n_rows"]),
            f"{s['entropy_start']:.4f}",
            f"{s['entropy_end']:.4f}",
            f"{s['left_share_start']*100:.1f}%",
            f"{s['left_share_end']*100:.1f}%",
            f"{s['eff_clusters_end']:.2f}",
        ])

    table = ax.table(cellText=rows, colLabels=col_labels, colWidths=col_widths, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.4)
    pdf.savefig(fig)
    plt.close(fig)


def _acceptance_table_page(pdf: PdfPages, summaries: dict) -> None:
    all_dists = sorted(set().union(*[s["accept_by_dist"].index.tolist() for s in summaries.values()]))
    fig, ax = plt.subplots(figsize=(11, 2 + 0.4 * len(all_dists)))
    ax.axis("off")
    ax.set_title("Acceptance rate by stance distance", fontsize=14, fontweight="bold", loc="left", pad=20)

    col_labels = ["Distance"] + [CONDITION_LABELS.get(c, c) for c in summaries]
    rows = []
    for d in all_dists:
        row = [str(d)]
        for cond, s in summaries.items():
            val = s["accept_by_dist"].get(d)
            row.append(f"{val*100:.1f}%" if val is not None else "n/a")
        rows.append(row)

    table = ax.table(cellText=rows, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    pdf.savefig(fig)
    plt.close(fig)


def _figure_pages(pdf: PdfPages, figures_dir: Path) -> None:
    for fname, explanation in FIGURE_EXPLANATIONS.items():
        fpath = figures_dir / fname
        if not fpath.exists():
            continue
        img = plt.imread(fpath)
        fig, ax = plt.subplots(figsize=(11, 9))
        ax.imshow(img)
        ax.axis("off")
        fig.suptitle(fname, fontsize=11, fontweight="bold", y=0.98)
        wrapped = textwrap.wrap(explanation, width=110)
        fig.text(0.06, 0.03, "\n".join(wrapped), fontsize=9, va="bottom")
        pdf.savefig(fig)
        plt.close(fig)


def build_pdf(data_dir: Path, figures_dir: Path, out_path: Path) -> None:
    summaries: dict[str, dict] = {}
    missing: list[str] = []

    for cond in CONDITIONS:
        df = load_condition(data_dir, cond)
        if df is None:
            missing.append(cond)
            continue
        summaries[cond] = summarize_condition(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(out_path) as pdf:
        _procedure_page(pdf, list(summaries.keys()), missing, summaries)

        if not summaries:
            _text_page(pdf, "No data yet", ["No results.csv found under any condition directory."])
            return

        _summary_table_page(pdf, summaries)
        _acceptance_table_page(pdf, summaries)
        _figure_pages(pdf, figures_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the cross-condition ablation report as a PDF.")
    parser.add_argument("--data-dir", required=True, help="Directory containing condition subdirs")
    parser.add_argument("--output", required=True, help="Path to write the PDF report")
    parser.add_argument("--figures-dir", required=True, help="Directory for comparison figures")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    figures_dir = Path(args.figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    present = [c for c in CONDITIONS if (data_dir / c / "results.csv").exists()]
    if len(present) >= 2:
        compare_conditions(data_dir, figures_dir)
        compare_effective_clusters(data_dir, figures_dir)
        compare_acceptance_matrix(data_dir, figures_dir)
        compare_transition_matrix(data_dir, figures_dir)
    elif present:
        print(f"Only one condition present ({present[0]}) — skipping comparison figures, need at least 2.")
    else:
        print(f"No results.csv found under {data_dir}/ yet.")

    out_path = Path(args.output)
    build_pdf(data_dir, figures_dir, out_path)
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
