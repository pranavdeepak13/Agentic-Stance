# Methodology facts

Every claim here is traceable to a specific file in the repository. The
methodology section may only state what is written here or what a writer
has personally re-verified against the named file. Do not extrapolate
behavior that is not shown below.

## Simulation loop (src/simulation.py)

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
