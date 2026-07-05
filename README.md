# GhostKG Opinion Dynamics

A simulation framework for studying how structured, decaying memory affects opinion formation in populations of LLM agents. Extends the LODAS framework (Cau et al. 2025, *EPJ Data Science*) with GhostKG: a per-agent knowledge graph whose memories decay over simulated time using the FSRS spaced-repetition algorithm.

**Research question:** Does knowledge graph memory help LLM agents stay in-character as opinions shift? Does memory reduce or amplify the selective-agreement patterns documented in the EPJ paper?

---

## Project structure

```
.
├── src/
│   ├── config.py        All data types, config loading, validation
│   ├── personas.py      Topic loader, AgentPersona dataclass
│   ├── prompts.py       All prompt templates
│   ├── llm.py           Async LLM dispatch (Ollama / Anthropic / OpenAI / Groq / vLLM)
│   ├── memory.py        AgentMemory interface, NullMemory, GhostMemory
│   ├── triplets.py      LLM-based KG triplet extraction
│   ├── exchange.py      Multi-turn dialogue loop
│   ├── annotator.py     Stance annotator with Likert clamp
│   ├── tracker.py       CSV + JSONL logging
│   ├── checkpoint.py    Crash recovery
│   └── simulation.py    Entry point — owns the main loop
│
├── analysis/
│   ├── metrics.py       EPJ metrics (entropy, acceptance matrices, etc.)
│   └── plots.py         All plot functions + CLI
│
├── topics/
│   └── immigration.py   140 agent personas for immigration policy topic
│
├── scripts/
│   └── gen_immigration_personas.py  Persona generator (run once)
│
├── docs/
│   └── index.html       Full documentation site (guide + API reference)
│
├── resources/           Reference papers and architecture notes
├── .env                 Config (gitignored)
├── .env.example         Safe config template
├── run_ablation.sh      Run all 4 conditions + generate plots
└── requirements.txt
```

---

## How it works

One simulation day:

1. All agents are shuffled into a random order.
2. Each agent initiates one multi-turn dialogue (2-5 turns) with a randomly chosen partner.
3. A separate annotator LLM reads each agent's own utterances and assigns a Likert stance (-2 to +2). Output is clamped to +-1 from prior stance.
4. KG-enabled agents absorb the dialogue into their knowledge graph. GhostKG stores subject-predicate-object triplets with FSRS decay.
5. Stances and transcripts are logged. Checkpoint written. Next day starts.

---

## Flow of control

```
python src/simulation.py
    |
    ├── load_config()                        # config.py: reads .env, validates all fields,
    |   |                                    # smoke-tests every prompt template
    |   ├── _validate_config()
    |   └── _smoke_test_prompts()
    |
    ├── create_personas()                    # personas.py -> list[AgentPersona]
    |
    ├── load_checkpoint()                    # checkpoint.py
    |   └── if crash found:
    |       ├── restore_db_backup()
    |       └── rebuild_stances() from CSV
    |
    ├── _init_ghostkg()                      # simulation.py (only for KG conditions)
    |   └── AgentManager(db_path)
    |       └── create_agent() x N
    |
    ├── _build_memory()                      # simulation.py (reads memory_condition ONCE)
    |   ├── NullMemory()          <- no_kg
    |   └── GhostMemory(manager) <- general_only / tom_only / full_kg
    |
    └── for day in 1..N_ITERATIONS:          # day-based loop (Phase 1 correction)
        ├── backup_db(day-1)                 # snapshot SQLite before touching it
        ├── clock += CLOCK_ADVANCE_HOURS
        |
        └── for initiator in shuffle(personas):
            ├── run_exchange(initiator, partner, day=day)   # exchange.py
            |   └── for turn in 1..n_turns:
            |       ├── build system prompt (persona + stance)
            |       ├── build user prompt (KG context + history)
            |       ├── llm_call()           # llm.py
            |       ├── memory.absorb(listener, round=day)   # memory.py
            |       |   └── [GhostMemory] extract_triplets_batch() -> absorb_content()
            |       └── append ExchangeTurn
            |
            ├── annotate_many([initiator, partner])    # annotator.py -> LikertStance
            |   └── clamp: max(prev-1, min(prev+1, new))
            |
            ├── current_stances[a] = stance_a          # in-memory only
            ├── current_stances[b] = stance_b
            └── tracker.log(day, ...)                  # -> results.csv + exchanges.jsonl

        write_checkpoint(day)                          # once per day, after all agents
```

**Design principle:** every module has exactly one job.
- `exchange.py` never knows which memory condition is active (Null Object Pattern).
- `annotator.py` never touches the knowledge graph.
- `simulation.py` is the only place that reads `memory_condition`.

---

## Memory conditions

| Condition | `MEMORY_CONDITION` | KG dimensions | What agents remember |
|---|---|---|---|
| Baseline | `no_kg` | none | Nothing. Pure LODAS replication. |
| General KG | `general_only` | general | Topic facts extracted from conversations. |
| ToM KG | `tom_only` | tom | Inferences about each other's views. |
| Full KG | `full_kg` | general + tom + beliefs | All three dimensions. |

---

## Data storage

**`results.csv`** — one row per exchange (n_agents x n_days rows per run)

