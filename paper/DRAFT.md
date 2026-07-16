# Structured Memory and Selective Agreement in Populations of LLM Agents

**Status: draft skeleton. Abstract and introduction are written in full. Later sections are outlined, to be filled in once the full ablation completes.**

---

## Abstract

Large language models exhibit a well-documented agreeableness bias: in dialogue, a model tends to shift toward whichever position was argued most recently or most persuasively, independent of the argument's merit. In populations of interacting LLM agents, this produces selective agreement, where agents move more readily toward interlocutors whose stated views are already close to their own. Prior work (Cau et al., 2025) documented this pattern in a framework of randomly paired LLM agents debating a divisive topic, each holding a position on a five-point Likert scale, with no memory carried between exchanges.

This paper asks whether persistent, structured memory changes that behavior. We extend the baseline framework with GhostKG, a per-agent knowledge graph whose contents decay over simulated time using FSRS, a spaced-repetition scheduling algorithm. We run a controlled ablation across four memory conditions, no memory, general factual recall, theory-of-mind recall of a partner's inferred beliefs, and all three combined, holding population, topic, random seed, and simulation length fixed across conditions.

Our no-memory baseline, run at 140 agents over ten simulated days on an immigration-policy topic, replicates the selective agreement effect at this larger scale: the probability an agent shifts toward its partner falls from 34.9% at a one-step stance gap to 20.1% at a two-step gap. The same run surfaces a confound worth reporting on its own terms: the population drifts asymmetrically over time, with left-leaning agents growing from 30% to 60% of the population as the center collapses, an effect attributable to the underlying model's directional prior on the topic rather than to symmetric social dynamics.

We report this baseline and the experimental design for the three memory-bearing conditions, currently in progress, and lay out the metrics, entropy over time, the acceptance matrix conditioned on stance distance, and the transition matrix, against which the central hypothesis will be tested: that structured memory of a partner's prior stated beliefs, more than memory of facts alone, reduces an agent's tendency toward unconditional agreement.

---

## 1. Introduction

Ask a large language model a question twice, framed from two different directions, and it will often give two different answers, each aligned with the framing it was just handed. This is not a subtle failure mode. It shows up in single-turn question answering, in multi-turn dialogue, and, when many LLM agents are placed in conversation with each other, it shows up as a population-level effect: agents converge toward whichever position is stated with confidence, regardless of whether that position is closer to being correct or more broadly held.

Cau et al. (2025) gave this effect a name in the context of multi-agent simulation: selective agreement. In their framework, LODAS, LLM agents are assigned a starting position on a topic, drawn from a five-point Likert scale, and are paired at random to debate. After each exchange, a separate model reads each agent's own utterances and assigns an updated stance. The central finding is that agents shift toward an interlocutor's position more often when that position is already close to their own, and shift less, or not at all, when the interlocutor's position is far away. This is a milder and more specific claim than saying LLMs are simply sycophantic: it says the sycophancy is conditional on similarity, which is a subtler and in some ways more concerning failure mode, since it produces the appearance of deliberation while actually reinforcing existing clusters.

The LODAS framework, by design, gives its agents no memory. Each exchange is independent of every other exchange that agent has had. This is a reasonable simplifying assumption for isolating the core effect, but it leaves open a natural question: does an agent that remembers what it has previously argued, and what it has learned about the people it is arguing with, behave differently? Human opinion change is not memoryless. People resist arguments that contradict things they have said before, not always for good epistemic reasons, but resist all the same. If LLM agents are meant to stand in for something like human deliberation, even as a rough model, giving them memory is a natural next step, and testing whether that memory changes the selective agreement pattern is a direct way to ask whether the effect is an artifact of memorylessness or something more fundamental to how these models process conversational pressure.

This paper introduces that memory as GhostKG, a structured knowledge graph attached to each agent, populated by extracting subject-predicate-object claims from the agent's conversations and stored with FSRS-based decay, so that older, less-reinforced information fades the way spaced-repetition literature suggests human recall does. We distinguish three kinds of memory content an agent might carry: general facts asserted in conversation, theory-of-mind inferences about what a specific partner believes, and the agent's own previously stated beliefs. We test each in isolation and in combination against a no-memory baseline, using the same population, topic, and simulation length across all four conditions, so that any difference in outcome is attributable to what the agent remembers rather than to some other confound in the setup.

**Contributions of this work:**

1. A reproduction of the selective agreement effect at a larger population scale (140 agents versus the smaller populations used in prior work), which also surfaces a directional drift confound tied to the underlying model's own topic priors, worth flagging as a methodological consideration for anyone running this kind of simulation.
2. A controlled four-condition ablation isolating which kind of memory, if any, changes the selective agreement pattern: factual recall, theory-of-mind recall, or both together.
3. An open, ±1-step constraint on stance movement per exchange, added after observing that unconstrained annotation allowed single-exchange shifts from one extreme of the scale to the other, a defect in the scoring mechanism rather than a plausible model of real opinion change.
4. A released simulation framework supporting arbitrary topics, memory conditions, and LLM backends (including local models via Ollama and high-throughput inference via vLLM), designed so that adding a new experimental condition touches one function rather than the exchange loop itself.

