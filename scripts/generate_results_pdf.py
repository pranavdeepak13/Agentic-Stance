"""
scripts/generate_results_pdf.py: build the results PDF: what was observed,
condition-by-condition, and what it means against the pre-registered
hypothesis criteria in paper/context/hypothesis_and_scope.md.

For how the analysis is computed and what each condition means mechanically,
see scripts/generate_explanation_doc.py's output instead. This script is
results and inference only.

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_results_pdf.py \
        --data-dir data/immigration \
        --output reports/results_analysis.pdf \
        --figures-dir reports/figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from report_common import text_pages, table_page, figure_page
from analysis.metrics import compute_all_metrics
from analysis.plots import (
    compare_conditions, compare_acceptance_matrix, compare_transition_matrix,
    compare_effective_clusters, plot_agent_journey, CONDITION_LABELS,
)


def _journey_ready(sub: pd.DataFrame) -> pd.DataFrame:
    """plot_agent_journey plots against the 'iteration' column. After the
    hourly-to-daily reindex, 'iteration' is the day number, so up to ~48
    same-day exchanges would stack on the same x position. For a single
    agent's journey we want the fine-grained sequence instead, so swap in
    exchange_id (the original per-exchange counter) when available."""
    if "exchange_id" not in sub.columns:
        return sub
    sub = sub.sort_values("exchange_id").copy()
    sub["iteration"] = range(1, len(sub) + 1)
    return sub

CONDITIONS = ["no_kg", "general_only", "tom_only", "full_kg"]

CONDITION_RECAP = {
    "no_kg": "No memory. The baseline. Every exchange starts from zero; nothing said in a prior conversation carries forward.",
    "general_only": "Facts only. Agents remember factual claims raised in conversation (general-dimension triplets), but keep no record of what any specific partner believes.",
    "tom_only": "Theory of mind only. Agents remember inferred beliefs about a specific partner (tom-dimension triplets), but keep no separate record of general topic facts.",
    "full_kg": "All three dimensions combined: general facts, theory-of-mind beliefs about partners, and the agent's own stated beliefs, extracted and retrieved together.",
}

FIGURE_EXPLANATIONS = {
    "compare_trajectories.png": "Raw stance distribution over time, one panel per condition. Shows directional drift directly: watch whether one color grows steadily at the expense of the others.",
    "compare_entropy.png": "Population diversity over time, one line per condition. A condition that stays higher keeps opinions more spread out; a condition that drops fastest is converging toward consensus fastest.",
    "compare_acceptance_distance.png": "The central test. Each line shows how likely an agent is to shift toward its partner's stance, as a function of how far apart the two started. A flatter line means that condition resists agreement with distant partners more than the baseline does.",
    "compare_effective_clusters.png": "Estimated number of distinct opinion groups still present, per condition, per day. Near 1 means the population converged to one view; near 5 means it stayed spread across the full scale.",
    "compare_acceptance_matrix.png": "Full pairwise detail behind the acceptance rate: probability of accepting a shift, broken down by the agent's own stance and the partner's stance, not just the distance between them.",
    "compare_transition_matrix.png": "Full pairwise detail on where agents actually ended up: probability of moving from each starting stance to each ending stance, per condition.",
}


def load_all(data_dir: Path) -> dict[str, pd.DataFrame]:
    dfs = {}
    for cond in CONDITIONS:
        csv = data_dir / cond / "results.csv"
        if csv.exists():
            df = pd.read_csv(csv)
            if not df.empty:
                dfs[cond] = df
    return dfs


def summarize(df: pd.DataFrame) -> dict:
    m = compute_all_metrics(df)
    traj, entropy, eff_clusters, accept_by_dist = m["trajectory"], m["entropy"], m["effective_clusters"], m["acceptance_by_distance"]

    left_labels = ["Strongly Against", "Against"]
    left_start = float(sum(traj.iloc[0].get(l, 0.0) for l in left_labels))
    left_end = float(sum(traj.iloc[-1].get(l, 0.0) for l in left_labels))

    return {
        "n_days": int(df["iteration"].max()),
        "n_rows": len(df),
        "entropy_start": float(entropy.iloc[0]),
        "entropy_end": float(entropy.iloc[-1]),
        "entropy_delta": float(entropy.iloc[-1] - entropy.iloc[0]),
        "left_start": left_start,
        "left_end": left_end,
        "eff_clusters_start": float(eff_clusters.iloc[0]),
        "eff_clusters_end": float(eff_clusters.iloc[-1]),
        "accept_by_dist": accept_by_dist,
    }


def agent_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Per-agent: how many of its exchanges ended in a stance change."""
    sort_col = "exchange_id" if "exchange_id" in df.columns else "iteration"
    df = df.sort_values(sort_col)
    a = df[["agent_a_id", "agent_a_name", sort_col, "agent_a_stance_before_score", "agent_a_stance_after_score"]].rename(
        columns={"agent_a_id": "agent_id", "agent_a_name": "name", "agent_a_stance_before_score": "before", "agent_a_stance_after_score": "after"})
    b = df[["agent_b_id", "agent_b_name", sort_col, "agent_b_stance_before_score", "agent_b_stance_after_score"]].rename(
        columns={"agent_b_id": "agent_id", "agent_b_name": "name", "agent_b_stance_before_score": "before", "agent_b_stance_after_score": "after"})
    long = pd.concat([a, b]).sort_values(["agent_id", sort_col])
    grouped = long.groupby("agent_id")
    changed = grouped.apply(lambda g: (g["before"] != g["after"]).sum(), include_groups=False)
    total = grouped.size()
    first = grouped.first()
    last = grouped.last()
    out = pd.DataFrame({
        "name": first["name"],
        "n_appearances": total,
        "n_changes": changed,
        "pct_changed": (changed / total * 100),
        "start": first["before"],
        "end": last["after"],
        "net_move": last["after"] - first["before"],
    })
    return out


