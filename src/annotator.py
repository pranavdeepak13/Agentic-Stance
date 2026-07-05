"""
annotator.py — Stance annotation by a third LLM judge.

The annotator reads an agent's utterances from a completed exchange and returns
a LikertStance. It is entirely separate from the agent LLMs — it sees the
exchange as a reader, not a participant.

Bias prevention: The annotator prompt instructs the LLM to report the stance
the agent expressed, not the annotator's own view. The full Likert scale
definition is included so the model uses a consistent frame every time.

Retry logic: up to MAX_RETRIES attempts on AnnotationError (unparseable output).
After all retries fail, returns the agent's previous stance as a safe fallback
(logged as a warning — not a crash).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import LikertStance, SimulationConfig
    from exchange import ExchangeTurn
    from personas import AgentPersona

from config import AnnotationError, LikertStance, parse_likert
from llm import LLMRequest, llm_call, llm_call_many
from prompts import (
    LIKERT_SCALE_DEFINITION,
    AnnotatorSystemPrompt,
    AnnotatorUserPrompt,
)

log = logging.getLogger(__name__)

MAX_RETRIES = 3
_system_prompt = AnnotatorSystemPrompt()
_user_prompt   = AnnotatorUserPrompt()


async def annotate(
    agent: "AgentPersona",
    exchange_log: list["ExchangeTurn"],
    previous_stance: "LikertStance",
    config: "SimulationConfig",
) -> "LikertStance":
    """
    Annotate the stance of `agent` based on their utterances in `exchange_log`.

    Parameters
    ----------
    agent           : the agent being annotated
    exchange_log    : full list of turns from the exchange
    previous_stance : the agent's stance before this exchange (used as fallback)
    config          : simulation config

    Returns
    -------
    LikertStance — the annotated stance after this exchange.
    """
    # Collect only this agent's utterances
    agent_utterances = [
        t.utterance
        for t in exchange_log
        if t.speaker_id == agent.agent_id
    ]

    if not agent_utterances:
        # Agent didn't speak (shouldn't happen, but handle gracefully)
        return previous_stance

    utterances_text = "\n".join(
        f"[Turn {i + 1}] {utt}" for i, utt in enumerate(agent_utterances)
    )

    result = await annotate_many([(agent, utterances_text, previous_stance)], config)
    return result[0]


async def annotate_many(
    items: list[tuple["AgentPersona", str, "LikertStance"]],
    config: "SimulationConfig",
) -> list["LikertStance"]:
    """
    Batch annotation for many agents.

    The caller passes the already-filtered utterances text for each agent.
    """
    if not items:
        return []

    llm_requests: list[LLMRequest] = []
    for agent, utterances_text, _previous_stance in items:
        system = _system_prompt.render(
            topic=config.topic,
            scale_definition=LIKERT_SCALE_DEFINITION,
        )
        user = _user_prompt.render(
            name=agent.name,
            topic=config.topic,
            utterances=utterances_text,
        )
        llm_requests.append(LLMRequest(system=system, user=user))

    outputs = await llm_call_many(llm_requests, config)
    annotated: list["LikertStance"] = []
    for (agent, _utterances_text, previous_stance), raw in zip(items, outputs):
        try:
            new_stance = parse_likert(raw)
            clamped_score = max(previous_stance.score - 1, min(previous_stance.score + 1, new_stance.score))
            annotated.append(LikertStance.from_score(clamped_score))
        except AnnotationError as exc:
            annotated.append(
                await _retry_annotation(agent, _utterances_text, previous_stance, config, exc)
            )
    return annotated


async def _retry_annotation(
    agent: "AgentPersona",
    utterances_text: str,
    previous_stance: "LikertStance",
    config: "SimulationConfig",
    initial_error: Exception,
) -> "LikertStance":
    system = _system_prompt.render(
        topic=config.topic,
        scale_definition=LIKERT_SCALE_DEFINITION,
    )
    user = _user_prompt.render(
        name=agent.name,
        topic=config.topic,
        utterances=utterances_text,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = await llm_call(system, user, config)
            new_stance = parse_likert(raw)
            clamped_score = max(previous_stance.score - 1, min(previous_stance.score + 1, new_stance.score))
            return LikertStance.from_score(clamped_score)
        except AnnotationError as exc:
            if attempt < MAX_RETRIES:
                log.warning(
                    "Annotation retry %d/%d failed for %s: %s. Retrying.",
                    attempt, MAX_RETRIES, agent.name, exc,
                )
            else:
                log.warning(
                    "Batch annotation failed for %s (%s). Keeping previous stance: %s.",
                    agent.name, initial_error, previous_stance.label,
                )
                return previous_stance