The remainder of this paper is organized as follows. Section 2 places this work against the selective agreement literature, spaced-repetition memory models, and prior multi-agent opinion dynamics simulations. Section 3 describes the simulation framework, the memory conditions, and the topics used. Section 4 describes the experiments run and in progress. Section 5 reports results. Section 6 discusses what the results do and do not support, and where the current design leaves open questions. Section 7 states limitations plainly. Section 8 concludes.

---

## 2. Related Work (skeleton)

- Cau et al. (2025), EPJ Data Science: LODAS framework, selective agreement finding. This paper's direct baseline and point of departure.
- Prior work on LLM sycophancy and agreement bias in single-turn and RLHF-trained models (cite the specific papers once selected; note where multi-agent population effects differ from single-agent sycophancy findings).
- Classical opinion dynamics models (bounded confidence, DeGroot, voter models) as the non-LLM precedent for entropy/consensus/polarization metrics used here.
- FSRS and spaced-repetition scheduling literature, as the justification for using it as a decay mechanism for social/conversational memory, and an open question of whether a scheduler built for individual factual recall transfers meaningfully to socially-situated belief memory.
- Knowledge-graph-augmented LLM agents (retrieval-augmented generation, agent memory architectures) as the general category GhostKG belongs to, and what distinguishes a decaying, dimension-typed graph from a flat retrieval store.

## 3. Method (skeleton)

- 3.1 Simulation framework: day-based loop, one exchange per agent per day, multi-turn dialogue, separate annotator model reading only the scored agent's own utterances.
- 3.2 The ±1 Likert clamp: motivation (the single-exchange extreme-to-extreme shift observed pre-clamp), mechanism, and its effect on interpreting entropy and transition results.
- 3.3 Memory conditions: no_kg, general_only, tom_only, full_kg. Definition of each KG dimension (general, tom, beliefs) and what gets extracted and retrieved under each condition.
- 3.4 GhostKG mechanics: triplet extraction, FSRS decay driven by a simulated clock (`set_agent_time`), and the scope of what is and is not passed as metadata (relevant to reproducibility: only subject-predicate-object crosses into storage, not our internal `round` bookkeeping field).
- 3.5 Population and topics: 140-agent truncated-Gaussian stance distribution for immigration policy; planned extensions to a second polarizing-but-distinct topic and a neutral control topic with an aligned stance-seeding strategy.
- 3.6 Metrics: Shannon entropy of the stance distribution over time, the acceptance matrix (probability of shifting toward a partner's stance, conditioned on stance distance), the transition matrix (start-to-end stance movement), and planned KG characterization metrics (triplet count over time, dominant predicate types, cross-agent KG overlap).

## 4. Experiments (skeleton)

- 4.1 Baseline (no_kg): complete. 140 agents, 10 days, seed 42, immigration topic, llama3.2 via Ollama.
- 4.2 general_only, tom_only, full_kg: in progress, same configuration, to run on a DGX server via vLLM.
- 4.3 Annotator-context ablation (general_only_ctx, tom_only_ctx, full_kg_ctx): planned, gated on a small code change (see Section 6), testing whether giving the annotator limited visibility into the partner's argument changes the scored outcome.
- 4.4 Second topic and neutral control topic: planned, to test whether findings generalize beyond immigration policy specifically.

## 5. Results (skeleton, to fill in once ablation completes)

- Entropy over time, all four conditions on one plot.
- Acceptance-by-stance-gap curve, all four conditions overlaid, to directly test whether KG conditions flatten the curve relative to no_kg.
- Left-drift magnitude by condition, since the no_kg baseline shows a large directional confound this needs to be reported as a covariate, not ignored.
- Transition matrices, one per condition.

## 6. Discussion (skeleton)

- Direct answer to the hypothesis: does any memory condition reduce selective agreement, and if so, which one, and by how much.
- Whether the directional left-drift confound is present, absent, or changed in magnitude across conditions, since that speaks to whether memory dampens model-prior-driven drift specifically or only dampens partner-driven agreement.
- The `round` field / GhostKG metadata finding as a reproducibility note for anyone extending this framework.
- Open question flagged for future work: whether FSRS, built for factual spaced repetition, is the right decay model for socially-situated belief memory, or whether a different decay curve should be tested.

## 7. Limitations (skeleton)

- Single base model (llama3.2) for the completed baseline; cross-model generalization untested until multiple model families are run.
- Single topic completed at time of writing; generalization across topic types (polarizing, moderately divisive, neutral) is planned but not yet demonstrated.
- Annotator-based stance scoring is itself a model judgment, not a ground-truth measurement; annotator biases are a confound shared with the source LODAS framework.
- Population size (140) is larger than prior work but still far smaller than real social networks; no claim is made about the KG conditions' effect at internet-scale populations.

## 8. Conclusion (skeleton)

- Restate the hypothesis test outcome once available.
- State what generalizes and what appears specific to this topic, model, and population size.
- Point to the next paper-worthy extension (second topic, cross-model replication, or the annotator-context finding) as the natural next contribution.

---

## Notes for next writing session

- Every empirical claim in Sections 5 through 8 needs the actual ablation numbers before it can be written. Do not draft those sections speculatively; wait for `general_only`, `tom_only`, `full_kg` to complete.
- Related work section needs real citations selected and checked, not placeholder claims. Do not cite anything not actually read.
- Once the DGX run completes, rerun the baseline analysis script against all four conditions together to produce the comparison plots this paper needs (see `analysis/plots.py --data-dir data/immigration` once all four condition directories exist under one topic folder).
