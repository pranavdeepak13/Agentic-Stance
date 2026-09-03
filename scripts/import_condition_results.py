"""
scripts/import_condition_results.py: import raw results CSVs delivered by a
collaborator into the pipeline's expected data/{topic}/{condition}/results.csv
layout, correcting for a schema change: the DGX run now logs one exchange per
agent per HOUR (not per day), so the raw `iteration` column is a fine-grained
exchange counter (up to n_agents * 24 * n_days), not the day index every other
tool in this repo assumes it to be.

This script:
  1. Matches filenames in --results-dir to the four conditions (case-insensitive,
     tolerant of spaces/underscores: "No KG Results.csv" -> no_kg).
  2. If the file has day_id/hour_id columns (the new schema), preserves the
     original fine-grained counter as `exchange_id` and overwrites `iteration`
     with `day_id`, so every downstream tool (analysis/metrics.py,
     analysis/plots.py, generate_ablation_report.py) sees `iteration` as a day
     index the way it always has, with zero changes needed to that code.
  3. Writes the result to data/{topic}/{condition}/results.csv.

Files without day_id/hour_id (the old schema) are copied through unchanged.

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/import_condition_results.py \
        --results-dir results \
        --data-dir data/immigration
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

CONDITION_PATTERNS = {
    "no_kg": re.compile(r"no[\s_-]*kg", re.IGNORECASE),
    "general_only": re.compile(r"general[\s_-]*only", re.IGNORECASE),
    "tom_only": re.compile(r"tom[\s_-]*only", re.IGNORECASE),
    "full_kg": re.compile(r"full[\s_-]*kg", re.IGNORECASE),
}


def match_condition(filename: str) -> str | None:
    for condition, pattern in CONDITION_PATTERNS.items():
        if pattern.search(filename):
            return condition
    return None


def import_one(csv_path: Path, condition: str, data_dir: Path) -> dict:
    df = pd.read_csv(csv_path)
    had_hourly_schema = "day_id" in df.columns and "hour_id" in df.columns

    if had_hourly_schema:
        df = df.rename(columns={"iteration": "exchange_id"})
        df.insert(0, "iteration", df["day_id"])

    out_dir = data_dir / condition
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.csv"

    overwritten_rows = None
    if out_path.exists():
        try:
            overwritten_rows = len(pd.read_csv(out_path, usecols=[0]))
        except Exception:
            overwritten_rows = -1  # existing file unreadable; still flag it
        print(f"Warning: {out_path} already exists ({overwritten_rows} rows), overwriting with {len(df)} rows from {csv_path}")

    df.to_csv(out_path, index=False)

    return {
        "condition": condition,
        "source": str(csv_path),
        "dest": str(out_path),
        "rows": len(df),
        "overwritten_rows": overwritten_rows,
        "hourly_schema": had_hourly_schema,
        "days": int(df["day_id"].max()) if had_hourly_schema else int(df["iteration"].max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import collaborator-delivered results CSVs into the pipeline layout.")
    parser.add_argument("--results-dir", required=True, help="Directory containing the raw delivered CSVs")
    parser.add_argument("--data-dir", required=True, help="Destination, e.g. data/immigration")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    data_dir = Path(args.data_dir)

    csv_files = sorted(results_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found under {results_dir}/")
        return

    imported = []
    unmatched = []
    for csv_path in csv_files:
        condition = match_condition(csv_path.stem)
        if condition is None:
            unmatched.append(csv_path.name)
            continue
        summary = import_one(csv_path, condition, data_dir)
        imported.append(summary)

    print(f"{'Condition':<16} {'Rows':>8}  {'Days':>5}  {'Schema':<10}  Source")
    for s in imported:
        schema = "hourly" if s["hourly_schema"] else "legacy"
        print(f"{s['condition']:<16} {s['rows']:>8}  {s['days']:>5}  {schema:<10}  {s['source']}")

    if unmatched:
        print(f"\nUnmatched files (skipped, matched no condition): {', '.join(unmatched)}")

    matched_conditions = {s["condition"] for s in imported}
    missing_conditions = set(CONDITION_PATTERNS) - matched_conditions
    if missing_conditions:
        print(f"\nWarning: no file matched for: {', '.join(sorted(missing_conditions))}. "
              f"The downstream report will list these as pending, not as an error, "
              f"confirm that is actually intended before treating the import as complete.")

    if unmatched or missing_conditions:
        sys.exit(1)


if __name__ == "__main__":
    main()
