# Conditions and implementation

This document explains the four memory conditions used in the ablation, what distinguishes them mechanically, and how they connect to the research question in `hypothesis_and_scope.md`. It is reference material, not a paper section.

## Why four conditions

The research question is whether persistent, structured, decaying memory changes the selective-agreement pattern LLM agents show in pairwise debate, relative to a memoryless baseline (Cau et al. 2025, LODAS framework). The hypothesis is more specific than "memory helps": it claims that memory of a partner's stated beliefs (theory-of-mind memory) reduces unconditional agreement more than memory of facts alone, and that combining facts, theory-of-mind, and self-belief tracking produces the most stable opinions over time.

Testing that claim requires isolating what kind of memory is doing the work, not just whether memory is present. Four conditions do this: one baseline with no memory at all, and three memory conditions that each turn on a different combination of content types. All four conditions share the same population, topic, seed, and simulation length; memory content is the only variable.

## no_kg: no memory (baseline)

Conceptually, this is the memoryless condition. An agent enters every exchange with no record of anything said in a prior exchange, by itself or by any partner.

In code, `no_kg` uses `NullMemory`, one of the two concrete implementations of the abstract `AgentMemory` interface in `src/memory.py`. Both of `NullMemory`'s methods, `absorb()` and `get_context()`, are no-ops. Nothing is extracted after an exchange, and nothing is injected into the next prompt. Which memory class gets instantiated is decided once, at startup, in `simulation.py::_build_memory()`; no other file branches on memory condition, so this is the only place the difference between conditions originates.

## general_only: facts

Conceptually, this condition gives an agent memory of factual content raised in conversation, general claims about the topic, without any record of what a specific partner believes.

In code, `general_only` uses `GhostMemory`, the second concrete implementation of `AgentMemory`. `GhostMemory` takes a `dimensions` list that determines which KG dimensions are active; for `general_only` this list is `["general"]`. On `absorb()`, `GhostMemory` extracts triplets via an LLM call, one per active dimension, so with only `"general"` active, only general-dimension triplets are extracted, each written into GhostKG through `manager.absorb_content()`. On `get_context()`, `GhostMemory` retrieves relevant prior triplets from GhostKG and formats them for injection into the next prompt. Because only the general dimension is active, retrieval can only surface general-dimension triplets.

## tom_only: theory of mind

Conceptually, this condition gives an agent memory of inferred beliefs about a specific conversation partner, not memory of general facts about the topic.

In code, `tom_only` uses the same `GhostMemory` class as `general_only`, with `dimensions` set to `["tom"]` instead of `["general"]`. The extraction call, the write path through `manager.absorb_content()`, and the retrieval path through `get_context()` are structurally identical to `general_only`. The only difference is which dimension is active and therefore which triplets get extracted and retrieved.

### What "theory of mind" means specifically in this codebase

This is not the general philosophical or cognitive-science sense of theory of mind. In this codebase it refers to one specific thing: an inferred belief about what a specific conversation partner believes, extracted as a `(subject, predicate, object)` triplet and tagged with `dimension="tom"`.

Each triplet produced by extraction is `(subject, predicate, object, dimension, round)` per `src/triplets.py`. The `dimension` field is what tags a triplet as `"tom"` versus `"general"` versus `"beliefs"`. A `"tom"` triplet encodes belief-about-partner content (what the partner appears to think); a `"general"` triplet encodes belief-about-topic content (a fact stated in the exchange, independent of who holds it). The `round` field records the simulated day the triplet was extracted on; it is retained in the project's own logs for analysis but is stripped before the triplet is handed to GhostKG's `absorb_content()`, which only accepts `(subject, predicate, object)`.

Mechanically, `tom_only` and `general_only` differ in exactly one place: the `dimensions` list passed to `GhostMemory` at construction. That list controls which dimension the extraction LLM call is run for, which in turn controls what gets written to GhostKG and what can later be retrieved. Storage and retrieval code paths are identical between the two conditions. The distinction is entirely in what content is tagged and extracted, not in how it is stored, decayed, or retrieved.

## full_kg: general + tom + beliefs combined

Conceptually, this condition combines factual memory, theory-of-mind memory about the partner, and the agent's own stated beliefs (self-belief tracking), all at once.

In code, `full_kg` uses `GhostMemory` with `dimensions` set to `["general", "tom", "beliefs"]`. `absorb()` runs one extraction LLM call per active dimension, so three extraction calls happen per absorbed turn instead of one, each tagged with its own dimension and written to GhostKG separately. `get_context()` retrieves and formats prior triplets across all three dimensions for injection into the next prompt.

## FSRS decay applies uniformly across all three KG conditions

Decay is not a variable across `general_only`, `tom_only`, and `full_kg`. GhostKG applies FSRS (a spaced-repetition scheduling algorithm) to triplet strength, keyed on the simulated clock, which is set via `manager.set_agent_time(agent_id, clock)`, called once per day with the simulated date. Older, less-reinforced triplets retrieve with lower weight over simulated time. This mechanism is identical regardless of which dimensions are active; it operates on whatever triplets exist in GhostKG for a given agent, without regard to whether those triplets came from the general, tom, or beliefs dimension. The `round` field on the project's own `Triplet` dataclass is not an input to this decay mechanism; decay is driven entirely by `set_agent_time()`, separately from the extraction dimension list. The specific FSRS parameters in use are GhostKG's defaults; this project has not tuned them.

The practical implication: what differs between `general_only`, `tom_only`, and `full_kg` is exclusively which dimensions are extracted and retrieved. The decay curve applied to whatever triplets exist is the same curve in all three conditions.
