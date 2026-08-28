"""
scripts/generate_ablation_report.py — Build the cross-condition comparison report.

Reads results.csv from each condition directory under --data-dir, computes the
standard metrics via analysis/metrics.py (no metric logic is duplicated here),
generates the comparison figures via analysis/plots.py, and writes one markdown
report with side-by-side tables.

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_ablation_report.py \
        --data-dir data/immigration \
        --output reports/full_ablation_comparison.md \
        --figures-dir reports/figures

Requires results.csv to exist for at least one condition under
data-dir/{condition}/results.csv. Conditions with no results.csv are skipped
and listed as pending in the report, not treated as an error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
LABEL_ORDER = ["Strongly Against", "Against", "Neutral", "In Favor", "Strongly In Favor"]


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

    first_day_dist = traj.iloc[0] if len(traj) else None
    last_day_dist = traj.iloc[-1] if len(traj) else None

    left_labels = ["Strongly Against", "Against"]
    left_start = float(sum(first_day_dist.get(l, 0.0) for l in left_labels)) if first_day_dist is not None else None
    left_end = float(sum(last_day_dist.get(l, 0.0) for l in left_labels)) if last_day_dist is not None else None

    return {
        "n_days": n_days,
        "n_rows": n_rows,
        "entropy_start": float(entropy.iloc[0]) if len(entropy) else None,
        "entropy_end": float(entropy.iloc[-1]) if len(entropy) else None,
        "left_share_start": left_start,
        "left_share_end": left_end,
        "eff_clusters_end": float(eff_clusters.iloc[-1]) if len(eff_clusters) else None,
        "accept_by_dist": accept_by_dist,
    }


def build_report(data_dir: Path, figures_dir: Path) -> str:
    summaries: dict[str, dict] = {}
    missing: list[str] = []

    for cond in CONDITIONS:
        df = load_condition(data_dir, cond)
        if df is None:
            missing.append(cond)
            continue
        summaries[cond] = summarize_condition(df)

    lines: list[str] = []
    lines.append("# Full ablation comparison")
    lines.append("")
    lines.append(f"Conditions present: {', '.join(summaries) if summaries else 'none'}")
    if missing:
        lines.append(f"Conditions pending: {', '.join(missing)}")
    lines.append("")

    if not summaries:
        lines.append("No results.csv found under any condition directory yet. Nothing to report.")
        return "\n".join(lines)

    # ── Summary table ──────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    lines.append("| Condition | Days | Rows | Entropy start | Entropy end | Left-leaning start | Left-leaning end | Effective clusters (end) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for cond, s in summaries.items():
        lines.append(
            f"| {CONDITION_LABELS.get(cond, cond)} "
            f"| {s['n_days']} | {s['n_rows']} "
            f"| {s['entropy_start']:.4f} | {s['entropy_end']:.4f} "
            f"| {s['left_share_start']*100:.1f}% | {s['left_share_end']*100:.1f}% "
            f"| {s['eff_clusters_end']:.2f} |"
        )
    lines.append("")

    # ── Acceptance by distance, one column per condition ────────────────────
    lines.append("## Acceptance rate by stance distance")
    lines.append("")
    all_dists = sorted(set().union(*[s["accept_by_dist"].index.tolist() for s in summaries.values()]))
    header = "| Distance | " + " | ".join(CONDITION_LABELS.get(c, c) for c in summaries) + " |"
    sep = "|---|" + "---|" * len(summaries)
    lines.append(header)
    lines.append(sep)
    for d in all_dists:
        row = [f"| {d} "]
        for cond, s in summaries.items():
            val = s["accept_by_dist"].get(d)
            row.append(f"| {val*100:.1f}%" if val is not None else "| n/a")
        row.append(" |")
        lines.append("".join(row))
    lines.append("")

    # ── Figures ───────────────────────────────────────────────────────────
    lines.append("## Figures")
    lines.append("")
    lines.append(f"Generated under `{figures_dir}/` by `analysis/plots.py`:")
    lines.append("")
    for fname in [
        "compare_trajectories.png",
        "compare_entropy.png",
        "compare_acceptance_distance.png",
        "compare_effective_clusters.png",
        "compare_acceptance_matrix.png",
        "compare_transition_matrix.png",
    ]:
        if (figures_dir / fname).exists():
            lines.append(f"- `{fname}`")
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append("Not written here. Read the numbers above against the hypothesis before drawing")
    lines.append("conclusions — this report only computes and tabulates, it does not interpret.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the cross-condition ablation report.")
    parser.add_argument("--data-dir", required=True, help="Directory containing condition subdirs")
    parser.add_argument("--output", required=True, help="Path to write the markdown report")
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

    report = build_report(data_dir, figures_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
