"""
analysis/metrics.py: compute the EPJ paper's opinion dynamics metrics from results.csv.

All metrics match the definitions in Cau et al. (2025, EPJ Data Science).

Metrics:
  opinion_trajectory     : P_x(t), proportion of agents at each stance per iteration
  entropy                : H(t), opinion diversity (higher = more diverse)
  std_deviation          : σ(t), spread of opinion scores
  effective_clusters     : C(t), effective number of opinion clusters
  transition_matrix      : T_ij, empirical opinion update probabilities
  acceptance_matrix      : A_ij, P(agent accepts | Discussant=i, Opponent=j)
  rejection_matrix       : R_ij, P(agent rejects | Discussant=i, Opponent=j)
  acceptance_by_distance : P(A | Δx), acceptance rate by opinion distance

Usage:
    import pandas as pd
    from analysis.metrics import compute_all_metrics

    df = pd.read_csv("data/no_kg/results.csv")
    metrics = compute_all_metrics(df)
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

# The ordered Likert score values (matches LikertStance scores: -2 to +2)
SCORE_VALUES = [-2, -1, 0, 1, 2]
LABEL_ORDER  = ["Strongly Against", "Against", "Neutral", "In Favor", "Strongly In Favor"]


def opinion_trajectory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute P_x(t): the proportion of agents holding each stance at each iteration.

    Returns a DataFrame indexed by iteration with one column per Likert label.
    Each row sums to 1.0 (or close, given rounding).

    Note: each iteration only updates 2 agents (the interacting pair).
    We track stance_after for both agents per row, accumulating across all agents.
    For a full population snapshot at each iteration, we use the most recent
    stance_after for every agent as of that iteration.
    """
    # Build a long-form table of (iteration, agent_id, stance_score)
    records = []
    for _, row in df.iterrows():
        records.append({
            "iteration":  int(row["iteration"]),
            "agent_id":   row["agent_a_id"],
            "stance":     row["agent_a_stance_after_label"],
            "score":      int(row["agent_a_stance_after_score"]),
        })
        records.append({
            "iteration":  int(row["iteration"]),
            "agent_id":   row["agent_b_id"],
            "stance":     row["agent_b_stance_after_label"],
            "score":      int(row["agent_b_stance_after_score"]),
        })

    long_df = pd.DataFrame(records)

    # For each agent, keep only their most recent stance at each iteration
    # (forward-fill to get population snapshots at every iteration)
    pivot = (
        long_df
        .sort_values("iteration", kind="stable")
        .groupby(["iteration", "agent_id"])["stance"]
        .last()
        .unstack("agent_id")
        .ffill()
    )

    # Count proportion per label per iteration
    n_agents = pivot.shape[1]
    result = pd.DataFrame(index=pivot.index, columns=LABEL_ORDER, dtype=float).fillna(0.0)

    for iteration, row in pivot.iterrows():
        counts = row.value_counts()
        for label in LABEL_ORDER:
            result.at[iteration, label] = counts.get(label, 0) / n_agents

    return result


def entropy(traj: pd.DataFrame) -> pd.Series:
    """
    Shannon entropy H(t) = -Σ p_i(t) log₂ p_i(t).

    Higher entropy → more diverse opinions.
    Lower entropy  → convergence or consensus.

    Input: opinion_trajectory DataFrame (rows = iterations, columns = labels).
    """
    def _h(row: pd.Series) -> float:
        probs = row[row > 0]
        return -float(sum(p * math.log2(p) for p in probs))

    return traj.apply(_h, axis=1).rename("entropy")


