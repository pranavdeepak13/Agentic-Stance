"""
analysis/plots.py: generate all analysis charts from simulation results.

Produces the same plot types as the EPJ paper (Cau et al., 2025):
  1. Opinion trajectory: proportion of agents at each stance per iteration (Figure 2 equivalent)
  2. Opinion distribution: stacked area chart of stance counts over time
  3. Acceptance matrix: heatmap of P(accept | Discussant=i, Opponent=j) (Figure 4 bottom)
  4. Acceptance by distance: P(A|Δx) line chart (Figure 4 top)
  5. Convergence metrics: entropy and σ over time
  6. Cross-condition comparison: side-by-side subplots for all four ablation conditions

Usage:
    python analysis/plots.py --data-dir data/ --output-dir data/plots/

Or import and call individual functions:
    from analysis.plots import plot_trajectory
    plot_trajectory(df, output_dir="data/plots", condition_name="no_kg")
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Prevent Python from writing .pyc / __pycache__ files.
# Must come before any project-local imports so those modules are never bytecode-cached.
sys.dont_write_bytecode = True

# Allow running as: python analysis/plots.py from the project root
sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from metrics import (
    LABEL_ORDER,
    SCORE_VALUES,
    acceptance_by_distance,
    acceptance_matrix,
    compute_all_metrics,
    effective_clusters,
    entropy,
    opinion_trajectory,
    rejection_matrix,
    std_deviation,
    transition_matrix,
)

# ── Style constants ────────────────────────────────────────────────────────────
# Diverging, colorblind-safe ramp for the five Likert stances (deep red -> deep
# blue through a neutral gray midpoint), and a colorblind-safe categorical set
# for the four memory conditions (seaborn "colorblind" palette, reordered so
# no_kg reads as the neutral baseline).

STANCE_COLORS = {
    "Strongly Against":  "#9e2a2b",
    "Against":           "#e08e6d",
    "Neutral":           "#9a9a9a",
    "In Favor":          "#6a9fb5",
    "Strongly In Favor": "#1d5b79",
}

_cb = sns.color_palette("colorblind")
CONDITION_COLORS = {
    "no_kg":        "#5a5a5a",
    "general_only": _cb[0],
    "tom_only":     _cb[2],
    "full_kg":      _cb[3],
}

CONDITION_LABELS = {
    "no_kg":        "No memory",
    "general_only": "General KG only",
    "tom_only":     "ToM KG only",
    "full_kg":      "Full KG",
}

sns.set_theme(
    style="whitegrid",
    context="paper",
    font_scale=1.15,
    rc={
        "figure.dpi":         300,
        "savefig.dpi":        300,
        "font.family":        "serif",
        "axes.edgecolor":     "#333333",
        "axes.linewidth":     0.8,
        "grid.linewidth":     0.5,
        "grid.color":         "#dddddd",
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "legend.frameon":     False,
        "axes.titleweight":   "bold",
        "axes.titlesize":     12,
        "axes.labelsize":     10.5,
        "xtick.labelsize":    9,
        "ytick.labelsize":    9,
        "legend.fontsize":    9,
    },
)


# ── Individual plot functions ──────────────────────────────────────────────────

def plot_trajectory(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    Opinion trajectory: proportion of agents at each Likert stance per iteration.
    One line per stance label, coloured by stance. Matches EPJ Figure 2.
    """
    traj = opinion_trajectory(df)
    fig, ax = plt.subplots(figsize=(9, 5))

    for label in LABEL_ORDER:
        if label in traj.columns:
            ax.plot(
                traj.index,
                traj[label] * 100,
                label=label,
                color=STANCE_COLORS[label],
                linewidth=2,
            )

    ax.set_xlabel("Iteration")
    ax.set_ylabel("% of agents")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    title = "Opinion trajectory"
    if condition_name:
        title += f": {CONDITION_LABELS.get(condition_name, condition_name)}"
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()

    _save(fig, output_dir, f"trajectory_{condition_name or 'all'}.png")


