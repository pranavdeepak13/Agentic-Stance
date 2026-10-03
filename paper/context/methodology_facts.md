# Methodology facts

Every claim here is traceable to a specific file in the repository. The
methodology section may only state what is written here or what a writer
has personally re-verified against the named file. Do not extrapolate
behavior that is not shown below.

## Open discrepancy: exchange cadence (flagged 2026-09-03, needs verification)

The results delivered from the DGX run (`results/*.csv`, imported via
`scripts/import_condition_results.py`) show 100,800 rows per condition
over 30 days: 140 agents x 24 hours x 30 days, with explicit `day_id`
and `hour_id` columns. This means each agent exchanged roughly once per
simulated hour, not once per simulated day as described below and as
the current `src/simulation.py` in this repository implements.

Rossetti mentioned fixing "a few minor issues" before running on the
DGX, but the actual diff has not been shared or pulled into this repo
yet. Until it is, the "Simulation loop" section below describes what
this repository's own `src/simulation.py` does, which does not match
the cadence of the delivered data. Do not write the methodology section
from this document until that diff is obtained and this section is
reconciled with it. Ask Rossetti directly for the commit or patch
rather than inferring the mechanism from the CSV shape alone, since the
CSV only tells us the row-level output, not how the loop that produced
it is structured (e.g. whether it is still one random partner per
agent per hour, whether `CLOCK_ADVANCE_HOURS` changed, whether
checkpointing changed cadence too).

### Partial resolution from the data itself (2026-09-30)

The loop code is still unconfirmed. The following facts are verified directly
from the four delivered CSVs by `scripts/compute_paper_numbers.py` and can be
stated in the paper as properties of the delivered data (see
`reports/full_ablation_summary.md`, Section 1):

- 30 simulated days x 24 rounds per day = 720 rounds per condition.
- The `sim_clock` value advances by exactly one simulated hour per round.
- Every round contains exactly 140 exchanges, and each of the 140 agents is
  the initiator of exactly one of them. The "one initiated exchange per
  agent per round" structure below therefore still holds, with a round
  lasting one simulated hour instead of one simulated day.
- Being picked as a partner is unbounded, as below (1 to 8 times in a round
  when picked).
- The pairing schedule and the per-exchange turn counts are identical across
  all four conditions, row for row.
- No single update changes a stance by more than one step, so the clamp was
  active.

