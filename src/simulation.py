"""
simulation.py — Top-level orchestrator and entry point.

This is the only module that:
  - knows which memory condition is active
  - owns the current_stances dict
  - owns the main simulation loop
  - calls backup_db, run_exchange, annotate, tracker.log, write_checkpoint in order

Everything else is wired together here via dependency injection.

Run:
    python src/simulation.py

Or set env vars inline:
    MEMORY_CONDITION=full_kg OUTPUT_DIR=data/full_kg python src/simulation.py
"""

from __future__ import annotations

# Prevent Python from writing .pyc / __pycache__ files.
# Placed right after __future__ (which must be first) and before all other imports.
import sys
sys.dont_write_bytecode = True

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src/ to path so relative imports work when run directly
sys.path.insert(0, str(Path(__file__).parent))

from annotator import annotate_many
from checkpoint import (
    backup_db,
    load_checkpoint,
    rebuild_stances,
    restore_db_backup,
    write_checkpoint,
)
from config import MemoryCondition, SimulationConfig, load_config
from exchange import ExchangeJob, ExchangeTurn, run_exchange, run_exchange_jobs
from memory import AgentMemory, GhostMemory, NullMemory
from personas import create_personas
from tracker import SimulationTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("simulation")


def _build_memory(config: SimulationConfig, manager: object) -> AgentMemory:
    """
    Construct the correct memory implementation for this run.
    This is the only place in the codebase that reads config.memory_condition.
    """
    condition = config.memory_condition

    if condition == MemoryCondition.NO_KG:
        return NullMemory()
    elif condition == MemoryCondition.GENERAL_ONLY:
        return GhostMemory(manager, config, dimensions=["general"])
    elif condition == MemoryCondition.TOM_ONLY:
        return GhostMemory(manager, config, dimensions=["tom"])
    elif condition == MemoryCondition.FULL_KG:
        return GhostMemory(manager, config, dimensions=["general", "tom", "beliefs"])
    else:
        raise ValueError(f"Unknown memory condition: {condition}")


def _init_ghostkg(config: SimulationConfig, agent_ids: list[str]) -> object:
    """
    Initialise a GhostKG AgentManager and register all agents.
    Returns None for no_kg condition (no GhostKG needed).
    """
    if config.memory_condition == MemoryCondition.NO_KG:
        return None

    try:
        from ghost_kg import AgentManager
    except ImportError:
        raise ImportError(
            "ghost_kg package not installed.\n"
            "Run: pip install git+https://github.com/GiulioRossetti/GhostKG"
        )

    manager = AgentManager(db_path=config.db_path)
    for agent_id in agent_ids:
        manager.create_agent(agent_id)
    return manager


