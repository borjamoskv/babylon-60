"""memory_compression — Background L1 Overflow Compression Pipeline.

Extracted from CortexMemoryManager to satisfy the Landauer LOC barrier (≤500).
Handles the 'Sleep-time Compute' pattern: overflowed L1 events are compressed
(LLM or raw) and persisted to L2 in a bounded background asyncio task.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.memory.manager import CortexMemoryManager
    from cortex.memory.models import CortexFactModel, EpisodicSnapshot, MemoryEntry, MemoryEvent

__all__ = [
    "compress_and_store",
    "summarize_events",
    "raw_concat",
]

logger = logging.getLogger("cortex.memory.compression")

_EPISODIC_ARTIFACT_KIND = "episodic_snapshot"


def raw_concat(events: list[MemoryEvent]) -> str:
    """Raw concatenation fallback for compression — O(N), no LLM required."""
    return "\n".join(f"[{e.role}]: {e.content}" for e in events)


async def summarize_events(
    manager: CortexMemoryManager,
    events: list[MemoryEvent],
) -> str:
    """Summarize events using LLM Router or raw concatenation fallback."""
    raw_text = raw_concat(events)

    if not manager._router:
        return raw_text

    try:
        from cortex.extensions.llm.router import CortexPrompt
        from cortex.utils.result import Ok

        prompt = CortexPrompt(
            system_instruction=(
                "You are a memory compression engine. Summarize the following "
                "conversation into a concise paragraph preserving all key decisions, "
                "technical details, errors, and outcomes. Output ONLY the summary."
            ),
            working_memory=[{"role": "user", "content": raw_text}],
            temperature=0.0,
            max_tokens=512,
        )
        result = await manager._router.invoke(prompt)
        if isinstance(result, Ok):
            logger.debug("LLM compression succeeded (%d chars)", len(result.value))
            return result.value

        logger.warning("LLM compression failed: %s — falling back to raw", result.error)
    except (ValueError, TypeError, RuntimeError, OSError, ImportError) as e:
        logger.warning("LLM compression error: %s — falling back to raw", e)

    return raw_text


def _build_snapshot(
    *,
    summary: str,
    events: list[MemoryEvent],
    session_id: str,
    tenant_id: str,
    vector_embedding: list[float] | None,
) -> EpisodicSnapshot:
    from cortex.memory.models import EpisodicSnapshot

    return EpisodicSnapshot(
        summary=summary,
        vector_embedding=vector_embedding or [],
        linked_events=[event.event_id for event in events],
        session_id=session_id,
        tenant_id=tenant_id,
    )


def _snapshot_metadata(
    snapshot: EpisodicSnapshot,
    *,
    project_id: str,
    compression_mode: str,
) -> dict[str, Any]:
    return {
        "type": _EPISODIC_ARTIFACT_KIND,
        "memory_artifact_kind": _EPISODIC_ARTIFACT_KIND,
        "project_id": project_id,
        "session_id": snapshot.session_id,
        "tenant_id": snapshot.tenant_id,
        "event_count": len(snapshot.linked_events),
        "linked_events": list(snapshot.linked_events),
        "compression": compression_mode,
    }


def _snapshot_to_fact(
    snapshot: EpisodicSnapshot,
    *,
    project_id: str,
    compression_mode: str,
) -> CortexFactModel:
    from cortex.memory.models import CortexFactModel

    if not snapshot.vector_embedding:
        raise ValueError("EpisodicSnapshot requires vector_embedding for fact persistence")

    return CortexFactModel(
        id=snapshot.snapshot_id,
        tenant_id=snapshot.tenant_id,
        project_id=project_id,
        content=snapshot.summary,
        embedding=snapshot.vector_embedding,
        timestamp=snapshot.created_at.timestamp(),
        cognitive_layer="episodic",
        category="episodic",
        metadata=_snapshot_metadata(
            snapshot,
            project_id=project_id,
            compression_mode=compression_mode,
        ),
    )


def _snapshot_to_legacy_entry(
    snapshot: EpisodicSnapshot,
    *,
    project_id: str,
    compression_mode: str,
) -> MemoryEntry:
    from cortex.memory.models import MemoryEntry

    return MemoryEntry(
        content=snapshot.summary,
        project=project_id,
        source="episodic",
        metadata=_snapshot_metadata(
            snapshot,
            project_id=project_id,
            compression_mode=compression_mode,
        ),
    )


async def compress_and_store(
    manager: CortexMemoryManager,
    events: list[MemoryEvent],
    session_id: str,
    tenant_id: str,
    project_id: str,
) -> None:
    """Compress overflowed events and store in L2 (v6 sovereign or legacy).

    Called as a background asyncio.Task — must NEVER raise.
    """
    try:
        summary = await summarize_events(manager, events)
        is_sovereign = manager._l2.__class__.__name__ == "SovereignVectorStoreL2"
        compression_mode = "llm" if manager._router else "raw"
        vector_embedding = await manager._encoder.encode(summary) if is_sovereign else None
        if is_sovereign and not vector_embedding:
            # Retry with the raw episode payload before giving up on fact persistence.
            vector_embedding = await manager._encoder.encode(raw_concat(events))
        snapshot = _build_snapshot(
            summary=summary,
            events=events,
            session_id=session_id,
            tenant_id=tenant_id,
            vector_embedding=vector_embedding,
        )

        if is_sovereign:
            fact = _snapshot_to_fact(
                snapshot,
                project_id=project_id,
                compression_mode=compression_mode,
            )
            await manager._l2.memorize(fact)
            if manager._hdc:
                await manager._hdc.memorize(fact)
        else:
            entry = _snapshot_to_legacy_entry(
                snapshot,
                project_id=project_id,
                compression_mode=compression_mode,
            )
            await manager._l2.memorize(entry)

        logger.debug(
            "Compressed %d events into L2 episode (session=%s, mode=%s, type=%s, hdc=%s)",
            len(events),
            session_id,
            compression_mode,
            "sovereign" if is_sovereign else "legacy",
            "active" if manager._hdc else "inactive",
        )
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        logger.exception("L2 compression failed: %s", e)