def plot_opinion_distribution(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    Stacked area chart showing opinion composition over time.
    """
    traj = opinion_trajectory(df)
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.stackplot(
        traj.index,
        [traj[label].values * 100 for label in LABEL_ORDER],
        labels=LABEL_ORDER,
        colors=[STANCE_COLORS[label] for label in LABEL_ORDER],
        alpha=0.85,
    )

    ax.set_xlabel("Iteration")
    ax.set_ylabel("% of agents")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    title = "Opinion distribution over time"
    if condition_name:
        title += f": {CONDITION_LABELS.get(condition_name, condition_name)}"
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=9, reverse=True)
    fig.tight_layout()

    _save(fig, output_dir, f"distribution_{condition_name or 'all'}.png")


def plot_acceptance_matrix(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    Heatmap of A_ij: probability that a Discussant with stance i
    accepts an Opponent with stance j. Matches EPJ Figure 4 (bottom panel).
    """
    A = acceptance_matrix(df)
    fig, ax = plt.subplots(figsize=(7, 6))

    im = ax.imshow(A.values, cmap="Blues", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label="P(accept)")

    ax.set_xticks(range(len(LABEL_ORDER)))
    ax.set_yticks(range(len(LABEL_ORDER)))
    short = ["SA-", "A-", "N", "A+", "SA+"]
    ax.set_xticklabels(short, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(short, fontsize=9)
    ax.set_xlabel("Opponent stance")
    ax.set_ylabel("Discussant stance")

    for i in range(len(LABEL_ORDER)):
        for j in range(len(LABEL_ORDER)):
            val = A.values[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=8, color="black" if val < 0.6 else "white")

    title = "Acceptance probability matrix"
    if condition_name:
        title += f"\n{CONDITION_LABELS.get(condition_name, condition_name)}"
    ax.set_title(title)
    fig.tight_layout()

    _save(fig, output_dir, f"acceptance_matrix_{condition_name or 'all'}.png")


def plot_acceptance_by_distance(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    P(A | Δx) vs Δx: acceptance probability as a function of opinion distance.
    Matches EPJ Figure 4 (top panel). Higher Δx → higher acceptance indicates
    asymmetric acceptance-rejection bias.
    """
    series = acceptance_by_distance(df)
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(
        series.index,
        series.values,
        marker="o",
        linewidth=2,
        color=CONDITION_COLORS.get(condition_name, "#1f77b4"),
        label=CONDITION_LABELS.get(condition_name, condition_name or "Acceptance"),
    )

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("Opinion distance Δx = x_Opponent − x_Discussant")
    ax.set_ylabel("P(A | Δx)")
    ax.set_ylim(0, 1)
    ax.set_title("Acceptance probability by opinion distance")
    ax.legend()
    fig.tight_layout()

    _save(fig, output_dir, f"acceptance_distance_{condition_name or 'all'}.png")


def plot_convergence_metrics(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    Entropy H(t) and standard deviation σ(t) over iterations.
    Both declining → opinions converging.
    """
    traj = opinion_trajectory(df)
    h    = entropy(traj)
    sig  = std_deviation(traj)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(h.index, h.values, color="#e377c2", linewidth=2)
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("Entropy H(t)")
    ax1.set_title("Opinion diversity (entropy)")

    ax2.plot(sig.index, sig.values, color="#17becf", linewidth=2)
    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Std deviation σ(t)")
    ax2.set_title("Opinion spread (std deviation)")

    title = condition_name and f"Convergence metrics: {CONDITION_LABELS.get(condition_name, condition_name)}"
    fig.suptitle(title or "Convergence metrics")
    fig.tight_layout()

    _save(fig, output_dir, f"convergence_{condition_name or 'all'}.png")


def compare_conditions(
    data_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """
    Side-by-side comparison of all four memory conditions.
    Looks for results.csv in data_dir/{condition}/ for each condition.
    Generates one cross-condition plot for each metric type.
    """
    data_dir   = Path(data_dir)
    conditions = ["no_kg", "general_only", "tom_only", "full_kg"]

    dfs: dict[str, pd.DataFrame] = {}
    for cond in conditions:
        csv = data_dir / cond / "results.csv"
        if csv.exists():
            dfs[cond] = pd.read_csv(csv)

    if not dfs:
        print(f"No results.csv files found under {data_dir}/")
        return

    # Cross-condition trajectory comparison
    fig, axes = plt.subplots(1, len(dfs), figsize=(5 * len(dfs), 5), sharey=True)
    if len(dfs) == 1:
        axes = [axes]

    for ax, (cond, df) in zip(axes, dfs.items()):
        traj = opinion_trajectory(df)
        for label in LABEL_ORDER:
            if label in traj.columns:
                ax.plot(traj.index, traj[label] * 100,
                        color=STANCE_COLORS[label], linewidth=1.5)
        ax.set_title(CONDITION_LABELS.get(cond, cond), fontsize=10)
        ax.set_xlabel("Iteration")
        if ax is axes[0]:
            ax.set_ylabel("% of agents")
        ax.set_ylim(0, 100)

    handles = [
        plt.Line2D([0], [0], color=STANCE_COLORS[l], linewidth=2, label=l)
        for l in LABEL_ORDER
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.06), fontsize=9)
    fig.suptitle("Opinion trajectories by memory condition", y=1.02)
    fig.tight_layout()
    _save(fig, output_dir, "compare_trajectories.png")

    # Cross-condition entropy comparison
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    for cond, df in dfs.items():
        traj = opinion_trajectory(df)
        h    = entropy(traj)
        ax2.plot(h.index, h.values,
                 color=CONDITION_COLORS.get(cond, "#888"),
                 label=CONDITION_LABELS.get(cond, cond),
                 linewidth=2)

    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Entropy H(t)")
    ax2.set_title("Opinion diversity across memory conditions")
    ax2.legend()
    fig2.tight_layout()
    _save(fig2, output_dir, "compare_entropy.png")

    # Cross-condition acceptance by distance
    fig3, ax3 = plt.subplots(figsize=(8, 4))
    for cond, df in dfs.items():
        series = acceptance_by_distance(df)
        ax3.plot(series.index, series.values,
                 marker="o",
                 color=CONDITION_COLORS.get(cond, "#888"),
                 label=CONDITION_LABELS.get(cond, cond),
                 linewidth=2)

    ax3.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6)
    ax3.set_xlabel("Opinion distance Δx = x_Opponent − x_Discussant")
    ax3.set_ylabel("P(A | Δx)")
    ax3.set_ylim(0, 1)
    ax3.set_title("Acceptance by opinion distance, all conditions")
    ax3.legend()
    fig3.tight_layout()
    _save(fig3, output_dir, "compare_acceptance_distance.png")


# ── NEW: Transition matrix ────────────────────────────────────────────────────

def plot_transition_matrix(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    Heatmap of T_ij: probability that an agent with stance i moves to stance j.

    Diagonal = agents who stayed the same.
    Off-diagonal = how opinion shifts flow between stances.
    """
    T = transition_matrix(df)
    fig, ax = plt.subplots(figsize=(7, 6))

    im = ax.imshow(T.values, cmap="YlOrRd", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label="P(transition)")

    short = ["SA−", "A−", "N", "A+", "SA+"]
    ax.set_xticks(range(len(LABEL_ORDER)))
    ax.set_yticks(range(len(LABEL_ORDER)))
    ax.set_xticklabels(short, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(short, fontsize=9)
    ax.set_xlabel("Stance after exchange")
    ax.set_ylabel("Stance before exchange")

    for i in range(len(LABEL_ORDER)):
        for j in range(len(LABEL_ORDER)):
            val = T.values[i, j]
            if val > 0:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=8, color="black" if val < 0.6 else "white")

    title = "Opinion transition matrix"
    if condition_name:
        title += f"\n{CONDITION_LABELS.get(condition_name, condition_name)}"
    ax.set_title(title)
    fig.tight_layout()
    _save(fig, output_dir, f"transition_matrix_{condition_name or 'all'}.png")


# ── NEW: Effective clusters ────────────────────────────────────────────────────

def plot_effective_clusters(
    df: pd.DataFrame,
    output_dir: str | Path,
    condition_name: str = "",
) -> None:
    """
    C(t) = N² / Σ n_i(t)²: effective number of opinion clusters over time.

    Higher C → more fragmentation. Lower C → fewer, larger opinion groups.
    """
    traj = opinion_trajectory(df)
    ec = effective_clusters(traj)
    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(ec.index, ec.values,
            color=CONDITION_COLORS.get(condition_name, "#1f77b4"),
            linewidth=2,
            label=CONDITION_LABELS.get(condition_name, condition_name or "Clusters"))

    ax.set_xlabel("Iteration")
    ax.set_ylabel("Effective clusters C(t)")
    title = "Opinion fragmentation (effective clusters)"
    if condition_name:
        title += f": {CONDITION_LABELS.get(condition_name, condition_name)}"
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    _save(fig, output_dir, f"effective_clusters_{condition_name or 'all'}.png")


# ── NEW: Agent opinion journey ─────────────────────────────────────────────────

def plot_agent_journey(
    df: pd.DataFrame,
    output_dir: str | Path,
    agent_id: str,
    agent_name: str = "",
    condition_name: str = "",
) -> None:
    """
    Trace a single agent's opinion score across every iteration they appeared in.

    Marks each data point and annotates stance-change moments with the label.
    This is the "single example" view that makes the simulation concrete and
    shows how one agent's opinion evolves through dialogue.
    """
    score_map = dict(zip(LABEL_ORDER, [-2, -1, 0, 1, 2]))
    label_map = {v: k for k, v in score_map.items()}

    # Collect all appearances (either as agent_a or agent_b) in order
    records: list[tuple[int, int, int, str]] = []  # (iter, score_before, score_after, partner)

    for _, row in df.iterrows():
        it = int(row["iteration"])
        if row["agent_a_id"] == agent_id:
            records.append((
                it,
                int(row["agent_a_stance_before_score"]),
                int(row["agent_a_stance_after_score"]),
                str(row["agent_b_name"]),
            ))
        elif row["agent_b_id"] == agent_id:
            records.append((
                it,
                int(row["agent_b_stance_before_score"]),
                int(row["agent_b_stance_after_score"]),
                str(row["agent_a_name"]),
            ))

    if not records:
        print(f"Agent {agent_id} not found in data, skipping journey plot.")
        return

    records.sort(key=lambda x: x[0])
    iters        = [r[0] for r in records]
    scores_after = [r[2] for r in records]
    changed      = [r[1] != r[2] for r in records]
    partners     = [r[3] for r in records]

    fig, ax = plt.subplots(figsize=(12, 5))

    # Shaded stance bands
    band_colors = ["#fce4e4", "#fff3e0", "#fffde7", "#e8f5e9", "#e3f2fd"]
    for score, color in zip([-2, -1, 0, 1, 2], band_colors):
        ax.axhspan(score - 0.5, score + 0.5, alpha=0.25, color=color, linewidth=0)

    # Journey line
    ax.step(iters, scores_after, where="post",
            color="#333333", linewidth=1.5, alpha=0.6, linestyle="--")
    ax.plot(iters, scores_after, "o", color="#333333", markersize=5, zorder=3)

    # Highlight stance changes. Above a density threshold, per-point text
    # labels overlap into an unreadable smear, so only annotate individually
    # when there are few enough changes for labels to stay legible; beyond
    # that, the colored markers alone still carry the signal.
    n_changes = sum(changed)
    annotate_individually = n_changes <= 20

    for i, (it, score, ch, partner) in enumerate(zip(iters, scores_after, changed, partners)):
        if ch:
            ax.plot(it, score, "o", color="#e74c3c", markersize=7 if annotate_individually else 4,
                    alpha=1.0 if annotate_individually else 0.7, zorder=4)
            if annotate_individually:
                ax.annotate(
                    f"-> {label_map[score]}\n(w/ {partner})",
                    xy=(it, score),
                    xytext=(it + 0.5, score + 0.35),
                    fontsize=7.5, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8),
                )

    if not annotate_individually:
        ax.text(
            0.01, 0.02,
            f"{n_changes} of {len(records)} exchanges changed this agent's stance "
            f"({n_changes / len(records) * 100:.1f}%). Individual labels omitted above "
            f"20 changes; each red point is still one real stance change.",
            transform=ax.transAxes, fontsize=8, color="#c0392b", va="bottom",
        )

    # Y-axis stance labels
    ax.set_yticks([-2, -1, 0, 1, 2])
    ax.set_yticklabels(["Strongly\nAgainst", "Against", "Neutral", "In Favor", "Strongly\nIn Favor"],
                       fontsize=8)
    ax.set_ylim(-2.7, 2.7)
    ax.set_xlabel("Exchange (sequential)")
    ax.set_ylabel("Stance")

    display_name = agent_name or agent_id
    title = f"Opinion journey: {display_name}"
    if condition_name:
        title += f" ({CONDITION_LABELS.get(condition_name, condition_name)})"
    ax.set_title(title)

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#333333",
               markersize=7, label="Stance (no change)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#e74c3c",
               markersize=9, label="Stance change"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)
    fig.tight_layout()

    safe_name = agent_name.lower().replace(" ", "_") if agent_name else agent_id
    _save(fig, output_dir, f"journey_{safe_name}_{condition_name or 'all'}.png")


# ── Cross-condition effective clusters comparison ──────────────────────────────

def compare_effective_clusters(
    data_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """Compare effective clusters C(t) across all four conditions."""
    data_dir   = Path(data_dir)
    conditions = ["no_kg", "general_only", "tom_only", "full_kg"]

    fig, ax = plt.subplots(figsize=(8, 4))
    for cond in conditions:
        csv = data_dir / cond / "results.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv)
        traj = opinion_trajectory(df)
        ec = effective_clusters(traj)
        ax.plot(ec.index, ec.values,
                color=CONDITION_COLORS.get(cond, "#888"),
                label=CONDITION_LABELS.get(cond, cond),
                linewidth=2)

    ax.set_xlabel("Iteration")
    ax.set_ylabel("C(t), effective clusters")
    ax.set_title("Opinion fragmentation across memory conditions")
    ax.legend()
    fig.tight_layout()
    _save(fig, output_dir, "compare_effective_clusters.png")


# ── Cross-condition acceptance matrix comparison ───────────────────────────────

def compare_acceptance_matrix(
    data_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """
    4-panel side-by-side heatmap of A_ij for all four memory conditions.

    Each panel shows P(accept | Discussant=i, Opponent=j). Placing all four
    together makes it immediately obvious where memory changes persuasion patterns.
    """
    data_dir   = Path(data_dir)
    conditions = ["no_kg", "general_only", "tom_only", "full_kg"]
    short      = ["SA−", "A−", "N", "A+", "SA+"]

    available = [(c, pd.read_csv(data_dir / c / "results.csv"))
                 for c in conditions if (data_dir / c / "results.csv").exists()]
    if not available:
        print("compare_acceptance_matrix: no results.csv found.")
        return

    n = len(available)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 5.5))
    if n == 1:
        axes = [axes]

    for ax, (cond, df) in zip(axes, available):
        A  = acceptance_matrix(df)
        im = ax.imshow(A.values, cmap="Blues", vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label="P(accept)", fraction=0.046, pad=0.04)

        ax.set_xticks(range(len(LABEL_ORDER)))
        ax.set_yticks(range(len(LABEL_ORDER)))
        ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(short, fontsize=8)
        ax.set_xlabel("Opponent stance", fontsize=9)
        if ax is axes[0]:
            ax.set_ylabel("Discussant stance", fontsize=9)

        for i in range(len(LABEL_ORDER)):
            for j in range(len(LABEL_ORDER)):
                val = A.values[i, j]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=8, color="black" if val < 0.6 else "white")

        ax.set_title(CONDITION_LABELS.get(cond, cond), fontsize=10, fontweight="bold")

    fig.suptitle("Acceptance probability matrix, all memory conditions", y=1.02, fontsize=13)
    fig.tight_layout()
    _save(fig, output_dir, "compare_acceptance_matrix.png")


# ── Cross-condition transition matrix comparison ───────────────────────────────

def compare_transition_matrix(
    data_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """
    4-panel side-by-side heatmap of T_ij for all four memory conditions.

    T_ij = P(stance after = j | stance before = i). Diagonal = agents who stayed.
    Comparing panels shows whether memory shifts opinion mobility up or down.
    """
    data_dir   = Path(data_dir)
    conditions = ["no_kg", "general_only", "tom_only", "full_kg"]
    short      = ["SA−", "A−", "N", "A+", "SA+"]

    available = [(c, pd.read_csv(data_dir / c / "results.csv"))
                 for c in conditions if (data_dir / c / "results.csv").exists()]
    if not available:
        print("compare_transition_matrix: no results.csv found.")
        return

    n = len(available)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 5.5))
    if n == 1:
        axes = [axes]

    for ax, (cond, df) in zip(axes, available):
        T  = transition_matrix(df)
        im = ax.imshow(T.values, cmap="YlOrRd", vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label="P(transition)", fraction=0.046, pad=0.04)

        ax.set_xticks(range(len(LABEL_ORDER)))
        ax.set_yticks(range(len(LABEL_ORDER)))
        ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(short, fontsize=8)
        ax.set_xlabel("Stance after exchange", fontsize=9)
        if ax is axes[0]:
            ax.set_ylabel("Stance before exchange", fontsize=9)

        for i in range(len(LABEL_ORDER)):
            for j in range(len(LABEL_ORDER)):
                val = T.values[i, j]
                if val > 0:
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            fontsize=8, color="black" if val < 0.6 else "white")

        ax.set_title(CONDITION_LABELS.get(cond, cond), fontsize=10, fontweight="bold")

    fig.suptitle("Opinion transition matrix, all memory conditions", y=1.02, fontsize=13)
    fig.tight_layout()
    _save(fig, output_dir, "compare_transition_matrix.png")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, output_dir: str | Path, filename: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate opinion dynamics plots.")
    parser.add_argument("--data-dir",   required=True, help="Directory containing condition subdirs")
    parser.add_argument("--output-dir", required=True, help="Where to save plots")
    parser.add_argument(
        "--condition",
        default=None,
        help="Single condition to plot (e.g. no_kg). Omit to run compare_conditions.",
    )
    args = parser.parse_args()

    if args.condition:
        csv_path = Path(args.data_dir) / args.condition / "results.csv"
        if not csv_path.exists():
            print(f"No results.csv found at {csv_path}")
            return
        df = pd.read_csv(csv_path)
        # Core plots
        plot_trajectory(df, args.output_dir, args.condition)
        plot_opinion_distribution(df, args.output_dir, args.condition)
        plot_acceptance_matrix(df, args.output_dir, args.condition)
        plot_acceptance_by_distance(df, args.output_dir, args.condition)
        plot_convergence_metrics(df, args.output_dir, args.condition)
        # New plots
        plot_transition_matrix(df, args.output_dir, args.condition)
        plot_effective_clusters(df, args.output_dir, args.condition)
        # Agent journey: plot the most-active agent (appeared in most iterations)
        all_agents = pd.concat([
            df[["agent_a_id","agent_a_name"]].rename(columns={"agent_a_id":"id","agent_a_name":"name"}),
            df[["agent_b_id","agent_b_name"]].rename(columns={"agent_b_id":"id","agent_b_name":"name"}),
        ])
        top = all_agents.groupby(["id","name"]).size().idxmax()
        plot_agent_journey(df, args.output_dir, top[0], top[1], args.condition)
    else:
        compare_conditions(args.data_dir, args.output_dir)
        compare_effective_clusters(args.data_dir, args.output_dir)
        compare_acceptance_matrix(args.data_dir, args.output_dir)
        compare_transition_matrix(args.data_dir, args.output_dir)


if __name__ == "__main__":
    _main()
