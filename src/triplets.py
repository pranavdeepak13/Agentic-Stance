"""
triplets.py — Extract knowledge graph triplets from text using an LLM.

Each triplet is (subject, predicate, object, dimension) where dimension is
one of: "general" | "tom" | "beliefs".

  general  — facts about the topic, events, or policies
  tom      — what the speaker believes about the other person's views (Theory of Mind)
  beliefs  — the speaker's own stated positions, values, or opinions

The extraction LLM is called once per utterance per absorb() call.
If parsing fails (model produces non-standard output), returns an empty list —
the simulation never crashes because triplet extraction failed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from llm import LLMRequest, llm_call_many
from prompts import TripletSystemPrompt, TripletUserPrompt

log = logging.getLogger(__name__)

_system_prompt = TripletSystemPrompt()
_user_prompt   = TripletUserPrompt()


@dataclass(frozen=True)
class Triplet:
    subject:   str
    predicate: str
    object:    str
    dimension: str  


async def extract_triplets(
    text: str,
    dimension: str,
    config: "SimulationConfig",
) -> list[Triplet]:
    """
    Extract KG triplets from `text` for the given KG `dimension`.

    Returns an empty list on any parsing failure (never raises).
    """
    results = await extract_triplets_batch([(text, dimension)], config)
    return results[0]


async def extract_triplets_batch(
    requests: list[tuple[str, str]],
    config: "SimulationConfig",
) -> list[list[Triplet]]:
    """
    Extract KG triplets for many (text, dimension) pairs in one batch.

    Returns a list aligned with the input request order. Failures degrade to
    empty lists per request.
    """
    if not requests:
        return []

    llm_requests: list[LLMRequest] = []
    for text, dimension in requests:
        system = _system_prompt.render(dimension=dimension)
        user = _user_prompt.render(text=text)
        llm_requests.append(LLMRequest(system=system, user=user))

    try:
        raw_outputs = await llm_call_many(llm_requests, config)
    except Exception as exc:
        log.warning("Triplet extraction batch failed: %s. Skipping batch.", exc)
        return [[] for _ in requests]

    parsed: list[list[Triplet]] = []
    for raw, (_, dimension) in zip(raw_outputs, requests):
        parsed.append(_parse_triplets(raw, dimension))
    return parsed


def _parse_triplets(raw: str, dimension: str) -> list[Triplet]:
    """
    Parse pipe-separated triplet lines from LLM output.

    Expected format (one per line):
        subject | predicate | object

    Lines that don't match are silently skipped.
    "NONE" response → empty list.
    """
    if raw.strip().upper() == "NONE":
        return []

    triplets: list[Triplet] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.upper() == "NONE":
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            log.debug("Skipping malformed triplet line: %r", line)
            continue
        subject, predicate, obj = parts
        if subject and predicate and obj:
            triplets.append(Triplet(subject, predicate, obj, dimension))

    return triplets
