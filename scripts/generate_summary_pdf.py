"""
scripts/generate_summary_pdf.py: build a short, plain-language, part-by-part
walkthrough of the external "Opinion Dynamics" HTML report (140 agents, 4
memory conditions, 30 days, delivered outside this repo's own PDF pipeline).

This script does not recompute anything from data/. Every number below was
read off that HTML report by hand and cross-checked against this repo's own
ground-truth docs (paper/context/hypothesis_and_scope.md and
methodology_facts.md). Where the two disagree, or where the HTML report
disagrees with itself, this script says so explicitly rather than picking a
number silently — see the caveats page and Part 9.

Usage:
    PYTHONDONTWRITEBYTECODE=1 .venv_report/bin/python -B scripts/generate_summary_pdf.py \
        --output reports/plain_language_summary.pdf
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

from report_common import text_pages, table_page, FONT_FAMILY


def cover_and_caveats_page(pdf: PdfPages) -> None:
    lines = [
        "What this document is",
        "",
        "A condensed, plain-language walkthrough of 'Opinion Dynamics —",
        "Research Report' (the HTML file reviewed alongside this PDF),",
        "which is itself a long, chart-heavy report on a 30-day simulation",
        "of 140 LLM agents debating immigration policy under four different",
        "memory setups. This document follows that report's own section",
        "order, Part for Part, and drops the statistical machinery (the",
        "equations, the null-model IDs, the effect-size jargon) in favor of",
        "one plain sentence per finding. The last Part answers 'what should",
        "be done next', which the source report does not itself address.",
        "",
        "Two things to know before reading the rest of this document",
        "",
        "CAVEAT 1 — the day/hour mismatch",
        "The source report describes the simulation loop as one pairing",
        "per agent per simulated day. But its own exchange counts",
        "(100,800 exchanges per condition over 30 days, 140 agents) work",
        "out to roughly 24 exchanges per agent per day, not one — and one",
        "of its own later sections admits agents 'exchange tens of times",
        "per day' when justifying a different calculation. This repo's own",
        "methodology notes (paper/context/methodology_facts.md) flag the",
        "same mismatch independently, on the same DGX-delivered dataset,",
        "and say explicitly: do not describe the cadence as 'once per day'",
        "until Rossetti's actual loop code is confirmed. Every number in",
        "this document is still the source report's number — this caveat",
        "is about how the loop that produced them is described, not about",
        "whether the numbers themselves are wrong.",
        "",
        "CAVEAT 2 — one pair of fallacy numbers does not add up",
        "The source report states in its main text that 'Full KG (38.9%)",
        "produces roughly half the fallacy rate of No Memory (83.7%)'. Its",
        "own summary table, two pages later, gives No Memory's comparable",
        "figure as 61.1%, not 83.7% — the 83.7 figure is a different",
        "metric (fallacy instances per 100 turns, which double-counts",
        "turns with more than one flagged fallacy) being compared against",
        "a percentage-of-turns figure for Full KG. This document uses the",
        "self-consistent table numbers throughout (Part 6) and flags this",
        "as one concrete example of a broader check worth doing: verify",
        "the chart-generation code before any number from that report is",
        "quoted in a paper or shared outside this project.",
        "",
        "Everything else below is read directly off the source report,",
        "condition names shortened for readability: No Memory, General KG",
        "(facts only), ToM KG (theory-of-mind / partner-modeling only),",
        "Full KG (both together).",
    ]
    text_pages(pdf, "Opinion Dynamics — Plain-Language Summary", lines)


def part1_experiment_page(pdf: PdfPages) -> None:
    lines = [
        "140 simulated people, called agents, debate immigration policy",
        "for 30 simulated days. Each agent has a fixed personality (name,",
        "age, job, background) and a stance that can move on a 5-point",
        "scale: Strongly Against, Against, Neutral, In Favor, Strongly In",
        "Favor. The population starts centrist, matching a normal survey:",
        "10% Strongly Against, 20% Against, 40% Neutral, 20% In Favor, 10%",
        "Strongly In Favor.",
        "",
        "The experiment runs the identical population through four",
        "versions of the simulation. The ONLY thing that changes between",
        "versions is what each agent is allowed to remember between",
        "conversations:",
        "",
        "  NO MEMORY — 'the amnesiac society'. Agents forget every",
        "  conversation immediately. Each debate starts from zero.",
        "",
        "  GENERAL KG — 'the fact machine'. Agents remember factual claims",
        "  raised in conversation (e.g. 'immigration affects wages'), but",
        "  keep no record of what any particular partner believes.",
        "",
        "  TOM KG — 'the empathic listener' (ToM = Theory of Mind).",
        "  Agents remember what specific partners believe and how they",
        "  argue, but track no separate bank of general facts.",
        "",
        "  FULL KG — 'the informed paradox'. Both of the above combined:",
        "  facts plus a model of every partner's beliefs, plus a running",
        "  record of the agent's own past positions.",
        "",
        "Each day: everyone is shuffled and paired once with a random",
        "partner, the pair exchanges 2 to 5 turns of argument, and a",
        "separate AI judge (which never sees the memory, only the words",
        "just spoken) scores whether and how far each agent's stance",
        "moved. Movement is capped at one step per exchange — an agent",
        "cannot jump from Strongly Against to In Favor in a single",
        "conversation, only drift toward it gradually.",
        "",
        "THE HEADLINE FINDING",
        "More memory does not mean more agreement. The condition that",
        "remembers the most (Full KG) ends up the most fragmented, not the",
        "most unified. The condition that produces the single strongest",
        "shared opinion (General KG) is not the richest-memory one — it is",
        "the one with facts only, no awareness of what other agents think.",
    ]
    text_pages(pdf, "Part 1 — The Experiment, In Plain Terms", lines)


def part2_architecture_page(pdf: PdfPages) -> None:
    lines = [
        "The four memory setups above are not just labels — they are four",
        "configurations of the same underlying memory system (GhostKG).",
        "Understanding it in outline explains why the four conditions",
        "behave so differently.",
        "",
        "Every exchange goes through three steps, described here without",
        "the formulas the source report uses to define them:",
        "",
        "  1. ABSORB — the agent reads the partner's message and files",
        "     away anything worth remembering, as a short note of the",
        "     form 'X relates to Y' (a fact, or a belief attributed to",
        "     the partner).",
        "  2. REFLECT — before replying, the agent looks back through its",
        "     own notes (only the categories its condition allows it to",
        "     see: facts, partner-beliefs, or both) and assembles what it",
        "     knows into context for its next argument.",
        "  3. REPLY — the agent generates its response from that context,",
        "     then rates how well the exchange went, which is what",
        "     decides how long the just-formed notes will stick around.",
        "",
        "FORGETTING IS BUILT IN, ON PURPOSE",
        "A note an agent files away does not last forever. It fades the",
        "way a fact you haven't discussed in weeks starts to feel fuzzy —",
        "unless the same topic comes up again, in which case the note is",
        "refreshed and becomes harder to forget. This decay mechanism",
        "(FSRS, a spaced-repetition model borrowed from flashcard apps)",
        "means an agent's memory in this simulation is not a permanent",
        "transcript — it is a living, selective record where frequently-",
        "revisited topics become entrenched and one-off mentions quietly",
        "disappear.",
        "",
        "WHY 'FACTS' AND 'PARTNER BELIEFS' ARE GENUINELY DIFFERENT",
        "General KG notes are things like 'immigration affects the",
        "economy' — free-floating claims about the world, with no owner.",
        "ToM KG notes are things like 'Agent 12 supports open borders' —",
        "claims specifically about what another named agent thinks. An",
        "agent using only General KG can win a factual argument but has",
        "no idea who it is arguing with or what they said last time. An",
        "agent using only ToM KG remembers its opponents intimately but",
        "has no independent facts to draw on. Full KG agents get both,",
        "plus a record of their own past stated positions — which turns",
        "out to matter a great deal, as the next parts show.",
    ]
    text_pages(pdf, "Part 2 — How the Memory Actually Works", lines)


def part3_persuasion_page(pdf: PdfPages) -> None:
    lines = [
        "The report tracks, for every single exchange, who moved and by",
        "how much. Three patterns hold up across all four conditions:",
        "",
        "1. PEOPLE MOVE ONE STEP AT A TIME, NEVER IN LEAPS",
        "An agent starting Strongly Against never jumps straight to In",
        "Favor in one exchange. Movement is always to the adjacent stance.",
        "This is a rule built into the simulation (a one-step-per-exchange",
        "cap), not an emergent finding — but everything downstream depends",
        "on it, so it is worth stating plainly.",
        "",
        "2. NEUTRAL IS THE LEAST PROTECTED POSITION, IN EVERY CONDITION",
        "Undecided agents are the easiest to move, no matter which memory",
        "type they carry. No version of memory 'anchors' the center of the",
        "opinion spectrum. Where a Neutral agent gets pushed, however,",
        "depends heavily on which memory condition it is in (Part 4).",
        "",
        "3. PRO POSITIONS ARE STICKY. CONTRA POSITIONS ARE NOT.",
        "Agents who are Strongly In Favor are the easiest to talk down to",
        "a more moderate favorable stance, in every single condition —",
        "over 90% of the time, regardless of memory. Agents who are",
        "Strongly Against hold their ground far better without memory, but",
        "become steadily easier to move as memory is added. Memory does",
        "not make anti-immigration positions easier to defend — it makes",
        "them easier to erode, while leaving pro-immigration positions",
        "just as easy to talk to (never fully immovable, just moderated).",
        "Read narrowly: this is a property of this specific simulated",
        "debate (this topic, this model, this population), not a general",
        "law about persuasion. It is still the report's most consistent",
        "single pattern, showing up in every one of the four conditions.",
        "",
        "4. THE 'WRONG' KIND OF DISTANT ARGUMENT IS THE HARDEST TO WIN",
        "Intuition says an argument from someone who agrees with you",
        "mostly should be easy to accept, and an argument from someone at",
        "the opposite extreme should be hardest. The data show almost the",
        "reverse: agents resist most when the opposing view is moderately",
        "different from their own, and accept most readily from someone at",
        "the extreme opposite end of the scale. One plausible reading:",
        "extreme arguments tend to be more fully worked out, leaving less",
        "room for a half-hearted rebuttal, while moderate disagreement",
        "invites exactly that. Full KG is the one condition that mostly",
        "irons this pattern out, making agents roughly equally persuadable",
        "regardless of how far apart the two views start.",
    ]
    text_pages(pdf, "Part 3 — Who Convinces Whom", lines)


def part4_fragmentation_page(pdf: PdfPages) -> None:
    lines = [
        "Two questions matter at the population level, separate from any",
        "single exchange: does the group end up more united or more split",
        "(fragmentation), and which way does it drift over the full 30",
        "days (direction)? The four conditions answer both questions",
        "differently.",
        "",
        "GENERAL KG (FACTS ONLY) — THE STRONGEST CONVERGENCE",
        "Ends the run with the fewest distinct opinion camps and the most",
        "agents In Favor or Strongly In Favor (52% positive by day 30, the",
        "highest of any condition). But — counterintuitively — it is the",
        "ONE condition where the In Favor camp actually loses agents in",
        "raw headcount over the 30 days, even though it is also the most",
        "stable camp to be in. Being stable (people who start pro-",
        "immigration mostly stay that way) and being growing (more people",
        "arriving at that view) turn out to be different things, and",
        "General KG is strong on the first and weak on the second.",
        "",
        "FULL KG (BOTH TYPES OF MEMORY) — THE MOST FRAGMENTED, YET THE",
        "MOST DECISIVE OVER TIME",
        "At any given moment, Full KG looks the least settled: the most",
        "opinion camps survive, individual agents change their stated",
        "position more often than in any other condition. Yet zoomed out",
        "to the full 30 days, it produces the strongest net swing toward",
        "In Favor (+25% in the positive field) and the steepest collapse",
        "of the Against camp (-33%). Constant local churn and a clear",
        "long-run destination are not contradictory here: individual",
        "conversations are unpredictable, but the accumulated drift, exam-",
        "ined over a month, tilts consistently in one direction.",
        "",
        "TOM KG (PARTNER-MODELING ONLY) — THE FAIREST OUTCOME",
        "The only condition where undecided agents end up moving toward",
        "'In Favor' and 'Against' in roughly equal numbers. It preserves",
        "the most balanced spread of opinion of any memory-bearing",
        "condition, but that balance comes at a cost: no view ever wins,",
        "and the In Favor camp slowly loses ground over the month.",
        "",
        "NO MEMORY — LIVELY BUT GOING NOWHERE",
        "Daily movement is high (this is, in fact, the most unstable",
        "condition exchange-to-exchange for extreme positions), but there",
        "is no persistent 30-day trend either way. The population ends up",
        "close to where it started.",
    ]
    text_pages(pdf, "Part 4 — Does the Group Unite or Split Apart?", lines)


def part4b_summary_table(pdf: PdfPages) -> None:
    col_labels = ["Condition", "By day 30, favors...", "How split is it?", "One-line verdict"]
    rows = [
        ["No Memory", "Roughly unchanged (~stalemate)", "Moderate, stable", "Lively but rudderless"],
        ["General KG", "Strongest pro-lean (52% positive)", "Lowest — most united", "Convinces most, but loses growth"],
        ["ToM KG", "Weak pro-lean, most balanced exits", "High, most even split", "Fairest outcome, no clear winner"],
        ["Full KG", "Strongest net swing to pro (+25%)", "Highest — most fragmented", "Chaotic locally, decisive overall"],
    ]
    table_page(pdf, "Part 4 (continued) — Quick-reference comparison", col_labels, rows,
               col_widths=[0.14, 0.32, 0.24, 0.30], figsize=(12, 5.5))


def part5_conceptual_cores_page(pdf: PdfPages) -> None:
    lines = [
        "As agents argue, the ones who end up on the same side (pro,",
        "anti, or neutral) gradually build up a shared vocabulary of",
        "talking points — the report calls this a 'conceptual core'. Two",
        "findings here are worth pulling out of the technical detail:",
        "",
        "RICHER MEMORY BUILDS BIGGER SHARED VOCABULARIES WITHIN A CAMP",
        "By day 30, agents on the same side under Full KG share roughly",
        "3 to 4 times as many common talking points as agents on the same",
        "side under ToM KG alone (for example, 339 shared concepts in the",
        "pro camp under Full KG, versus 102 under ToM KG). General KG",
        "sits in between. More representational capacity produces more",
        "common ground — inside a given camp.",
        "",
        "ACROSS CONDITIONS, THE FOUR SIMULATIONS BARELY SPEAK THE SAME",
        "LANGUAGE",
        "This is the sharper point. Compare the SAME camp (say, the pro-",
        "immigration agents) across two DIFFERENT memory conditions, and",
        "the overlap in shared concepts drops to 14-26%, even for the",
        "closest pair of conditions. In the distinctive-vocabulary tables",
        "(Part 6), the overlap in the most characteristic keywords across",
        "conditions is not low — it is exactly zero, in every single one",
        "of 18 comparisons checked. Practically: change only what an agent",
        "is allowed to remember, and it doesn't just end up with a",
        "different opinion — it ends up arguing in what amounts to a",
        "different dialect. This is one reason cross-condition influence",
        "(an agent from one memory setup persuading one from another) is",
        "structurally unlikely: there is barely enough shared vocabulary",
        "to have the argument in the first place.",
    ]
    text_pages(pdf, "Part 5 — What Common Ground Forms (and What Doesn't)", lines)


def part6_discourse_page(pdf: PdfPages) -> None:
    lines = [
        "Every one of the 403,200 exchanges in the study was also scored",
        "for tone (positive or negative language) and checked for nine",
        "types of logical fallacy (straw man, appeal to emotion, and so",
        "on) by an automated classifier. See Caveat 2 on the first page —",
        "the numbers below use the report's self-consistent summary table,",
        "not the headline sentence that mixes two different metrics.",
        "",
        "THE SURPRISING PAIRING: TONE AND RIGOR DO NOT MOVE TOGETHER",
        "Full KG agents produce the most negative-sounding language of any",
        "condition (and stay negative even when their own stated position",
        "is favorable) — but they also commit the fewest logical fallacies",
        "by a wide margin. General KG agents sound the most upbeat, but",
        "make sloppier arguments more often than any other condition.",
        "Sounding reasonable and arguing rigorously turn out to be two",
        "separate things, and richer memory buys the second at the cost",
        "of the first.",
        "",
        "ONE FALLACY TYPE FLIPS THE PATTERN: STRAW-MANNING",
        "Full KG is the only condition where a specific fallacy — straw",
        "man arguments (misrepresenting what the other side actually",
        "said) — goes UP rather than down. The likely reading: agents with",
        "enough real detail to work with can construct a more convincing-",
        "sounding distortion of their opponent's position; agents with",
        "little factual material to draw on cannot build a targeted",
        "misrepresentation, even if they wanted to.",
        "",
        "AT THE WORD LEVEL, THE FOUR CONDITIONS SHARE NOTHING",
        "Checking the single most distinctive words used in each",
        "condition (as opposed to the broader concepts in Part 5), the",
        "overlap across all four conditions is zero — not low, zero, in",
        "every comparison checked. This is the same 'different dialects'",
        "finding from Part 5, now confirmed down to individual word",
        "choice, not just topic-level concepts.",
    ]
    text_pages(pdf, "Part 6 — How Agents Argue: Tone and Logical Rigor", lines)


def part6b_discourse_charts(pdf: PdfPages) -> None:
    conditions = ["Full KG", "General KG", "No Memory", "ToM KG"]
    sentiment = [-0.361, 0.214, -0.127, 0.029]
    fallacy_pct_turns = [38.9, 63.2, 61.1, 55.1]
    colors = sns.color_palette("Set2", len(conditions))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    axes[0].bar(conditions, sentiment, color=colors)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_title("Mean sentiment (-1 negative, +1 positive)", fontsize=11, family=FONT_FAMILY)
    axes[1].bar(conditions, fallacy_pct_turns, color=colors)
    axes[1].set_title("Turns containing >=1 logical fallacy (%)", fontsize=11, family=FONT_FAMILY)
    for ax in axes:
        ax.tick_params(axis="x", rotation=20)
        for label in ax.get_xticklabels():
            label.set_family(FONT_FAMILY)
    fig.suptitle("Tone vs. rigor: Full KG is the most negative AND the most careful",
                 fontsize=13, fontweight="bold", family=FONT_FAMILY)
    fig.text(0.06, 0.02,
             "Table-consistent figures (Part 6 / Caveat 2). Source: sentiment and fallacy-rate "
             "summary tables in the original report.",
             fontsize=8, family=FONT_FAMILY, style="italic")
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    pdf.savefig(fig)
    plt.close(fig)


def part7_regimes_page(pdf: PdfPages) -> None:
    col_labels = ["Condition", "Nickname", "One-sentence verdict"]
    rows = [
        ["No Memory", "Stochastic Equilibrium", "Lively but rudderless — the closest thing to fair, by default."],
        ["General KG", "Monopolar Convergence", "The most opinionated context of the four. Facts are not neutral — they lean."],
        ["ToM KG", "Competitive Diversity", "The fairest memory. Preserves pluralism, produces no winner."],
        ["Full KG", "Unstable Asymmetric Eq.", "Paradoxically the most volatile locally and the most decisive over time."],
    ]
    table_page(pdf, "Part 7 — Four Conditions, Four Distinct Regimes", col_labels, rows,
               col_widths=[0.16, 0.24, 0.60], figsize=(12, 5.2))

    lines = [
        "THE ONE-PARAGRAPH VERSION OF THE WHOLE REPORT",
        "Memory type does not decide whether opinions change — every",
        "condition sees plenty of movement. It decides HOW the group",
        "moves as a whole: whether it converges (General KG), stays split",
        "(ToM KG), churns locally while drifting decisively (Full KG), or",
        "goes nowhere in particular (No Memory). The right question for",
        "any real information environment is not 'how much information",
        "does it provide', but 'what kind, and whose side does it quietly",
        "help'.",
        "",
        "The source report backs this up with 19 separate statistical",
        "checks (Part 8) rather than resting on the raw numbers alone —",
        "worth knowing before treating any single chart as the full",
        "story.",
    ]
    text_pages(pdf, "Part 7 (continued) — The Core Insight", lines)


def part8_validation_page(pdf: PdfPages) -> None:
    lines = [
        "Nearly every claim in this document was checked against a",
        "'what would this look like if it were pure chance' baseline —",
        "not just eyeballed off a chart. The source report runs 19",
        "separate statistical tests for this purpose; the mechanics are",
        "skipped here, but three examples give a sense of the rigor:",
        "",
        "  - The population drift each condition shows (Part 4) was",
        "    compared against 1,000 randomly-shuffled versions of the",
        "    same data. For General KG and Full KG, the real drift beat",
        "    the random version in over 99.4% of trials — a roughly",
        "    1-in-150-or-better result, not a coin flip.",
        "",
        "  - The sentiment gap between conditions (Part 6) was tested",
        "    across all 403,200 exchanges; the chance of seeing a gap",
        "    this large by accident is, for practical purposes, zero",
        "    (p is effectively 0 in standard notation).",
        "",
        "  - One specific pattern — that Full KG agents show genuinely",
        "    unpredictable individual behavior, not just more movement",
        "    on average — was checked agent-by-agent rather than only at",
        "    the population level. Every single Full KG agent tested",
        "    (100%) showed this individually, versus 77% under ToM KG, 3%",
        "    under General KG, and 0% under No Memory. This is arguably",
        "    the single most technically novel result in the report and",
        "    is worth a closer read before deciding whether it belongs in",
        "    the main paper text or a technical appendix (Part 9).",
        "",
        "Not everything passed. A handful of secondary patterns (a",
        "specific test for whether agents give unusually generous",
        "credit to extreme-opposite arguments) came back statistically",
        "underpowered — the source report labels these 'inconclusive'",
        "rather than confirmed, and this document has left them out of",
        "the earlier Parts for that reason.",
    ]
    text_pages(pdf, "Part 8 — Is Any of This Just Noise?", lines)


def part9_recommendations_page(pdf: PdfPages) -> None:
    lines = [
        "1. RESOLVE THE DAY/HOUR DISCREPANCY BEFORE WRITING METHODS",
        "Confirm with Rossetti what the actual DGX loop code does before",
        "any methodology text (in this report, a future paper draft, or",
        "anything shared outside the project) describes the simulation",
        "as 'one exchange per agent per day'. The data behind every number",
        "in this document is consistent with roughly 24 exchanges per",
        "agent per day, and this repo's own ground-truth notes",
        "(paper/context/methodology_facts.md) already flag this as open.",
        "This does not put the FINDINGS in question — it puts one",
        "specific sentence describing the loop in question.",
        "",
        "2. FIX THE FALLACY-RATE COMPARISON (CAVEAT 2) BEFORE IT IS QUOTED",
        "Small, mechanical, and easy to miss: a chart-generation or",
        "copy-editing bug mixes two different fallacy metrics for the",
        "No Memory condition. Worth a quick pass over the report's other",
        "17-plus charts and tables for the same kind of mismatch before",
        "any number from it goes into a paper draft or external message.",
        "",
        "3. TEST WHETHER THE HEADLINE PATTERNS ARE TOPIC- OR MODEL-",
        "SPECIFIC",
        "Every result above comes from one topic (immigration policy) and",
        "one model (llama3.2). This matches the project's own existing",
        "plan (a moderately divisive topic and a neutral control topic,",
        "still pending) and the paper's stated scope, which explicitly",
        "excludes cross-topic and cross-model claims for now. The two",
        "strongest, most citable findings — the Memory Asymmetry",
        "Principle (pro positions are sticky, contra positions erode as",
        "memory grows) and the Information Paradox (more memory, more",
        "fragmentation, not more consensus) — are exactly the two claims",
        "a reviewer will ask to see replicated on a second topic before",
        "accepting them as general rather than an artifact of this one",
        "debate.",
        "",
        "4. UPDATE THE PRE-REGISTERED HYPOTHESIS DOCUMENT TO MATCH WHAT",
        "WAS ACTUALLY FOUND",
        "paper/context/hypothesis_and_scope.md predates this dataset and",
        "predicts a different pattern (full_kg = most stable opinions).",
        "That is a fine thing for a pre-registered hypothesis to get",
        "wrong — the document itself says a null result is still",
        "publishable — but the Results section should be written against",
        "what was pre-registered, explicitly stating the reversal, rather",
        "than quietly writing new claims (Information Paradox, Memory",
        "Asymmetry) as if they were the original prediction.",
        "",
        "5. DECIDE WHERE THE NON-MARKOVIAN RESULT (PART 8) GOES",
        "It is technically the most novel single finding here but also",
        "the hardest to explain without equations. Decide early whether",
        "it anchors a claim in the main text (in which case it needs its",
        "own plain-language framing, similar to this document's Part 8)",
        "or moves to a technical appendix aimed at reviewers who want the",
        "statistical detail.",
        "",
        "6. THE ANNOTATOR-CONTEXT QUESTION IS STILL OPEN",
        "Whether the stance-scoring judge should see 1-3 prior exchange",
        "turns instead of just the current utterance is explicitly out of",
        "scope for this paper per the project's own notes, but flagged",
        "as a planned follow-on. No action needed now beyond keeping it",
        "off the current paper's claims.",
    ]
    text_pages(pdf, "Part 9 — What Should Be Done Next", lines)


def key_statements_table(pdf: PdfPages) -> None:
    col_labels = ["#", "Statement", "Status"]
    rows = [
        ["1", "Strongly-favorable positions resist persuasion regardless of memory.", "Validated"],
        ["2", "Strongly-opposed positions grow more persuadable as memory increases.", "Validated"],
        ["3", "Neutral agents are the most persuadable group in every condition.", "Validated"],
        ["4", "Facts (General KG) drive convergence; partner-modeling (ToM KG) drives diversity.", "Validated"],
        ["5", "Combining both memory types produces effects neither produces alone.", "Validated"],
        ["6", "More memory produces more fragmentation, not more consensus.", "Validated"],
        ["7", "Moderate-distance opponents are resisted most; extreme-distance ones, least.", "Validated"],
        ["8", "The factual-knowledge environment has a built-in directional (pro) lean.", "Validated"],
        ["9", "Each condition's shared vocabulary is largely exclusive to that condition.", "Validated"],
        ["10", "Full KG is simultaneously the most negative and the most rigorous condition.", "Validated"],
        ["11", "Keyword vocabulary is fully disjoint across all four conditions (0% overlap).", "Validated"],
        ["12", "Full KG produces individually unpredictable trajectories, not just more motion.", "Validated (N19)"],
    ]
    table_page(pdf, "Reference — The 12 Key Statements From the Source Report", col_labels, rows,
               col_widths=[0.04, 0.80, 0.16], figsize=(12, 8.5))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the plain-language summary PDF.")
    parser.add_argument("--output", required=True, help="Path to write the PDF")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(out_path) as pdf:
        cover_and_caveats_page(pdf)
        part1_experiment_page(pdf)
        part2_architecture_page(pdf)
        part3_persuasion_page(pdf)
        part4_fragmentation_page(pdf)
        part4b_summary_table(pdf)
        part5_conceptual_cores_page(pdf)
        part6_discourse_page(pdf)
        part6b_discourse_charts(pdf)
        part7_regimes_page(pdf)
        part8_validation_page(pdf)
        part9_recommendations_page(pdf)
        key_statements_table(pdf)

    print(f"Plain-language summary PDF written to {out_path}")


if __name__ == "__main__":
    main()
