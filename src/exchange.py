"""
exchange.py — The dialogue loop between one agent pair for one simulation iteration.

run_exchange() takes two agents, alternates speaker/listener each turn, builds
prompts, calls the LLM, and updates the listener's memory after each utterance.

This module knows nothing about:
  - memory conditions (it receives an AgentMemory instance via dependency injection)
  - GhostKG, triplets, or SQLite
  - the annotator
  - the CSV log

It only produces a list of ExchangeTurn objects — the complete transcript.
The simulation loop (simulation.py) decides what to do with it next.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import LikertStance, SimulationConfig
    from memory import AgentMemory
    from personas import AgentPersona

from llm import llm_call
from prompts import AgentSystemPrompt, AgentUserPrompt

log = logging.getLogger(__name__)

_system_prompt = AgentSystemPrompt()
_user_prompt   = AgentUserPrompt()


@dataclass
class ExchangeTurn:
    turn:         int
    speaker_id:   str
    speaker_name: str
    listener_id:  str
    utterance:    str


@dataclass(frozen=True)
class ExchangeJob:
    agent_a: "AgentPersona"
    agent_b: "AgentPersona"
    n_turns: int
    current_stances: dict[str, "LikertStance"]
    memory: "AgentMemory"
    config: "SimulationConfig"
    sim_clock: str


async def run_exchange(
    agent_a: "AgentPersona",
    agent_b: "AgentPersona",
    n_turns: int,
    current_stances: dict[str, "LikertStance"],
    memory: "AgentMemory",
    config: "SimulationConfig",
    sim_clock: str,
    day: int = 0,
) -> list[ExchangeTurn]:
    """
    Run a multi-turn dialogue between agent_a and agent_b.

    Agents alternate as speaker/listener. On each turn:
      1. The speaker's system prompt is built from their persona and current stance.
      2. The speaker's user prompt includes their KG context and the exchange history so far.
      3. The LLM generates the utterance.
      4. The listener absorbs the utterance into their memory.

    Returns the full list of ExchangeTurn objects (the transcript).
    """
    exchange_log: list[ExchangeTurn] = []

    for turn_num in range(1, n_turns + 1):
        if turn_num % 2 == 1:
            speaker, listener = agent_a, agent_b
        else:
            speaker, listener = agent_b, agent_a
        history = _format_history(exchange_log)
        kg_context = memory.get_context(speaker.agent_id, config.topic)

        # Build prompts
        system = _system_prompt.render(
            name=speaker.name,
            age=str(speaker.age),
            occupation=speaker.occupation,
            leaning=speaker.leaning.value,
            persona_description=speaker.persona_description,
            topic=config.topic,
            current_stance=current_stances[speaker.agent_id].label,
        )
        user = _user_prompt.render(
            kg_context=kg_context,
            exchange_history=history,
        )

        # LLM call
        utterance = await llm_call(system, user, config)

        turn = ExchangeTurn(
            turn=turn_num,
            speaker_id=speaker.agent_id,
            speaker_name=speaker.name,
            listener_id=listener.agent_id,
            utterance=utterance,
        )
        exchange_log.append(turn)

        await memory.absorb(listener.agent_id, utterance, author=speaker.agent_id, round=day)

        log.debug(
            "[iter] turn %d | %s → %s | %d chars",
            turn_num, speaker.name, listener.name, len(utterance),
        )

    return exchange_log


async def run_exchange_jobs(jobs: list[ExchangeJob]) -> list[list[ExchangeTurn]]:
    """
    Run multiple exchange jobs concurrently.

    Jobs must be independent: no shared mutable stance state, no overlapping
    participants that would require sequential updates between jobs.
    """
    if not jobs:
        return []
    return await asyncio.gather(
        *[
            run_exchange(
                job.agent_a,
                job.agent_b,
                job.n_turns,
                job.current_stances,
                job.memory,
                job.config,
                job.sim_clock,
            )
            for job in jobs
        ]
    )


def _format_history(exchange_log: list[ExchangeTurn]) -> str:
    """Format completed turns as a readable conversation string."""
    if not exchange_log:
        return ""
    lines = [
        f"{t.speaker_name}: {t.utterance}"
        for t in exchange_log
    ]
    return "\n".join(lines)