async def run_simulation(config: SimulationConfig) -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    log.info("=" * 60)
    log.info("Run ID       : %s", run_id)
    log.info("Topic        : %s", config.topic)
    log.info("Agents       : %d", config.n_agents)
    log.info("Iterations   : %d", config.n_iterations)
    log.info("Memory       : %s", config.memory_condition.value)
    log.info("Provider     : %s / %s", config.llm_provider, config.llm_model)
    log.info("Output dir   : %s", config.output_dir)
    log.info("=" * 60)

    # ── Load personas ──────────────────────────────────────────────────────────
    personas = create_personas(config)
    agent_ids = [p.agent_id for p in personas]

    # ── Resume or fresh start ──────────────────────────────────────────────────
    start_iteration = 1
    last_completed = load_checkpoint(config)

    if last_completed is not None:
        log.info("Resuming from iteration %d (last completed: %d)", last_completed + 1, last_completed)
        restore_db_backup(last_completed, config)
        start_iteration = last_completed + 1

    # ── Initialise current stances ─────────────────────────────────────────────
    csv_path = Path(config.output_dir) / "results.csv"
    if start_iteration > 1:
        current_stances = rebuild_stances(personas, csv_path)
        log.info("Rebuilt stances from CSV for %d agents.", len(current_stances))
    else:
        current_stances = {p.agent_id: p.initial_stance for p in personas}

    # ── Initialise GhostKG (None for no_kg condition) ─────────────────────────
    manager = _init_ghostkg(config, agent_ids)

    # ── Build memory implementation ────────────────────────────────────────────
    memory = _build_memory(config, manager)
    log.info("Memory implementation: %s", type(memory).__name__)

    # ── Tracker ────────────────────────────────────────────────────────────────
    tracker = SimulationTracker(config, run_id)

    # ── RNG (seeded for reproducibility) ──────────────────────────────────────
    rng = random.Random(config.random_seed)

    # ── Simulated clock ────────────────────────────────────────────────────────
    # Each iteration advances by clock_advance_hours so FSRS decay fires.
    # We track from a fixed epoch so results are reproducible.
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = epoch + timedelta(hours=config.clock_advance_hours * (start_iteration - 1))

    if config.parallel_exchange_jobs > 1:
        await _run_parallel_scheduler(
            config=config,
            personas=personas,
            agent_ids=agent_ids,
            current_stances=current_stances,
            memory=memory,
            tracker=tracker,
            manager=manager,
            rng=rng,
            start_iteration=start_iteration,
            clock=clock,
        )
        log.info("Simulation complete. Results in: %s", config.output_dir)
        return

    # ── Main loop ──────────────────────────────────────────────────────────────
    for iteration in range(start_iteration, config.n_iterations + 1):

        # Snapshot the DB before touching anything this iteration (crash safety)
        backup_db(iteration - 1, config)

        # Advance FSRS clock
        clock += timedelta(hours=config.clock_advance_hours)
        sim_clock = clock.isoformat()

        # Advance GhostKG agent times so FSRS decay operates on the simulated timeline
        if manager is not None:
            for agent_id in agent_ids:
                try:
                    manager.set_agent_time(agent_id, clock)
                except Exception:
                    pass  # GhostKG API may differ by version; log and continue

        # Select a random pair (without replacement within each pair)
        pair = rng.sample(personas, 2)
        agent_a, agent_b = pair[0], pair[1]

        # Random number of turns for this exchange
        n_turns = rng.randint(config.min_turns, config.max_turns)

        log.info(
            "Iter %3d/%d | %s (%s) ↔ %s (%s) | %d turns | clock %s",
            iteration, config.n_iterations,
            agent_a.name, current_stances[agent_a.agent_id].label,
            agent_b.name, current_stances[agent_b.agent_id].label,
            n_turns,
            clock.strftime("%Y-%m-%d"),
        )

        # Capture stances before the exchange (needed for tracker._before fields)
        stance_a_before = current_stances[agent_a.agent_id]
        stance_b_before = current_stances[agent_b.agent_id]

        exchange_log = await run_exchange(
            agent_a, agent_b, n_turns, current_stances, memory, config, sim_clock
        )

        stance_a_after, stance_b_after = await annotate_many(
            [
                (agent_a, _format_agent_utterances(agent_a.agent_id, exchange_log), stance_a_before),
                (agent_b, _format_agent_utterances(agent_b.agent_id, exchange_log), stance_b_before),
            ],
            config=config,
        )

        # Update in-memory stances (no disk read — stances live in this dict)
        current_stances[agent_a.agent_id] = stance_a_after
        current_stances[agent_b.agent_id] = stance_b_after

        log.info(
            "         → %s: %s→%s | %s: %s→%s",
            agent_a.name, stance_a_before.label, stance_a_after.label,
            agent_b.name, stance_b_before.label, stance_b_after.label,
        )

        # Log to CSV and JSONL — checkpoint is written AFTER this succeeds
        tracker.log(
            iteration=iteration,
            agent_a=agent_a,
            agent_b=agent_b,
            stance_a_before=stance_a_before,
            stance_a_after=stance_a_after,
            stance_b_before=stance_b_before,
            stance_b_after=stance_b_after,
            exchange_log=exchange_log,
            sim_clock=sim_clock,
        )

        write_checkpoint(iteration, config)

    log.info("Simulation complete. Results in: %s", config.output_dir)