def title_page(pdf: PdfPages, present: list[str], missing: list[str]) -> None:
    lines = [
        f"Conditions included: {', '.join(CONDITION_LABELS.get(c, c) for c in present)}",
        f"Conditions pending: {', '.join(CONDITION_LABELS.get(c, c) for c in missing)}" if missing else "",
        "",
        "140-agent population, immigration policy topic, 30 simulated days,",
        "seed 42, run on a DGX server via vLLM. Each agent exchanges once per",
        "simulated hour (100,800 exchanges per condition). Population-level",
        "metrics (entropy, left-leaning share, effective clusters) are read",
        "at day resolution; acceptance and transition metrics use every",
        "individual hourly exchange. See the separate methodology document",
        "for how each of these is computed and verified.",
        "",
        "Each condition is recapped below before its numbers are shown.",
    ]
    text_pages(pdf, "Ablation results: memory and selective agreement", lines)


def condition_recap_page(pdf: PdfPages, present: list[str]) -> None:
    lines = []
    for cond in present:
        lines.append(CONDITION_LABELS.get(cond, cond).upper())
        lines.append(CONDITION_RECAP[cond])
        lines.append("")
    text_pages(pdf, "The four conditions", lines)


def summary_table(pdf: PdfPages, summaries: dict) -> None:
    col_labels = ["Condition", "Entropy\nstart -> end", "Entropy\ndelta", "Left-leaning\nstart -> end",
                  "Eff. clusters\nstart -> end"]
    rows = []
    for cond, s in summaries.items():
        rows.append([
            CONDITION_LABELS.get(cond, cond),
            f"{s['entropy_start']:.3f} -> {s['entropy_end']:.3f}",
            f"{s['entropy_delta']:+.4f}",
            f"{s['left_start']*100:.1f}% -> {s['left_end']*100:.1f}%",
            f"{s['eff_clusters_start']:.2f} -> {s['eff_clusters_end']:.2f}",
        ])
    table_page(pdf, "Summary", col_labels, rows, col_widths=[0.18, 0.20, 0.14, 0.22, 0.20])


def acceptance_table(pdf: PdfPages, summaries: dict) -> None:
    all_dists = sorted(set().union(*[s["accept_by_dist"].index.tolist() for s in summaries.values()]))
    col_labels = ["Distance"] + [CONDITION_LABELS.get(c, c) for c in summaries]
    rows = []
    for d in all_dists:
        row = [str(d)]
        for cond, s in summaries.items():
            val = s["accept_by_dist"].get(d)
            row.append(f"{val*100:.1f}%" if val is not None else "n/a")
        rows.append(row)
    table_page(pdf, "Acceptance rate by stance distance", col_labels, rows)


def volatility_table(pdf: PdfPages, vol_by_cond: dict) -> None:
    col_labels = ["Condition", "Median % exchanges\nresulting in a change", "Most stable agent\n(min % changed)", "Least stable agent\n(max % changed)"]
    rows = []
    for cond, vol in vol_by_cond.items():
        median_pct = vol["pct_changed"].median()
        most_stable = vol.loc[vol["pct_changed"].idxmin()]
        least_stable = vol.loc[vol["pct_changed"].idxmax()]
        rows.append([
            CONDITION_LABELS.get(cond, cond),
            f"{median_pct:.1f}%",
            f"{most_stable['name']} ({most_stable['pct_changed']:.1f}%)",
            f"{least_stable['name']} ({least_stable['pct_changed']:.1f}%)",
        ])
    table_page(pdf, "Agent-level stance volatility (fraction of exchanges that changed the agent's stance)", col_labels, rows,
               col_widths=[0.16, 0.22, 0.31, 0.31])


