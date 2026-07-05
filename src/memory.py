"""
memory.py — AgentMemory interface + two concrete implementations.

exchange.py receives an AgentMemory instance and calls absorb() and get_context()
without knowing which implementation is in use. The memory condition lives only
in simulation.py, which constructs the correct implementation at startup.

Null Object Pattern (Arch Issue 2 from DESIGN_DECISIONS.md):
NullMemory   — both methods are no-ops; used for no_kg condition
GhostMemory  — absorb() extracts triplets then writes to GhostKG;
get_context() retrieves relevant triplets as a formatted string

GhostMemory takes a `dimensions` list, so one class serves all three KG conditions:
    general_only  → dimensions=["general"]
    tom_only      → dimensions=["tom"]
    full_kg       → dimensions=["general", "tom", "beliefs"]
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from triplets import extract_triplets_batch

log = logging.getLogger(__name__)



class AgentMemory(ABC):
    @abstractmethod
    async def absorb(self, agent_id: str, text: str, author: str, round: int = 0) -> None:
        """Store `text` (spoken by `author`) in `agent_id`'s memory."""

    @abstractmethod
    def get_context(self, agent_id: str, topic: str) -> str:
        """Return relevant memory context for `agent_id` as a plain string."""


class NullMemory(AgentMemory):
    """No-op memory for the no_kg baseline condition."""

    async def absorb(self, agent_id: str, text: str, author: str, round: int = 0) -> None:
        pass

    def get_context(self, agent_id: str, topic: str) -> str:
        return ""
    

class GhostMemory(AgentMemory):
    """
    Memory backed by a GhostKG AgentManager.

    On absorb(): extracts KG triplets from the text using an LLM, then writes
    them to the agent's knowledge graph via GhostKG's absorb_content().

    On get_context(): calls GhostKG's get_context() which retrieves the most
    relevant triplets (weighted by FSRS retrievability) and returns them as a
    formatted string ready to inject into a prompt.

    The `dimensions` list controls which KG dimensions are active for this run.
    """

    def __init__(self,manager: object,config: "SimulationConfig",dimensions: list[str],  ) -> None:
        self._manager = manager
        self._config  = config
        self._dimensions = dimensions

    async def absorb(self, agent_id: str, text: str, author: str, round: int = 0) -> None:
        """
        Extract triplets from `text` for each active dimension, then write
        them to the agent's KG via GhostKG.
        """
        triplet_batches = await extract_triplets_batch(
            [(text, dim) for dim in self._dimensions],
            self._config,
            round=round,
        )

        for dim, triplets in zip(self._dimensions, triplet_batches):
            if not triplets:
                continue

            # Convert to the format GhostKG's absorb_content() expects:
            # list of (subject, predicate, object) tuples
            kg_triplets = [(t.subject, t.predicate, t.object) for t in triplets]

            try:
                self._manager.absorb_content(
                    agent_id,
                    text,
                    author=author,
                    triplets=kg_triplets,
                )
            except Exception as exc:
                log.warning(
                    "GhostKG absorb_content failed for agent %s (dim=%s): %s. Skipping.",
                    agent_id, dim, exc,
                )

    def get_context(self, agent_id: str, topic: str) -> str:
        """
        Retrieve relevant memory context for `agent_id` from GhostKG.
        Returns a formatted string, or empty string if nothing is retrieved.
        """
        try:
            context = self._manager.get_context(agent_id, topic)
            if not context:
                return ""
            if isinstance(context, list):
                return "\n".join(str(item) for item in context)
            return str(context)
        except Exception as exc:
            log.warning(
                "GhostKG get_context failed for agent %s: %s. Returning empty context.",
                agent_id, exc,
            )
            return ""