Still unknown, pending Rossetti's diff: how often `set_agent_time()` is
called (per round or per day), where `backup_db()` and `write_checkpoint()`
fire, whether any other change was made to prompts, the topic string (the
CSV's `topic` value is "immigration", this repo uses "immigration policy"),
or the annotator, and which model vLLM served.

Approved wording for the Methods section until the diff arrives: "In the
delivered runs, each agent initiated one exchange per simulated hour with a
uniformly random partner, for 24 rounds per simulated day over 30 days. This
cadence is recovered from the logged data; the exact loop implementation used
on the collaborator's infrastructure is pending confirmation."

## Simulation loop (src/simulation.py), as implemented in this repo, may be stale

One iteration equals one simulated day. At the start of each day:

1. All agents are shuffled into a fresh random order (`day_order`).
2. Each agent, taken in that order, initiates exactly one exchange with a
   uniformly random partner drawn from the remaining population.
3. `backup_db()` snapshots the GhostKG SQLite file before that day's
   exchanges run, into `simulation_iter_{day-1}.db.bak`.
4. The simulated clock advances by `CLOCK_ADVANCE_HOURS` (default 24).
5. After every agent has initiated one exchange, `write_checkpoint(day)`
   writes `checkpoint.json` once for the whole day, not once per exchange.

This design guarantees equal daily participation: no agent can be
excluded from a day, and no agent can appear twice as an initiator on the
same day. Being chosen as a partner is unbounded (an agent can be a
partner zero, one, or multiple times per day).

## One exchange (src/exchange.py)

`run_exchange()` runs 2 to 5 turns (`MIN_TURNS`, `MAX_TURNS`, drawn once
per exchange), alternating utterances between the initiator and partner.
Both agents' turns are dispatched together through `llm_call_many()`.
After each turn, `memory.absorb()` is called for whichever agent is
listening. `exchange.py` holds no branch on memory condition; it is
written entirely against the `AgentMemory` interface.

## Stance annotation and the clamp (src/annotator.py)

After an exchange completes, a separate LLM call reads only the utterances
belonging to the agent being scored, never the partner's utterances, to
prevent partner argument content from directly biasing the score. The
returned Likert score is then clamped:

```
clamped = max(previous.score - 1, min(previous.score + 1, parsed.score))
```

An agent can move at most one step (out of five possible: -2 to +2) per
exchange, in either direction. This clamp was added after an unconstrained
run produced a single-exchange shift from one extreme of the scale to the
opposite extreme, which was treated as a defect in the scoring mechanism,
not a plausible model of real opinion change.

## Memory conditions (src/memory.py)

`AgentMemory` is an abstract interface with two methods: `absorb()` and
`get_context()`. Two concrete implementations exist:

- `NullMemory`: both methods are no-ops. Used for `no_kg`.
- `GhostMemory`: `absorb()` extracts triplets via an LLM call, one per
  active KG dimension, then writes them to GhostKG via
  `manager.absorb_content()`. `get_context()` retrieves relevant prior
  triplets from GhostKG and formats them for injection into the next
  prompt.

Which class is instantiated is decided once, at startup, in
`simulation.py::_build_memory()`. No other file branches on memory
condition.

`GhostMemory` takes a `dimensions` list that determines which KG
dimensions are active:

| Condition | dimensions |
|---|---|
| general_only | ["general"] |
| tom_only | ["tom"] |
| full_kg | ["general", "tom", "beliefs"] |

## Triplet extraction (src/triplets.py)

Each triplet is `(subject, predicate, object, dimension, round)`. The
`round` field records the simulated day the triplet was extracted on.
This field is populated on our own `Triplet` dataclass but is stripped
before the triple is handed to GhostKG's `absorb_content()`, which only
accepts `(subject, predicate, object)`. GhostKG's own recency/decay
mechanism does not depend on this field: it is driven separately by
`manager.set_agent_time(agent_id, clock)`, called once per day with the
simulated date. `round` is retained in our own logs for analysis only
(e.g. "which day was this fact learned"), not as an input to GhostKG's
FSRS decay.

## FSRS decay

GhostKG applies FSRS (a spaced-repetition scheduling algorithm) to
triplet strength, keyed on the simulated clock set via
`set_agent_time()`. Older, less-reinforced triplets retrieve with lower
weight over simulated time. The specific FSRS parameters used are
GhostKG's defaults; this project has not tuned them.

## Metrics (analysis/metrics.py)

All metrics match the definitions in Cau et al. (2025):

- `opinion_trajectory`: proportion of the population at each stance, per
  iteration
- `entropy`: Shannon entropy of that distribution over time, H(t)
- `std_deviation`: spread of opinion scores over time
- `effective_clusters`: effective number of distinct opinion clusters
- `transition_matrix`: empirical stance-update probabilities
- `acceptance_matrix` / `rejection_matrix`: P(accept or reject | own
  stance, partner stance)
- `acceptance_by_distance`: P(accept | stance distance), the primary
  metric for testing the selective-agreement hypothesis

## Population (topics/immigration.py)

140 personas, each with a unique name, age, occupation, and free-text
persona description. Initial stance is tied to the persona description,
not assigned independently at random, following a truncated-Gaussian
target distribution (14 far left, 28 left, 56 center, 28 right, 14 far
right).

## Reproducibility infrastructure

Checkpoint and crash recovery (src/checkpoint.py): `checkpoint.json`
records `last_completed_iteration`. On restart, if present, the
matching `.db.bak` is restored over the live SQLite file, in-memory
stances are rebuilt by replaying `results.csv`, and the day loop resumes
at `last_completed_iteration + 1`. The DGX ablation script
(`scripts/run_dgx_ablation.sh`) wraps this in a retry loop (up to 5
attempts per condition) and relies entirely on this existing mechanism
rather than reimplementing resume logic.

## Prompts and the stance scale (src/prompts.py, src/config.py, topics/immigration.py)

Added 2026-09-30, verified against the named files.

- Agent system prompt (`AgentSystemPrompt`): gives the agent its name, age,
  occupation, political leaning, free-text persona, the topic, and its
  current stance label. It says: "You may change your mind if you find their
  argument genuinely convincing, or you may push back if you disagree. Do not
  simply agree to be agreeable."
- Agent user prompt (`AgentUserPrompt`): when memory context is non-empty,
  it is injected under the header "Here is what you remember from previous
  conversations on this topic:". Under no_kg that block is absent. Replies
  are limited to 2 to 4 sentences.
- Annotator prompt (`AnnotatorSystemPrompt`, `AnnotatorUserPrompt`): tells
  the annotator to act as a neutral stance annotator, to report the stance
  the agent expressed rather than its own view, and to output one label from
  the five-point scale. The scale defines In Favor / Against relative to
  "the proposition".
- Triplet extraction prompt (`TripletSystemPrompt`): one call per active
  dimension. The dimension guidance is "facts about the topic, policies, or
  events mentioned" (general), "what the speaker believes about the other
  person's views or stance" (tom), and "the speaker's own stated positions,
  values, or opinions" (beliefs). It asks for 0 to 5 triplets of the form
  `subject | predicate | object`, 3 to 8 words per part, "only what is
  clearly stated, not inferred".
- The topic string passed to agents and annotator is `config.topic`, default
  "immigration policy". No proposition is stated. Neither the agent nor the
  annotator is told what In Favor means.
- Intended polarity, from the docstring of `topics/immigration.py`: "In
  Favor" means supporting restrictive immigration policy, and "Against"
  means pro-immigration. Personas with far-right leaning start at Strongly
  In Favor. Because the prompt never states the proposition, the paper must
  report stances by scale label and must not call either side
  pro-immigration. Report the missing proposition as a validity threat.
- The DGX data's `topic` column reads "immigration", not "immigration
  policy". Rossetti's code may have used a different topic string. This is
  unconfirmed.

## Run facts for the delivered ablation (verified from data, see reports/full_ablation_summary.md)

- One run per condition, `RANDOM_SEED=42` per `scripts/run_dgx_ablation.sh`.
  The data confirms that all four conditions share an identical pairing
  schedule and identical per-exchange turn counts, so seeded randomness
  governs pairing and turn counts. Differences between conditions come from
  memory content and from the LLM outputs.
- Model served on the DGX: unconfirmed. `scripts/DGX_RUNBOOK.md`
  recommends `meta-llama/Llama-3.1-8B-Instruct` via vLLM, and the repo
  default (`src/config.py`) is `llama3.2` via Ollama. Do not name a model
  for the DGX runs in the paper until Rossetti confirms it.
- GhostKG version installed in this repo: 0.2.0, which implements FSRS v6
  with 21 default parameters (`ghost_kg/memory/fsrs.py`). Whether the DGX
  run used the same version is unconfirmed.
