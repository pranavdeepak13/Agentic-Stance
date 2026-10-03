"""
scripts/compute_paper_numbers.py: recompute, from the four DGX-delivered CSVs
under results/, every population-level number the paper cites that this repo
can reproduce itself. Output is a markdown block on stdout, pasted into
reports/full_ablation_summary.md (section "Reproducible from this repo").

Definitions follow analysis/metrics.py (Cau et al. 2025): entropy in bits over
the five Likert labels, effective clusters C = 1 / sum(p_i^2), acceptance =
the scored agent moved strictly toward the partner's pre-exchange stance.
Population snapshots use each agent's most recent stance_after as of the end
of a day, vectorised here because metrics.py iterates row by row and is slow
on 100,800 rows per condition.

Usage:
    .venv/bin/python -B scripts/compute_paper_numbers.py --results-dir results --bootstrap
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

FILES = {
    "no_kg": "No KG Results.csv",
    "general_only": "General Only Results.csv",
    "tom_only": "Tom Only Results.csv",
    "full_kg": "Full KG Results.csv",
}
SCORES = [-2, -1, 0, 1, 2]
LABELS = {-2: "SA", -1: "A", 0: "N", 1: "F", 2: "SF"}


def long_form(df: pd.DataFrame) -> pd.DataFrame:
    """One row per scored agent per exchange: (seq, day, agent, before, after, partner_before)."""
    parts = []
    for me, other in (("a", "b"), ("b", "a")):
        parts.append(pd.DataFrame({
            "seq": df["iteration"] * 2 + (0 if me == "a" else 1),
            "day": df["day_id"],
            "agent": df[f"agent_{me}_id"],
            "before": df[f"agent_{me}_stance_before_score"],
            "after": df[f"agent_{me}_stance_after_score"],
            "partner": df[f"agent_{other}_stance_before_score"],
        }))
    return pd.concat(parts).sort_values("seq").reset_index(drop=True)


def distribution_at_end_of(lf: pd.DataFrame, initial: pd.Series, day: int) -> pd.Series:
    last = lf[lf["day"] <= day].groupby("agent")["after"].last()
    state = initial.copy()
    state.loc[last.index] = last
    return state.value_counts().reindex(SCORES, fill_value=0)


def entropy_bits(counts: pd.Series) -> float:
    p = counts / counts.sum()
    return float(-sum(x * math.log2(x) for x in p if x > 0))


def clusters(counts: pd.Series) -> float:
    p = counts / counts.sum()
    return float(1.0 / (p ** 2).sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, default=Path("results"))
    ap.add_argument("--bootstrap", action="store_true", help="also print agent-clustered bootstrap intervals")
    args = ap.parse_args()

    for cond, fname in FILES.items():
        df = pd.read_csv(args.results_dir / fname)
        lf = long_form(df)
        initial = lf.groupby("agent")["before"].first()
        n_days = int(df["day_id"].max())

        print(f"\n### {cond}\n")
        per_hour = df.groupby(["day_id", "hour_id"])
        print(f"- rows (exchanges): {len(df)}; days {df['day_id'].min()}..{n_days}; "
              f"hours {df['hour_id'].min()}..{df['hour_id'].max()}")
        print(f"- exchanges per (day, hour): min {per_hour.size().min()}, max {per_hour.size().max()}")
        uniq = per_hour["agent_a_id"].nunique()
        print(f"- distinct initiators per (day, hour): min {uniq.min()}, max {uniq.max()}")
        print(f"- n_turns range: {df['n_turns'].min()}..{df['n_turns'].max()}, mean {df['n_turns'].mean():.3f}")

        d0 = initial.value_counts().reindex(SCORES, fill_value=0)
        rows = []
        for d in [0, 1, 5, 10, 15, 20, 25, n_days]:
            c = d0 if d == 0 else distribution_at_end_of(lf, initial, d)
            rows.append((d, c))
        print("\n| End of day | SA | A | N | F | SF | Against side | In Favor side | H (bits) | C |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for d, c in rows:
            print(f"| {d} | " + " | ".join(str(int(c[s])) for s in SCORES)
                  + f" | {int(c[-2] + c[-1])} | {int(c[1] + c[2])} | {entropy_bits(c):.4f} | {clusters(c):.3f} |")

        # daily series for mean-over-run statistics
        daily = [distribution_at_end_of(lf, initial, d) for d in range(1, n_days + 1)]
        H = np.array([entropy_bits(c) for c in daily])
        C = np.array([clusters(c) for c in daily])
        print(f"\n- entropy, mean over days 1..{n_days}: {H.mean():.4f}; min {H.min():.4f}; max {H.max():.4f}")
        print(f"- effective clusters, mean over days 1..{n_days}: {C.mean():.3f}")
        mean_score = np.array([(c * pd.Series(SCORES, index=SCORES)).sum() / c.sum() for c in daily])
        print(f"- mean stance score, day 0: {(d0 * pd.Series(SCORES, index=SCORES)).sum() / 140:.3f}; "
              f"day {n_days}: {mean_score[-1]:.3f}")

        moved = (lf["after"] != lf["before"])
        print(f"- share of agent-updates with any stance change: {moved.mean():.4f} (n={len(lf)})")
        print(f"- max |after - before| observed: {int((lf['after'] - lf['before']).abs().max())}")

        # acceptance by absolute distance (toward partner)
        delta = lf["partner"] - lf["before"]
        mv = lf["after"] - lf["before"]
        acc = (mv * delta > 0)
        print("\n| abs distance | accepted | total | P(accept) |")
        print("|---|---|---|---|")
        for k in [1, 2, 3, 4]:
            m = delta.abs() == k
            print(f"| {k} | {int(acc[m].sum())} | {int(m.sum())} | {acc[m].mean():.4f} |")
        same = delta == 0
        print(f"| 0 (any move) | {int(moved[same].sum())} | {int(same.sum())} | {moved[same].mean():.4f} |")

        # per-stance movement: P(move | before)
        print("\n| before | n | P(any move) | P(move toward centre) |")
        print("|---|---|---|---|")
        for s in SCORES:
            m = lf["before"] == s
            toward_c = ((lf["after"] - lf["before"]) * (-np.sign(s)) > 0) if s != 0 else pd.Series(False, index=lf.index)
            print(f"| {LABELS[s]} | {int(m.sum())} | {moved[m].mean():.4f} | "
                  f"{(toward_c[m].mean() if s != 0 else float('nan')):.4f} |")
        n = lf[lf["before"] == 0]
        print(f"\n- Neutral outflow: P(N -> In Favor) {(n['after'] == 1).mean():.4f}, "
              f"P(N -> Against) {(n['after'] == -1).mean():.4f}")

    if args.bootstrap:
        bootstrap_acceptance(args.results_dir)
        signed_acceptance(args.results_dir)


def bootstrap_acceptance(results_dir: Path, n_boot: int = 1000, seed: int = 0) -> None:
    """Agent-clustered bootstrap (resample scored agents) for P(accept | |d|) and P(move away | |d|)."""
    rng = np.random.default_rng(seed)
    print("\n### Agent-clustered bootstrap, 95% intervals (1000 resamples of the 140 scored agents)\n")
    print("| condition | P(acc|d=1) | P(acc|d=2) | ratio d2/d1 | P(away|d=1) | P(away|d=2) | P(any move) |")
    print("|---|---|---|---|---|---|---|")
    for cond, fname in FILES.items():
        lf = long_form(pd.read_csv(results_dir / fname))
        delta = lf["partner"] - lf["before"]
        mv = lf["after"] - lf["before"]
        lf = lf.assign(d=delta.abs(), acc=(mv * delta > 0), away=(mv * delta < 0), moved=(mv != 0))
        agents = lf["agent"].unique()
        per = {}
        for k in (1, 2):
            g = lf[lf["d"] == k].groupby("agent")
            per[k] = pd.DataFrame({"acc": g["acc"].sum(), "away": g["away"].sum(), "n": g.size()}).reindex(agents, fill_value=0)
        allm = lf.groupby("agent").agg(m=("moved", "sum"), n=("moved", "size")).reindex(agents, fill_value=0)

        def stats(idx):
            a1 = per[1].iloc[idx].sum(); a2 = per[2].iloc[idx].sum(); am = allm.iloc[idx].sum()
            p1, p2 = a1["acc"] / a1["n"], a2["acc"] / a2["n"]
            return np.array([p1, p2, p2 / p1, a1["away"] / a1["n"], a2["away"] / a2["n"], am["m"] / am["n"]])

        point = stats(np.arange(len(agents)))
        boots = np.array([stats(rng.integers(0, len(agents), len(agents))) for _ in range(n_boot)])
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
        cells = [f"{p:.3f} [{l:.3f}, {h:.3f}]" for p, l, h in zip(point, lo, hi)]
        print(f"| {cond} | " + " | ".join(cells) + " |")


def signed_acceptance(results_dir: Path, n_boot: int = 1000, seed: int = 0) -> None:
    """P(accept | signed dx), dx = partner - scored agent, as in Cau et al. (2025), with agent-clustered bootstrap.

    Also reports the directional asymmetry P(A | +k) - P(A | -k) for k = 1, 2: positive values mean agents
    accept partners on the In Favor side of them more readily than partners on the Against side.
    """
    rng = np.random.default_rng(seed)
    deltas = [-4, -3, -2, -1, 1, 2, 3, 4]
    print("\n### Acceptance by signed distance dx = partner - agent (point estimate, n)\n")
    print("| condition | " + " | ".join(f"dx={d:+d}" for d in deltas) + " |")
    print("|---|" + "---|" * len(deltas))
    asym_rows = []
    for cond, fname in FILES.items():
        lf = long_form(pd.read_csv(results_dir / fname))
        dx = lf["partner"] - lf["before"]
        acc = ((lf["after"] - lf["before"]) * dx > 0)
        lf = lf.assign(dx=dx, acc=acc)
        cells = []
        for d in deltas:
            m = lf["dx"] == d
            cells.append(f"{acc[m].mean():.3f} ({int(m.sum())})")
        print(f"| {cond} | " + " | ".join(cells) + " |")

        agents = lf["agent"].unique()
        tabs = {d: lf[lf["dx"] == d].groupby("agent")["acc"].agg(["sum", "size"]).reindex(agents, fill_value=0)
                for d in (-2, -1, 1, 2)}

        def asym(idx):
            r = {d: tabs[d].iloc[idx].sum() for d in tabs}
            p = {d: r[d]["sum"] / r[d]["size"] for d in r}
            return np.array([p[1] - p[-1], p[2] - p[-2]])

        point = asym(np.arange(len(agents)))
        boots = np.array([asym(rng.integers(0, len(agents), len(agents))) for _ in range(n_boot)])
        lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
        asym_rows.append((cond, point, lo, hi))

    print("\n### Directional asymmetry, agent-clustered bootstrap 95% intervals\n")
    print("| condition | P(A|+1) - P(A|-1) | P(A|+2) - P(A|-2) |")
    print("|---|---|---|")
    for cond, p, lo, hi in asym_rows:
        print(f"| {cond} | {p[0]:+.3f} [{lo[0]:+.3f}, {hi[0]:+.3f}] | {p[1]:+.3f} [{lo[1]:+.3f}, {hi[1]:+.3f}] |")


if __name__ == "__main__":
    main()