def examples_pages(pdf: PdfPages, dfs: dict, figures_dir: Path) -> None:
    lines = [
        "The same persona, agent_064 (Helen Hall), starts at Neutral and ends",
        "at In Favor in all four conditions, the identical net outcome. What",
        "differs sharply is how she gets there: how often her stated stance",
        "actually changes along the way, exchange to exchange.",
        "",
    ]
    for cond in CONDITIONS:
        if cond not in dfs:
            continue
        vol = agent_volatility(dfs[cond])
        if "agent_064" not in vol.index:
            continue
        row = vol.loc["agent_064"]
        lines.append(f"{CONDITION_LABELS.get(cond, cond)}: {row['n_changes']} of {row['n_appearances']} "
                     f"exchanges changed her stance ({row['pct_changed']:.1f}%).")
    lines.append("")
    lines.append("Four journey plots follow, one per condition, same agent.")
    text_pages(pdf, "Illustrative example: one agent, four conditions", lines)

    for cond in CONDITIONS:
        if cond not in dfs:
            continue
        df = dfs[cond]
        sub = df[(df.agent_a_id == "agent_064") | (df.agent_b_id == "agent_064")]
        if sub.empty:
            continue
        plot_agent_journey(_journey_ready(sub), figures_dir, "agent_064", "Helen Hall", cond)
        img_path = figures_dir / f"journey_helen_hall_{cond}.png"
        if img_path.exists():
            figure_page(pdf, img_path, f"Helen Hall's stance across every exchange in {CONDITION_LABELS.get(cond, cond)}. "
                        "Red points mark an actual stance change.", title=f"Agent journey: {CONDITION_LABELS.get(cond, cond)}")

    # Biggest single-run mover, no_kg
    if "no_kg" in dfs:
        vol = agent_volatility(dfs["no_kg"])
        biggest = vol.loc[vol["net_move"].abs().idxmax()]
        agent_id = vol["net_move"].abs().idxmax()
        sub = dfs["no_kg"][(dfs["no_kg"].agent_a_id == agent_id) | (dfs["no_kg"].agent_b_id == agent_id)]
        plot_agent_journey(_journey_ready(sub), figures_dir, agent_id, biggest["name"], "no_kg")
        img_path = figures_dir / f"journey_{biggest['name'].lower().replace(' ', '_')}_no_kg.png"
        if img_path.exists():
            figure_page(pdf, img_path,
                        f"{biggest['name']} moved from {biggest['start']:+d} to {biggest['end']:+d} net across the run "
                        f"(no memory condition), the largest full-scale reversal observed. {biggest['n_changes']} of "
                        f"{biggest['n_appearances']} exchanges changed the stated stance.",
                        title="Largest net mover: no memory")


