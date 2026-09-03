# Hypothesis and scope

Ground truth for what this paper claims and does not claim. Any section
referencing the research question or hypothesis must match this document,
not restate it from memory.

## Research question

Does persistent, structured, decaying memory change the selective-agreement
pattern that LLM agents exhibit in pairwise debate, relative to a memoryless
baseline (Cau et al. 2025, LODAS framework)?

## Hypothesis

Structured memory of a partner's prior stated beliefs (theory-of-mind
memory) reduces an agent's tendency toward unconditional agreement more
than memory of facts alone. Combined memory (facts + theory-of-mind +
self-belief tracking) produces the most stable opinions over time.

This is a hypothesis, not a finding. No section of the paper may state it
as established until the general_only, tom_only, and full_kg results exist
and have been read against it.

## Experimental design

Four conditions, same population, same topic, same seed, same simulation
length, only memory differs:

| Condition | Memory content |
|---|---|
| no_kg | none (baseline) |
| general_only | facts extracted from conversation |
| tom_only | inferred beliefs about the specific partner |
| full_kg | general + tom + the agent's own stated beliefs |

Population: 140 agents, immigration policy topic, truncated-Gaussian
stance distribution (10% far left, 20% left, 40% center, 20% right, 10%
far right).

Simulation length: originally 10 days for no_kg, at one exchange per
agent per day. Extended to 30 days for general_only, tom_only, and
full_kg by the collaborator running the DGX ablation. The no_kg
baseline was re-run at 30 days for alignment. All four conditions are
now confirmed at 30 days, delivered 2026-09-03, 100,800 rows per
condition (140 agents x 24 hours x 30 days). This is a materially
different design than the original 10-day runs: the DGX version
exchanges roughly once per simulated hour, not once per day. The
mechanism behind this change has not been confirmed against source code
yet (see `methodology_facts.md`, "Open discrepancy"). Do not describe
the cadence as "once per day" anywhere until that is resolved.

## What would count as support for the hypothesis

Stated in advance, before results exist, so the paper is not written to
fit whatever the numbers happen to show:

- tom_only shows a flatter acceptance-by-distance curve than no_kg and
  general_only (agents push back more against distant-stance partners)
- full_kg shows the smallest entropy change over the run (most stable
  population-level opinion distribution)
- general_only sits between no_kg and tom_only, or shows no meaningful
  difference from no_kg (facts alone, without belief tracking, may not
  be enough to change agreement behavior)

## What would count against the hypothesis

- No KG condition moves the acceptance curve relative to no_kg
- tom_only and general_only produce statistically indistinguishable
  curves (would suggest the effect is about having any memory at all,
  not about what kind)
- Any KG condition shows a larger, not smaller, entropy collapse than
  no_kg

A null result on any of the above is still a publishable, reportable
finding. It is not a failed experiment.

## Known confound

The no_kg baseline shows a large directional left-drift (left-leaning
share of the population roughly doubling over the run) that is not
explained by selective agreement alone. This is attributed to a
directional prior in the underlying model's (llama3.2) handling of the
immigration topic specifically, not to symmetric social dynamics. Every
cross-condition comparison must report this drift per condition, not
just the acceptance curve, since a KG condition could suppress the drift,
leave it unchanged, or amplify it, and each of those is a different
finding.

## Explicitly out of scope for this paper

- Cross-model comparison (only llama3.2 has been run to completion)
- Cross-topic generalization (only immigration policy has been run)
- The annotator-context ablation (general_only_ctx, tom_only_ctx,
  full_kg_ctx) — planned as a follow-on, not part of this paper unless
  it is explicitly added back into scope later
- Network topology beyond uniform random daily pairing