Key columns: `iteration`, `run_id`, `memory_condition`, `topic`, `agent_a_id`, `agent_a_stance_before_label`, `agent_a_stance_before_score`, `agent_a_stance_after_label`, `agent_a_stance_after_score`, same for agent_b, `n_turns`, `sim_clock`.

**`exchanges.jsonl`** — one JSON object per exchange, full conversation transcripts

**`simulation.db`** — GhostKG SQLite database, backed up before each day (`simulation_iter_N.db.bak`)

**`checkpoint.json`** — `{"last_completed_iteration": N, "memory_condition": "...", ...}`

All output files go into `OUTPUT_DIR`. Defaults to `data/run_01`. Gitignored.

---

## Install

```bash
git clone https://github.com/pranavdeepak13/Agentic-Stance.git
cd Agentic-Stance
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## Configure

All settings live in `.env`. See `.env.example` for the full list.

```bash
LLM_PROVIDER=ollama          # ollama | anthropic | openai | groq | vllm
LLM_MODEL=llama3.2
LLM_MAX_CONCURRENCY=8
PARALLEL_EXCHANGE_JOBS=1     # >1 activates vLLM parallel scheduler

TOPIC=immigration policy
N_AGENTS=140
N_ITERATIONS=10
MEMORY_CONDITION=no_kg

OUTPUT_DIR=data/immigration/no_kg
DB_PATH=data/immigration/no_kg/simulation.db
```

| Provider | Setup |
|---|---|
| Ollama (default, local) | `ollama serve` then `ollama pull llama3.2` |
| Groq (fast API) | `LLM_PROVIDER=groq LLM_MODEL=llama3-8b-8192`, set `GROQ_API_KEY` |
| Anthropic | `LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001`, set `ANTHROPIC_API_KEY` |
| vLLM | `LLM_PROVIDER=vllm LLM_BASE_URL=http://127.0.0.1:8000/v1`, set `LLM_MODEL` |

---

## Run

**Quick test (3 days, 4 agents):**
```bash
PYTHONDONTWRITEBYTECODE=1 N_AGENTS=4 N_ITERATIONS=3 OUTPUT_DIR=data/test DB_PATH=data/test/sim.db \
  .venv/bin/python src/simulation.py
```

**Single condition:**
```bash
PYTHONDONTWRITEBYTECODE=1 TOPIC=immigration MEMORY_CONDITION=no_kg \
  OUTPUT_DIR=data/immigration/no_kg DB_PATH=data/immigration/no_kg/simulation.db \
  N_AGENTS=140 N_ITERATIONS=10 \
  .venv/bin/python src/simulation.py
```

**Full ablation (all 4 conditions + plots):**
```bash
bash run_ablation.sh immigration 10
```

**Multiple seeds:**
```bash
bash run_ablation.sh immigration 10 42,43,44
```

Resume a crashed run: re-run the same command. Checkpoint is detected automatically.

---

## Analysis

```bash
# All conditions compared (requires all 4 results.csv files)
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python analysis/plots.py \
  --data-dir data/immigration --output-dir data/immigration/plots

# Single condition
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python analysis/plots.py \
  --data-dir data/immigration --output-dir data/immigration/plots --condition no_kg
```

Metrics: entropy H(t), std deviation sigma(t), effective clusters C(t), transition matrix T_ij, acceptance matrix A_ij, P(acceptance | delta-x).

---

## Add a topic

Create `topics/{slug}.py` defining `TOPIC_LABEL: str` and `PERSONAS: list[dict]`. Set `TOPIC={slug}` in `.env`. Nothing else changes.

Distribution for 140 agents: FAR_LEFT 14, LEFT 28, CENTER 56, RIGHT 28, FAR_RIGHT 14.

Use `scripts/gen_immigration_personas.py` as the template.

---

## Add an LLM provider

Two steps in `src/llm.py`: add `async def _call_one_{name}(...)` function, add an `if provider == "{name}"` branch in `llm_call_many()`. Register the name in `SUPPORTED_PROVIDERS` in `src/config.py`.

---

## vLLM

vLLM serves models through an OpenAI-compatible endpoint. The simulation connects to it the same way as any other provider.

```bash
# Start vLLM server (separate terminal)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --port 8000

# Run simulation against it
LLM_PROVIDER=vllm LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct \
LLM_BASE_URL=http://127.0.0.1:8000/v1 \
LLM_MAX_CONCURRENCY=16 \
.venv/bin/python src/simulation.py
```

Set `PARALLEL_EXCHANGE_JOBS=4` to run disjoint agent pairs concurrently within each day.

---

## Crash recovery

Re-run the same command. The simulation:
1. Reads `checkpoint.json` to find the last completed day.
2. Restores `simulation_iter_N.db.bak` to roll GhostKG back to a consistent state.
3. Rebuilds in-memory stances from `results.csv`.
4. Resumes from day N+1. No duplicate rows are written.

---

## Reference

Cau, E., Pansanella, V., Pedreschi, D., & Rossetti, G. (2025). Selective agreement, not sycophancy: investigating opinion dynamics in LLM interactions. *EPJ Data Science*, 14, 59. https://doi.org/10.1140/epjds/s13688-025-00579-1

GhostKG: https://github.com/GiulioRossetti/GhostKG