async def _run_parallel_scheduler(
    config: SimulationConfig,
    personas: list[object],
    agent_ids: list[str],
    current_stances: dict[str, object],
    memory: AgentMemory,
    tracker: SimulationTracker,
    manager: object,
    rng: random.Random,
    start_iteration: int,
    clock: datetime,
) -> None:
    """
    Execute exchanges in parallel batches of disjoint pairs.

    The scheduler keeps the same checkpointing contract as the sequential loop
    by checkpointing after each completed exchange, even though LLM generation
    happens concurrently at batch scope.
    """
    exchange_index = start_iteration
    while exchange_index <= config.n_iterations:
        backup_db(exchange_index - 1, config)
        clock += timedelta(hours=config.clock_advance_hours)
        sim_clock = clock.isoformat()

        if manager is not None:
            for agent_id in agent_ids:
                try:
                    manager.set_agent_time(agent_id, clock)
                except Exception:
                    pass

        jobs = _build_exchange_batch(
            personas=personas,
            current_stances=current_stances,
            memory=memory,
            config=config,
            sim_clock=sim_clock,
            rng=rng,
            max_jobs=config.parallel_exchange_jobs,
            remaining=config.n_iterations - exchange_index + 1,
        )

        if not jobs:
            break

        batch_logs = await run_exchange_jobs(jobs)

        annotation_requests: list[tuple[object, str, object]] = []
        before_pairs: list[tuple[object, object]] = []
        for job, exchange_log in zip(jobs, batch_logs):
            agent_a_before = current_stances[job.agent_a.agent_id]
            agent_b_before = current_stances[job.agent_b.agent_id]
            before_pairs.append((agent_a_before, agent_b_before))
            annotation_requests.append(
                (job.agent_a, _format_agent_utterances(job.agent_a.agent_id, exchange_log), agent_a_before)
            )
            annotation_requests.append(
                (job.agent_b, _format_agent_utterances(job.agent_b.agent_id, exchange_log), agent_b_before)
            )

        annotated = await annotate_many(annotation_requests, config=config)

        for index, (job, exchange_log) in enumerate(zip(jobs, batch_logs)):
            stance_a_before, stance_b_before = before_pairs[index]
            stance_a_after = annotated[index * 2]
            stance_b_after = annotated[index * 2 + 1]

            current_stances[job.agent_a.agent_id] = stance_a_after
            current_stances[job.agent_b.agent_id] = stance_b_after

            log.info(
                "Iter %3d/%d | %s (%s) ↔ %s (%s) | %d turns | clock %s",
                exchange_index, config.n_iterations,
                job.agent_a.name, stance_a_before.label,
                job.agent_b.name, stance_b_before.label,
                job.n_turns,
                clock.strftime("%Y-%m-%d"),
            )
            log.info(
                "         → %s: %s→%s | %s: %s→%s",
                job.agent_a.name, stance_a_before.label, stance_a_after.label,
                job.agent_b.name, stance_b_before.label, stance_b_after.label,
            )

            tracker.log(
                iteration=exchange_index,
                agent_a=job.agent_a,
                agent_b=job.agent_b,
                stance_a_before=stance_a_before,
                stance_a_after=stance_a_after,
                stance_b_before=stance_b_before,
                stance_b_after=stance_b_after,
                exchange_log=exchange_log,
                sim_clock=sim_clock,
            )
            write_checkpoint(exchange_index, config)
            exchange_index += 1


def _build_exchange_batch(
    personas: list[object],
    current_stances: dict[str, object],
    memory: AgentMemory,
    config: SimulationConfig,
    sim_clock: str,
    rng: random.Random,
    max_jobs: int,
    remaining: int,
) -> list[ExchangeJob]:
    shuffled = personas[:]
    rng.shuffle(shuffled)
    batch_size = min(max_jobs, remaining, len(shuffled) // 2)
    jobs: list[ExchangeJob] = []
    for index in range(batch_size):
        agent_a = shuffled[index * 2]
        agent_b = shuffled[index * 2 + 1]
        n_turns = rng.randint(config.min_turns, config.max_turns)
        jobs.append(
            ExchangeJob(
                agent_a=agent_a,
                agent_b=agent_b,
                n_turns=n_turns,
                current_stances=current_stances,
                memory=memory,
                config=config,
                sim_clock=sim_clock,
            )
        )
    return jobs


def _format_agent_utterances(agent_id: str, exchange_log: list[ExchangeTurn]) -> str:
    utterances: list[str] = []
    for turn_index, turn in enumerate(exchange_log, start=1):
        if getattr(turn, "speaker_id", None) == agent_id:
            utterances.append(f"[Turn {turn_index}] {turn.utterance}")
    return "\n".join(utterances)


if __name__ == "__main__":
    config = load_config()
    asyncio.run(run_simulation(config))