def std_deviation(traj: pd.DataFrame, score_map: dict[str, int] | None = None) -> pd.Series:
    """
    Weighted standard deviation σ(t) of opinion scores.

    σ(t) = sqrt( Σ p_i(t) * (i - μ(t))² )
    μ(t) = Σ p_i(t) * i

    Lower σ → tighter clustering around the mean stance.
    """
    if score_map is None:
        score_map = dict(zip(LABEL_ORDER, SCORE_VALUES))

    scores = np.array([score_map[label] for label in LABEL_ORDER])

    def _sigma(row: pd.Series) -> float:
        p = row.values.astype(float)
        mu = float(np.dot(p, scores))
        return float(np.sqrt(np.dot(p, (scores - mu) ** 2)))

    return traj.apply(_sigma, axis=1).rename("std_deviation")


def effective_clusters(traj: pd.DataFrame) -> pd.Series:
    """
    Effective number of opinion clusters C(t) = N² / Σ n_i(t)², where n_i(t) is
    the number of AGENTS (not exchange-endpoints) holding stance i at time t.

    Higher C → more fragmentation (many similarly-sized opinion groups).
    Lower C  → fewer clusters (convergence toward fewer opinions).

    Formula from Sirbu et al. (2017), as used in the EPJ paper.

    Takes the trajectory DataFrame from opinion_trajectory(df), the same input
    entropy() and std_deviation() take, not the raw results.csv DataFrame.
    Since opinion_trajectory already resolves each agent to its single most
    recent stance per iteration (correctly handling iterations that bundle
    many exchanges, e.g. a full day of hourly exchanges), effective_clusters
    reuses that resolution instead of re-deriving it from raw exchange rows.
    With p_i(t) = n_i(t) / N (traj's columns), C(t) = N² / Σ(p_i·N)² = 1 / Σp_i².
    """
    p = traj.to_numpy(dtype=float)
    sum_sq = (p ** 2).sum(axis=1)
    with np.errstate(divide="ignore"):
        c = np.where(sum_sq > 0, 1.0 / sum_sq, 0.0)
    return pd.Series(c, index=traj.index, name="effective_clusters")


def transition_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Empirical transition matrix T_ij = P(stance at t+1 = j | stance at t = i).

    Rows = stance before exchange. Columns = stance after exchange.
    Each row sums to 1.0.

    Computed across all agent-exchange pairs (both agent_a and agent_b).
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for _, row in df.iterrows():
        counts[row["agent_a_stance_before_label"]][row["agent_a_stance_after_label"]] += 1
        counts[row["agent_b_stance_before_label"]][row["agent_b_stance_after_label"]] += 1

    T = pd.DataFrame(0.0, index=LABEL_ORDER, columns=LABEL_ORDER)
    for before, after_counts in counts.items():
        total = sum(after_counts.values())
        if total > 0:
            for after, count in after_counts.items():
                T.at[before, after] = count / total

    return T


