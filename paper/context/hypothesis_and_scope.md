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
  full_kg_ctx): planned as a follow-on, not part of this paper unless
  it is explicitly added back into scope later
- Network topology beyond uniform random daily pairing

## Outcome (appended 2026-09-30, after the 30-day four-condition results)

Everything above this heading is the pre-registered text and is left
unchanged. This section records what was found. Every number is from
`reports/full_ablation_summary.md` (label [R], reproducible from this repo)
unless marked otherwise.

### Criterion by criterion

| Pre-registered criterion | Result | Verdict |
|---|---|---|
| Support: tom_only has a flatter acceptance-by-distance curve than no_kg and general_only | d2/d1 acceptance ratio: tom_only 0.417 [0.396, 0.438], no_kg 0.401 [0.373, 0.430], general_only 0.366 [0.346, 0.386] | **Not supported.** tom_only is indistinguishable from no_kg |
| Support: full_kg has the smallest entropy change over the run | Entropy drop, day 0 to 30: full_kg 0.431, no_kg 0.473, tom_only 0.548, general_only 0.615 bits | **Met as operationalised**, but see "Stability" below |
| Support: general_only sits between no_kg and tom_only, or does not differ from no_kg | Acceptance curve close to no_kg; population outcome is the most convergent of all four | **Mixed.** No effect on the curve, largest effect on convergence |
| Against: no KG condition moves the acceptance curve relative to no_kg | full_kg ratio 0.758 [0.740, 0.775] | **Not met.** full_kg clearly moves it |
| Against: tom_only and general_only curves indistinguishable | d=1 0.275 vs 0.272; d=2 0.115 vs 0.099; ratio intervals do not overlap (0.417 vs 0.366) but both sit near no_kg | **Largely met.** Neither single-dimension memory changes selective agreement much |
| Against: some KG condition has a larger entropy collapse than no_kg | general_only (0.615) and tom_only (0.548) both exceed no_kg (0.473) | **Met** for general_only and tom_only |

### Stability: the reversal

The hypothesis predicted that combined memory would produce "the most stable
opinions over time", and it used the smallest entropy change as its
operational test. full_kg passes that test. The test measured the wrong thing,
though. full_kg keeps the most diversity because its agents never settle:

- 47.9% of full_kg agent-updates change stance, against 26.7% to 33.6% in the
  other three conditions;
- full_kg has the highest mean entropy and the most effective clusters over
  days 1 to 30, so it is the most fragmented condition throughout, not only at
  the end;
- full_kg agents accept distant partners more than any other condition
  (P(accept | d=2) = 0.267 against about 0.10 elsewhere).

On opinion stability, the construct the hypothesis cared about, full_kg is the
**least** stable condition, not the most. general_only, which the hypothesis
expected to matter least, produces the strongest convergence (lowest entropy
and fewest clusters, both at day 30 and averaged over the run). This is a
reversal of the prediction on the stability axis. It is not a confirmation,
even though one pre-registered number happens to point the "right" way.

### Agreement: partly the reverse of the mechanism predicted

The hypothesis expected theory-of-mind memory to reduce unconditional
agreement. tom_only does not change agreement relative to no_kg. full_kg
flattens the selective-agreement curve, but it does so by making agents
**more** willing to move toward distant partners, not by making them push
back harder. Move-away rates stay low in every condition. So the only memory
condition that changes the pattern makes agreement less selective and more
frequent.

### What the paper must not do

- The paper must not present "Information Paradox" or "Memory Asymmetry
  Principle" (labels from the external report) as the original hypothesis.
  If the paper uses them at all, it must introduce them as post hoc
  descriptions of an outcome that the pre-registered hypothesis did not
  predict.
- The paper must not cite the external report's directional claims as
  established, because several do not reproduce (see
  `reports/full_ablation_summary.md`, Section 6). In particular, the strongest
  net shift toward In Favor belongs to general_only, not full_kg.
- The paper must not describe In Favor as "pro-immigration". Per
  `topics/immigration.py`, In Favor means supporting restrictive immigration
  policy, and the prompts never state the proposition
  (`reports/full_ablation_summary.md`, Section 6.1).

### Known confound, revisited

The left drift described under "Known confound" above came from the 10-day
llama3.2/Ollama pilot. It does **not** appear in the 30-day DGX no_kg run
(day 30: 54 agents on the Against side, 65 on the In Favor side, mean score
+0.036). Report the drift per condition as mean stance score and side counts,
which the section on directional shifts does. Do not describe a left drift as
a baseline property of this ablation.

### Scope changes implied by the delivered data

- Each condition was run **once**, with one seed and one pairing schedule
  shared by all four conditions (verified row by row). Every
  between-condition comparison is therefore a single-run comparison.
  Agent-clustered bootstrap intervals describe within-run variability only.
- The DGX run's LLM is unconfirmed. The runbook recommends
  Llama-3.1-8B-Instruct, and the pilot used llama3.2. The earlier "only
  llama3.2 has been run" scope statement needs updating once the model is
  confirmed.

### Addendum (2026-09-30, same day): the directional measure

The pre-registered criteria used unsigned distance. Cau et al. (2025) define
selective agreement on signed distance, dx = x_partner - x_agent: acceptance
that rises with dx means a directional bias. Reading the delivered data that
way (`reports/full_ablation_summary.md`, Section 3.4):

- Every condition shows a one-step directional asymmetry: agents accept a
  partner on their In Favor side more readily than one on their Against
  side.
- The asymmetry is +0.042 under no_kg and +0.052 under tom_only. It is
  +0.176 under general_only, and that interval does not overlap any other
  condition's. Factual memory therefore amplifies the directional bias about
  fourfold. It is also the condition that converges most strongly toward In
  Favor.
- full_kg's asymmetry is modest (+0.067). Its distinctive effect is higher
  acceptance in both directions, including at two steps.

None of this was predicted. The hypothesis assigned the largest role to
theory-of-mind memory. tom_only leaves the shape of the acceptance curve
and the directional asymmetry indistinguishable from no_kg, and its churn
(0.336) is the closest to no_kg's (0.331). It does raise the level of
one-step acceptance slightly (0.275 [0.266, 0.283] vs 0.253 [0.243, 0.263]).

LODAS design differences that matter for comparing with Cau et al.: LODAS
uses a 7-point scale, has the Discussant update itself (no separate
annotator), debates a low-controversy topic with an explicit framing
statement, and averages over 10 runs. It also uses 140 agents and 30
iterations, so the population size here is the same as LODAS's, not larger.
