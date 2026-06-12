# GhostKG Opinion Dynamics

A simulation framework that studies how **structured, decaying memory** affects opinion formation in populations of LLM agents. Extends the LODAS framework from Cau et al. (2025, *EPJ Data Science*) by adding GhostKG — a per-agent knowledge graph whose memories decay over simulated time using the FSRS spaced-repetition algorithm.

**Research question:** Does a knowledge graph memory help LLM agents stay in-character as opinions shift, compared to a no-memory baseline? Does memory reduce or amplify the selective-agreement patterns found in the EPJ paper?

**Research collaboration:** Pranav Deepak & Dr. Giulio Rossetti (KDD Lab, CNR Italy / University of Pisa)

---

## Table of contents

- [GhostKG Opinion Dynamics](#ghostkg-opinion-dynamics)
  - [Table of contents](#table-of-contents)
  - [How it works](#how-it-works)
  - [Project structure](#project-structure)
  - [Flow of control](#flow-of-control)
  - [Data types and storage](#data-types-and-storage)
    - [Core enums (`config.py`)](#core-enums-configpy)
    - [`results.csv` — one row per iteration](#resultscsv--one-row-per-iteration)
    - [`exchanges.jsonl` — one JSON object per iteration](#exchangesjsonl--one-json-object-per-iteration)
  - [Memory conditions](#memory-conditions)
  - [Install](#install)
  - [Configure](#configure)
  - [Run](#run)
    - [Quick test (3 iterations, 4 agents)](#quick-test-3-iterations-4-agents)
    - [Baseline run (no memory)](#baseline-run-no-memory)
    - [Full ablation study](#full-ablation-study)
  - [Generate analysis plots](#generate-analysis-plots)
    - [All conditions compared](#all-conditions-compared)
    - [Single condition](#single-condition)
    - [From Python](#from-python)
  - [Understanding the output](#understanding-the-output)
    - [Metrics defined in `analysis/metrics.py`](#metrics-defined-in-analysismetricspy)
    - [Reading the acceptance matrix](#reading-the-acceptance-matrix)
  - [Change the topic](#change-the-topic)
  - [Add a new LLM provider](#add-a-new-llm-provider)
  - [Use vLLM](#use-vllm)
  - [Crash recovery](#crash-recovery)
  - [Reference](#reference)

---

## How it works

At each simulation **iteration**:

1. Two agents are picked at random from the population.
2. They hold a **multi-turn dialogue** (2–5 turns). Each agent is given their persona, current stance, and memories retrieved from their knowledge graph.
3. After the dialogue, a **third annotator LLM** reads each agent's utterances and assigns a Likert stance on a 5-point scale: *Strongly Against → Against → Neutral → In Favor → Strongly In Favor*.
4. KG-enabled agents **absorb the dialogue** into their knowledge graph. GhostKG extracts subject-predicate-object triplets and stores them with FSRS decay — memories fade if not reinforced.
5. Stances are logged. Repeat for N iterations.

This reproduces the core LODAS loop and adds the GhostKG memory layer on top, enabling direct comparison between conditions.

---

## Project structure

```
.
├── src/
│   ├── config.py        All data types (enums, dataclasses), config loading, validation
│   ├── personas.py      12 hardcoded agent personas for immigration policy
│   ├── prompts.py       All 6 prompt templates as typed, frozen dataclasses
│   ├── llm.py           Async LLM dispatch — Ollama / Anthropic / OpenAI / Groq / vLLM
│   ├── memory.py        AgentMemory interface, NullMemory, GhostMemory
│   ├── triplets.py      LLM-based triplet extraction for the knowledge graph
│   ├── exchange.py      Multi-turn dialogue loop (condition-blind)
│   ├── annotator.py     Third-party stance annotator (bias-prevented)
│   ├── tracker.py       CSV + JSONL logging
│   ├── checkpoint.py    Crash recovery
│   └── simulation.py   Entry point — owns the main loop
│
├── analysis/
│   ├── metrics.py       All EPJ paper metrics (entropy, acceptance matrices, etc.)
│   └── plots.py         All plot functions + CLI
│
├── data/                Created at runtime — gitignored
│   └── .gitkeep
│
├── .env.example         Safe config template — copy to .env and fill in values
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Flow of control

Exact call chain for one complete simulation run, top to bottom:

```
python src/simulation.py
    │
    ├── load_config()                        # config.py
    │   ├── reads .env
    │   ├── _validate_config()               # fails fast with ALL errors at once
    │   └── _smoke_test_prompts()            # renders every prompt with dummy values
    │
    ├── create_personas()                    # personas.py → list[AgentPersona]
    │
    ├── load_checkpoint()                    # checkpoint.py
    │   └── if crash found: restore_db_backup + rebuild_stances from CSV
    │
    ├── AgentManager(db_path)                # GhostKG: opens/creates SQLite KG
    │   └── create_agent() × N              # register every agent
    │
    ├── _build_memory()                      # simulation.py (only place that reads memory_condition)
    │   ├── NullMemory()         ← no_kg
    │   └── GhostMemory(manager) ← all other conditions
    │
    └── for iteration in 1..N_ITERATIONS:
        │Hi Giulio,

Sharing the first full results from the GhostKG extension of LODAS. All four memory conditions are done, 5 plots attached.

---

SETUP

- 12 agents across political leanings, immigration policy topic
- 50 iterations per condition, 2 to 5 turns per exchange, llama3.2 local
- Annotator: separate LLM pass reading only that agent's utterances (bias-prevented)
- 4 conditions: no_kg (LODAS baseline), general_only (topic facts), tom_only (Theory of Mind), full_kg (all three)

---

KEY FINDINGS

1. Full KG shows the most stability. Entropy growth is lowest in full_kg (+0.38) vs the no-memory baseline (+0.85). Structured memory makes opinions harder to shift.

2. ToM alone amplifies disagreement. tom_only has the highest entropy growth (+1.19). Agents who track each other's stances push back harder, not softer.

3. Acceptance bias reverses under general KG. In the EPJ paper, agents accept opinions farther from their own at higher rates (positive delta-x bias). Our no-memory baseline barely replicates this (+0.008). With general_only, the bias flips negative (-0.175). Factual knowledge seems to make agents more resistant to opposing views, not more open. [compare_acceptance_distance.png]

4. Extreme single-exchange shifts happen. In tom_only iteration 1, Patricia (far-right, Strongly In Favor) moved to Strongly Against after a 2-turn exchange with Marcus (far-left). A 4-point shift in 2 turns. Marcus reframed immigration restriction as class exploitation, not a culture argument. [journey_patricia_tom_only.png]

5. Extreme stances collapse in every condition. Strongly In Favor and Neutral both approach 0% by iteration 50. Population concentrates at Against / In Favor regardless of memory type. [compare_trajectories.png]

---

ATTACHED PLOTS

1. compare_trajectories.png — stance proportions over time, 4 conditions side by side
2. compare_entropy.png — Shannon entropy H(t), all conditions on one chart
3. compare_acceptance_distance.png — P(accept | delta-x) per condition, the EPJ Figure 4 equivalent
4. journey_patricia_tom_only.png — Patricia's full opinion trace, red dots mark changes
5. compare_effective_clusters.png — C(t) = N^2 / sum(n_i^2), how many opinion clusters exist at each step

---

QUESTIONS

1. Entropy is still rising at iteration 50 in all conditions. At what iteration count did you see convergence onset in the EPJ runs? Should we go to 100 to 200 iterations before drawing conclusions?

2. Our no-memory baseline does not replicate the EPJ positive delta-x bias (+0.008 vs your consistent positive effect). Is this model-specific (llama3.2 vs GPT-4), topic-specific, or population size? Worth running a direct comparison?

3. ToM is encoded as (speaker, believes, X) triplets extracted per utterance. Is this the right operationalisation or should ToM state be tracked at the agent level rather than per-utterance?

---

NEXT STEPS

- 3 additional seeds per condition for variance estimates before drawing any conclusions
- 100-iteration rerun (convergence onset is unknown from 50 iterations)
- Inspect the actual GhostKG triplets being stored (qualitative check on signal vs noise)
- Leaning-pair breakdown of acceptance rates (left-right, far_left-center, etc.)

Raw CSVs and exchanges.jsonl available if useful. Full codebase runs locally with Ollama, no API keys needed.

Best,
Pranav
        ├── backup_db(iteration-1)           # snapshot SQLite before touching it
        ├── clock += 24h                     # advance FSRS simulated time
        ├── select_pair(rng)                 # random 2 agents from population
        │
        ├── run_exchange(agent_a, agent_b)   # exchange.py
        │   └── for turn in 1..n_turns:
        │       ├── build system prompt      # agent persona + current stance
        │       ├── build user prompt        # KG context + exchange history
        │       ├── llm_call()               # llm.py
        │       ├── memory.absorb(listener)  # memory.py
        │       │   └── [GhostMemory] extract_triplets() → manager.absorb_content()
        │       └── append ExchangeTurn
        │
        ├── annotate(agent_a, exchange_log)  # annotator.py → LikertStance
        ├── annotate(agent_b, exchange_log)  # annotator.py → LikertStance
        │
        ├── current_stances[a] = stance_a   # in-memory dict, never re-read from disk
        ├── current_stances[b] = stance_b
        │
        ├── tracker.log(iteration, …)        # → results.csv + exchanges.jsonl
        └── write_checkpoint(iteration)      # only AFTER log succeeds
```

**Key design principle:** Every module has exactly one job.
- `exchange.py` never knows which memory condition is active — it receives an `AgentMemory` via dependency injection (Null Object Pattern).
- `annotator.py` never touches the knowledge graph.
- `simulation.py` is the **only** place that reads `memory_condition`.

---

## Data types and storage

### Core enums (`config.py`)

```python
class LikertStance(Enum):
    STRONGLY_AGAINST  = ("Strongly Against",  -2)
    AGAINST           = ("Against",           -1)
    NEUTRAL           = ("Neutral",            0)
    IN_FAVOR          = ("In Favor",           1)
    STRONGLY_IN_FAVOR = ("Strongly In Favor",  2)
    # Access via: stance.label → "Against"  |  stance.score → -1

class PoliticalLeaning(str, Enum):
    FAR_LEFT | LEFT | CENTER | RIGHT | FAR_RIGHT

class MemoryCondition(str, Enum):
    NO_KG | GENERAL_ONLY | TOM_ONLY | FULL_KG
```

### `results.csv` — one row per iteration

| Column | Description |
|--------|-------------|
| `iteration` | Iteration number (1-indexed) |
| `run_id` | Unique run identifier (timestamp) |
| `memory_condition` | Which ablation condition (`no_kg`, `full_kg`, …) |
| `topic` | The discussion topic |
| `agent_a_id` / `agent_b_id` | Agent identifiers |
| `agent_a_name` / `agent_b_name` | Display names |
| `agent_a_leaning` / `agent_b_leaning` | Political leaning |
| `agent_a_stance_before_label` | Likert label **before** exchange |
| `agent_a_stance_before_score` | Integer score (-2 to +2) before |
| `agent_a_stance_after_label` | Likert label **after** exchange |
| `agent_a_stance_after_score` | Integer score after |
| *(same four columns for agent_b)* | |
| `n_turns` | Number of turns in this exchange |
| `sim_clock` | Simulated timestamp |

The `_before` and `_after` columns are what make the acceptance/rejection matrices computable, matching EPJ Figure 4.

### `exchanges.jsonl` — one JSON object per iteration

Each line is the full conversation transcript for that iteration:

```json
{
  "iteration": 1,
  "run_id": "20260101T120000",
  "memory_condition": "no_kg",
  "topic": "immigration policy",
  "agent_a": {"id": "agent_01", "name": "Jordan", "leaning": "left"},
  "agent_b": {"id": "agent_07", "name": "Marcus", "leaning": "right"},
  "agent_a_stance_before": "Neutral",
  "agent_a_stance_after": "Against",
  "agent_b_stance_before": "In Favor",
  "agent_b_stance_after": "In Favor",
  "n_turns": 3,
  "sim_clock": "2026-01-02T00:00:00+00:00",
  "turns": [
    {"turn": 1, "speaker_id": "agent_01", "speaker_name": "Jordan", "utterance": "…"},
    {"turn": 2, "speaker_id": "agent_07", "speaker_name": "Marcus", "utterance": "…"},
    {"turn": 3, "speaker_id": "agent_01", "speaker_name": "Jordan", "utterance": "…"}
  ]
}
```

---

## Memory conditions

| Condition | `MEMORY_CONDITION` | What agents remember |
|-----------|-------------------|----------------------|
| Baseline | `no_kg` | Nothing — pure replication of LODAS |
| General KG | `general_only` | Facts about the topic extracted from conversations |
| ToM KG | `tom_only` | What they infer about each other's views (Theory of Mind proxy) |
| Full KG | `full_kg` | All three: topic facts + ToM + own stated beliefs |

GhostKG stores each memory as a subject-predicate-object triplet and applies FSRS decay. Each iteration advances the simulated clock by 24 hours, so older memories fade unless reinforced by later conversations.

---

## Install

```bash
git clone <repo-url>
cd Agentic-Stance

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env             # then edit .env with your settings
```

> **No `__pycache__`:** `PYTHONDONTWRITEBYTECODE=1` is set in `.env.example` and `sys.dont_write_bytecode = True` is set at the top of every entry point. Python will never write bytecode files anywhere in this project.

---

## Configure

All settings live in `.env`:

```bash
# LLM provider
LLM_PROVIDER=ollama          # ollama | anthropic | openai | groq | vllm
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:8000/v1   # used by vLLM and other OpenAI-compatible servers
LLM_MAX_TOKENS=512
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.95
LLM_MAX_CONCURRENCY=8        # per-process request concurrency for batch-aware providers
PARALLEL_EXCHANGE_JOBS=1     # >1 activates the disjoint-exchange scheduler

# Simulation
TOPIC=immigration policy
N_AGENTS=12
N_ITERATIONS=50
MIN_TURNS=2
MAX_TURNS=5
RANDOM_SEED=42               # fixed seed → reproducible pair selection

# Memory
MEMORY_CONDITION=no_kg       # no_kg | general_only | tom_only | full_kg
CLOCK_ADVANCE_HOURS=24       # FSRS decay fires every 24 simulated hours

# Output (created automatically)
OUTPUT_DIR=data/no_kg
DB_PATH=data/no_kg/simulation.db

# API keys — only needed for the respective provider
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GROQ_API_KEY=...
```

**Provider quick-start:**

| Provider | What to set |
|----------|-------------|
| **Ollama** (default, local, free) | Install from [ollama.com](https://ollama.com), run `ollama serve`, run `ollama pull llama3.2` |
| **Groq** (fast API, generous free tier) | `LLM_PROVIDER=groq`, `LLM_MODEL=llama3-8b-8192`, set `GROQ_API_KEY` |
| **Anthropic** | `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-3-haiku-20240307`, set `ANTHROPIC_API_KEY` |
| **OpenAI** | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`, set `OPENAI_API_KEY` |
| **vLLM** | `LLM_PROVIDER=vllm`, `LLM_MODEL=<served-model-name>`, set `LLM_BASE_URL` to the OpenAI-compatible endpoint |

---

## Run

### Quick test (3 iterations, 4 agents)

```bash
N_AGENTS=4 N_ITERATIONS=3 OUTPUT_DIR=data/test DB_PATH=data/test/sim.db python src/simulation.py
```

Check `data/test/results.csv` has 3 rows, `exchanges.jsonl` has 3 records.

### Baseline run (no memory)

```bash
# .env has MEMORY_CONDITION=no_kg
python src/simulation.py
```

### Full ablation study

```bash
MEMORY_CONDITION=no_kg        OUTPUT_DIR=data/no_kg        DB_PATH=data/no_kg/sim.db        python src/simulation.py
MEMORY_CONDITION=general_only OUTPUT_DIR=data/general_only DB_PATH=data/general_only/sim.db python src/simulation.py
MEMORY_CONDITION=tom_only     OUTPUT_DIR=data/tom_only     DB_PATH=data/tom_only/sim.db     python src/simulation.py
MEMORY_CONDITION=full_kg      OUTPUT_DIR=data/full_kg      DB_PATH=data/full_kg/sim.db      python src/simulation.py
```

### vLLM

`vLLM` works in two practical modes:

1. **Without explicit batching**: point the existing simulation at a `vllm` server and run normally.
2. **With batching enabled**: use the batch-aware paths already wired into annotation and triplet extraction; vLLM batches concurrent requests on the server side.

Minimal environment setup:

```bash
LLM_PROVIDER=vllm
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
LLM_BASE_URL=http://127.0.0.1:8000/v1
```

#### 1. vLLM without batching

This keeps the standard sequential simulation flow:

```bash
LLM_PROVIDER=vllm LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct LLM_BASE_URL=http://127.0.0.1:8000/v1 \
  python src/simulation.py
```

#### 2. vLLM with batching

Batching is already active where it matters:

- `annotator.py` batches the two stance judgements per exchange
- `triplets.py` batches extraction requests per utterance/dimension set
- `llm.py` uses bounded concurrent requests, which vLLM batches on the server

Example with a higher per-process concurrency cap:

```bash
LLM_PROVIDER=vllm \
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct \
LLM_BASE_URL=http://127.0.0.1:8000/v1 \
LLM_MAX_CONCURRENCY=16 \
python src/simulation.py
```

#### 3. Parallel exchange jobs

Set `PARALLEL_EXCHANGE_JOBS` above `1` to activate the disjoint-exchange scheduler:

```bash
LLM_PROVIDER=vllm \
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct \
LLM_BASE_URL=http://127.0.0.1:8000/v1 \
PARALLEL_EXCHANGE_JOBS=4 \
python src/simulation.py
```

For independent exchange workloads outside the main simulation loop, use `run_exchange_jobs()` directly:

```python
import asyncio
from exchange import ExchangeJob, run_exchange_jobs

jobs = [ExchangeJob(...), ExchangeJob(...)]
results = asyncio.run(run_exchange_jobs(jobs))
```

This is the intended entry point for parallelizing exchange-level workloads that do not share mutable stance state.

---

## Generate analysis plots

### All conditions compared

```bash
python analysis/plots.py --data-dir data/ --output-dir data/plots/
```

Requires `data/{no_kg,general_only,tom_only,full_kg}/results.csv`. Produces:
- `compare_trajectories.png` — opinion trajectory per condition (4 panels)
- `compare_entropy.png` — entropy H(t) per condition on one chart
- `compare_acceptance_distance.png` — P(A|Δx) per condition on one chart

### Single condition

```bash
python analysis/plots.py --data-dir data/ --output-dir data/plots/ --condition no_kg
```

Produces:
- `trajectory_no_kg.png` — proportion of agents at each stance over time
- `distribution_no_kg.png` — stacked area chart of stance composition
- `acceptance_matrix_no_kg.png` — heatmap of P(accept | Discussant=i, Opponent=j)
- `acceptance_distance_no_kg.png` — P(A|Δx) line chart
- `convergence_no_kg.png` — entropy H(t) and std deviation σ(t) side by side

### From Python

```python
import pandas as pd
from analysis.metrics import compute_all_metrics
from analysis.plots import plot_trajectory, plot_acceptance_matrix

df = pd.read_csv("data/no_kg/results.csv")
metrics = compute_all_metrics(df)          # dict with all metric objects
plot_trajectory(df, "data/plots", "no_kg")
plot_acceptance_matrix(df, "data/plots", "no_kg")
```

---

## Understanding the output

### Metrics defined in `analysis/metrics.py`

| Metric | What it tells you |
|--------|------------------|
| **Opinion trajectory** P_x(t) | How the distribution of stances evolves over time |
| **Entropy** H(t) = −Σ p_i log₂ p_i | Opinion diversity. Declining → convergence toward fewer positions |
| **Std deviation** σ(t) | Spread around the mean stance. Declining → clustering |
| **Effective clusters** C(t) = N²/Σn_i² | Number of meaningfully-sized opinion groups |
| **Transition matrix** T_ij | How often agents move from stance i to stance j |
| **Acceptance matrix** A_ij | Probability a Discussant with stance i moves toward an Opponent with stance j |
| **P(A\|Δx)** | Acceptance rate by signed opinion distance. The EPJ finding: does Δx > 0 predict higher acceptance? |

### Reading the acceptance matrix

Rows = Discussant's starting stance. Columns = Opponent's stance. Cell value = probability the Discussant moved toward the Opponent. High values above the diagonal mean agents tend to move in a positive direction regardless of their own stance — a sign of asymmetric persuasion bias.

---

## Change the topic

Only two files need to change:

1. **`.env`** — set `TOPIC=environmental policy` (or any topic)
2. **`src/personas.py`** — update `initial_stance` for each persona to reflect realistic priors on the new topic

Everything else — prompts, annotator, tracker, analysis — picks up the `topic` string from config automatically. No other code changes needed.

---

## Add a new LLM provider

All provider logic is in `src/llm.py`. Two steps:

**1. Add the function:**
```python
async def _call_myprovider(system: str, user: str, model: str) -> str:
    try:
        import myprovider_sdk
        import os
        client = myprovider_sdk.AsyncClient(api_key=os.environ["MYPROVIDER_API_KEY"])
        response = await client.chat(model=model, messages=[...])
        return response.text.strip()
    except Exception as exc:
        raise LLMError(f"MyProvider call failed: {exc}") from exc
```

**2. Add the branch in `llm_call()`:**
```python
elif config.llm_provider == "myprovider":
    return await _call_myprovider(system, user, config.llm_model)
```

**3. Register it in `config.py`:**
```python
SUPPORTED_PROVIDERS = {"ollama", "anthropic", "openai", "groq", "vllm", "myprovider"}
```

No other files change.

`vLLM` is already wired in as an OpenAI-compatible backend, so you only need to point `LLM_PROVIDER=vllm` at a running endpoint.

---

## Use vLLM

`vLLM` is supported through the same entry point as the other providers. The difference is how much concurrency you allow:

- `LLM_MAX_CONCURRENCY=1` keeps requests effectively serial from the client side.
- `LLM_MAX_CONCURRENCY>1` lets the backend batch concurrent requests.

Minimal examples:

```bash
# Sequential client-side behavior
LLM_PROVIDER=vllm LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct LLM_BASE_URL=http://127.0.0.1:8000/v1 \
  LLM_MAX_CONCURRENCY=1 python src/simulation.py

# Batch-friendly behavior
LLM_PROVIDER=vllm LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct LLM_BASE_URL=http://127.0.0.1:8000/v1 \
  LLM_MAX_CONCURRENCY=16 python src/simulation.py
```

If you want to parallelize independent exchanges directly, build `ExchangeJob` objects and run them with `run_exchange_jobs()` from `src/exchange.py`.

---

## Crash recovery

The simulation is designed to be crash-safe. If it dies mid-run:

1. **SQLite is backed up before each iteration** (`backup_db()`). GhostKG data is never lost.
2. **The checkpoint records the last successfully logged iteration** (`write_checkpoint()` only fires after `tracker.log()` succeeds).
3. **On restart**, the simulation automatically:
   - Restores the SQLite DB to the last safe backup
   - Reads the checkpoint to find where to resume
   - Rebuilds the in-memory stances dict from `results.csv`
   - Continues from the next iteration with no duplicate rows

To resume a crashed run, simply re-run the same command. No flags needed.

---

## Reference

Cau, E., Pansanella, V., Pedreschi, D., & Rossetti, G. (2025). Selective agreement, not sycophancy: investigating opinion dynamics in LLM interactions. *EPJ Data Science*, 14, 59. https://doi.org/10.1140/epjds/s13688-025-00579-1

Rossetti, G. et al. GhostKG. https://github.com/GiulioRossetti/GhostKG