def acceptance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Acceptance probability matrix A_ij.

    A_ij = P(Discussant moves toward Opponent | Discussant stance = i, Opponent stance = j)

    "Moves toward" means the Discussant's after-score moves in the direction of the Opponent's score.

    Rows = Discussant's before stance. Columns = Opponent's before stance.
    """
    accept_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_counts:  dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for _, row in df.iterrows():
        # Treat agent_a as Discussant (who changes), agent_b as Opponent
        d_before = row["agent_a_stance_before_label"]
        d_after  = row["agent_a_stance_after_label"]
        o_before = row["agent_b_stance_before_label"]

        d_before_score = row["agent_a_stance_before_score"]
        d_after_score  = row["agent_a_stance_after_score"]
        o_before_score = row["agent_b_stance_before_score"]

        total_counts[d_before][o_before] += 1
        # "Accepted" = Discussant moved closer to Opponent
        direction = o_before_score - d_before_score
        movement  = d_after_score  - d_before_score
        if direction != 0 and (movement * direction > 0):
            accept_counts[d_before][o_before] += 1

        # Reverse: treat agent_b as Discussant
        d_before = row["agent_b_stance_before_label"]
        d_after  = row["agent_b_stance_after_label"]
        o_before = row["agent_a_stance_before_label"]

        d_before_score = row["agent_b_stance_before_score"]
        d_after_score  = row["agent_b_stance_after_score"]
        o_before_score = row["agent_a_stance_before_score"]

        total_counts[d_before][o_before] += 1
        direction = o_before_score - d_before_score
        movement  = d_after_score  - d_before_score
        if direction != 0 and (movement * direction > 0):
            accept_counts[d_before][o_before] += 1

    A = pd.DataFrame(0.0, index=LABEL_ORDER, columns=LABEL_ORDER)
    for d, opp_counts in total_counts.items():
        for o, total in opp_counts.items():
            if total > 0:
                A.at[d, o] = accept_counts[d][o] / total

    return A


def rejection_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rejection probability matrix R_ij = 1 - A_ij (for interactions where direction ≠ 0).
    Computed analogously to acceptance_matrix but counts moves away from Opponent.
    """
    reject_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_counts:  dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for _, row in df.iterrows():
        for d_before_col, d_after_col, d_before_score_col, d_after_score_col, o_before_col, o_before_score_col in [
            ("agent_a_stance_before_label", "agent_a_stance_after_label",
             "agent_a_stance_before_score", "agent_a_stance_after_score",
             "agent_b_stance_before_label", "agent_b_stance_before_score"),
            ("agent_b_stance_before_label", "agent_b_stance_after_label",
             "agent_b_stance_before_score", "agent_b_stance_after_score",
             "agent_a_stance_before_label", "agent_a_stance_before_score"),
        ]:
            d_before = row[d_before_col]
            o_before = row[o_before_col]
            direction = row[o_before_score_col] - row[d_before_score_col]
            movement  = row[d_after_score_col]  - row[d_before_score_col]

            total_counts[d_before][o_before] += 1
            if direction != 0 and (movement * direction < 0):
                reject_counts[d_before][o_before] += 1

    R = pd.DataFrame(0.0, index=LABEL_ORDER, columns=LABEL_ORDER)
    for d, opp_counts in total_counts.items():
        for o, total in opp_counts.items():
            if total > 0:
                R.at[d, o] = reject_counts[d][o] / total

    return R


def acceptance_by_distance(df: pd.DataFrame) -> pd.Series:
    """
    P(A | Δx) where Δx = x_Opponent - x_Discussant (signed opinion distance).

    The key EPJ finding: acceptance probability increases with Δx
    (agents more likely to accept opinions that are more positive than their own).

    Returns a Series indexed by Δx value.
    """
    accept_by_delta: dict[int, list[int]] = defaultdict(list)

    for _, row in df.iterrows():
        for d_before_score, d_after_score, o_before_score in [
            (row["agent_a_stance_before_score"], row["agent_a_stance_after_score"], row["agent_b_stance_before_score"]),
            (row["agent_b_stance_before_score"], row["agent_b_stance_after_score"], row["agent_a_stance_before_score"]),
        ]:
            delta     = int(o_before_score) - int(d_before_score)
            direction = delta
            movement  = int(d_after_score) - int(d_before_score)

            if direction != 0:
                accepted = 1 if (movement * direction > 0) else 0
                accept_by_delta[delta].append(accepted)

    result = {
        delta: sum(vals) / len(vals)
        for delta, vals in sorted(accept_by_delta.items())
        if vals
    }
    return pd.Series(result, name="P(A|delta_x)")


def compute_all_metrics(df: pd.DataFrame) -> dict:
    """
    Compute all metrics for a single condition's results DataFrame.
    Returns a dict with all metric objects, ready for plotting.
    """
    traj = opinion_trajectory(df)
    return {
        "trajectory":           traj,
        "entropy":              entropy(traj),
        "std_deviation":        std_deviation(traj),
        "effective_clusters":   effective_clusters(traj),
        "transition_matrix":    transition_matrix(df),
        "acceptance_matrix":    acceptance_matrix(df),
        "rejection_matrix":     rejection_matrix(df),
        "acceptance_by_distance": acceptance_by_distance(df),
    }