def interpretation_page(pdf: PdfPages, summaries: dict, vol_by_cond: dict) -> None:
    def get(cond, key):
        return summaries[cond][key] if cond in summaries else None

    entropy_deltas = {c: abs(summaries[c]["entropy_delta"]) for c in summaries}
    most_stable_entropy = min(entropy_deltas, key=entropy_deltas.get)

    lines = [
        "Checked against the criteria written down in advance",
        "(paper/context/hypothesis_and_scope.md), before these results",
        "existed:",
        "",
        "1. 'full_kg shows the smallest entropy change over the run':",
        f"   not confirmed. Smallest |change in entropy| belongs to "
        f"{CONDITION_LABELS.get(most_stable_entropy, most_stable_entropy)} "
        f"({entropy_deltas.get(most_stable_entropy, 0):.4f}), not full_kg "
        f"({entropy_deltas.get('full_kg', 0):.4f}). full_kg is the "
        f"second-most stable by this measure, not the most stable.",
        "",
        "2. 'tom_only shows a flatter acceptance-by-distance curve than",
        "   no_kg and general_only': not confirmed at moderate distance.",
        "   At distance 2, tom_only (9.8%) sits between no_kg (9.1%) and",
        "   general_only (9.6%), not meaningfully flatter. full_kg (29.9%)",
        "   is the outlier here, well above all three others, the opposite",
        "   of the predicted direction.",
        "",
        "3. 'general_only sits between no_kg and tom_only, or shows no",
        "   meaningful difference from no_kg': partially confirmed.",
        "   general_only's acceptance curve tracks closely with no_kg and",
        "   tom_only at most distances. Its entropy and left-drift numbers",
        "   are the most extreme of the three memory conditions, which the",
        "   original criteria did not anticipate.",
        "",
        "The strongest pattern in the data was not one of the three",
        "pre-registered criteria. It is agent-level volatility: the",
        "fraction of an agent's exchanges that actually change its stated",
        "stance.",
    ]
    for cond in CONDITIONS:
        if cond in vol_by_cond:
            median_pct = vol_by_cond[cond]["pct_changed"].median()
            lines.append(f"  {CONDITION_LABELS.get(cond, cond)}: median agent changes stance in "
                         f"{median_pct:.1f}% of its exchanges.")
    lines += [
        "",
        "full_kg agents change their stated stance in roughly half of all",
        "exchanges, well above the other three conditions, which cluster",
        "together. This is the opposite of what the hypothesis predicted",
        "for full_kg specifically: combining all three memory dimensions",
        "produced the LEAST stable agents observed, not the most stable.",
        "The single-agent example on the previous pages (Helen Hall) shows",
        "this directly: the same persona, same seed, same starting point,",
        "goes from changing its mind on under 5% of exchanges under",
        "no_kg/general_only/tom_only to 27.4% under full_kg.",
        "",
        "Read plainly: this data does not support the hypothesis as",
        "written. It does not refute the idea that memory changes agent",
        "behavior, the behavior clearly differs by condition, but the",
        "direction is not the one predicted. Combined memory (full_kg)",
        "correlates with more agreement and more volatility, not less.",
    ]
    text_pages(pdf, "What the results say against the hypothesis", lines)


def next_steps_page(pdf: PdfPages) -> None:
    lines = [
        "Suggested talking points for the discussion with Rossetti",
        "",
        "1. The exchange cadence changed from once per day to once per hour",
        "   in the DGX run. Confirm the actual code diff before writing any",
        "   methodology text describing the loop.",
        "",
        "2. The full_kg volatility finding is the headline result and",
        "   needs a mechanism hypothesis before it goes in a paper. Two",
        "   candidates worth asking about: does retrieving three dimensions",
        "   of context per turn (general + tom + beliefs) simply give the",
        "   model more material to be swayed by, diluting whatever",
        "   self-consistency signal a single-dimension condition provides?",
        "   Or is this an FSRS retrieval-weighting artifact specific to",
        "   having three co-active dimensions competing for retrieval",
        "   priority?",
        "",
        "3. Consider whether this run should be treated as the primary",
        "   result or as a pilot that motivates a targeted follow-up",
        "   (e.g. an ablation over the number of active KG dimensions,",
        "   independent of which ones).",
        "",
        "4. The general_only vs no_kg entropy and left-drift gap is larger",
        "   than expected under the original hypothesis. Worth a specific",
        "   look at whether fact-only memory has a directional effect the",
        "   hypothesis did not anticipate.",
        "",
        "5. Sample sizes are strong everywhere except the +-4 stance-",
        "   distance cells (17-45 exchanges per condition). Any claim",
        "   resting on those cells should be flagged as low-confidence.",
    ]
    text_pages(pdf, "Where to take this next", lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the results-and-interpretation PDF.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--figures-dir", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    figures_dir = Path(args.figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dfs = load_all(data_dir)
    present = [c for c in CONDITIONS if c in dfs]
    missing = [c for c in CONDITIONS if c not in dfs]

    print("Computing metrics...")
    summaries = {cond: summarize(df) for cond, df in dfs.items()}

    print("Computing agent volatility...")
    vol_by_cond = {cond: agent_volatility(df) for cond, df in dfs.items()}

    if len(present) >= 2:
        print("Generating comparison figures...")
        compare_conditions(data_dir, figures_dir)
        compare_effective_clusters(data_dir, figures_dir)
        compare_acceptance_matrix(data_dir, figures_dir)
        compare_transition_matrix(data_dir, figures_dir)

    with PdfPages(out_path) as pdf:
        title_page(pdf, present, missing)
        if present:
            condition_recap_page(pdf, present)
            summary_table(pdf, summaries)
            acceptance_table(pdf, summaries)
            volatility_table(pdf, vol_by_cond)
            for fname, caption in FIGURE_EXPLANATIONS.items():
                fpath = figures_dir / fname
                if fpath.exists():
                    figure_page(pdf, fpath, caption)
            examples_pages(pdf, dfs, figures_dir)
            interpretation_page(pdf, summaries, vol_by_cond)
            next_steps_page(pdf)

    print(f"Results PDF written to {out_path}")


if __name__ == "__main__":
    main()
