"""
Error merging strategy for compaction.
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from cortex.compaction.utils import content_hash, merge_error_contents

__all__ = ["execute_merge_errors"]

if TYPE_CHECKING:
    from cortex.compaction.compactor import CompactionResult
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compaction.merge_errors")
_LOG_FMT = "Compactor [%s] %s"


async def execute_merge_errors(
    engine: "CortexEngine",
    project: str,
    result: "CompactionResult",
    dry_run: bool,
) -> None:
    """Execute the MERGE_ERRORS strategy."""

    # Use public API to recall decrypted facts
    all_facts = await engine.facts.recall(project=project)

    # Filter error facts
    error_facts = [f for f in all_facts if f.fact_type == "error"]

    if len(error_facts) <= 1:
        return

    # Group by content hash
    hash_groups: dict[str, list] = defaultdict(list)
    for fact in error_facts:
        hash_groups[content_hash(fact.content)].append(fact)

    merged_count = 0
    merged_ids: set[int] = set()

    for group in hash_groups.values():
        if len(group) <= 1:
            continue
        if not dry_run:
            await _merge_error_group(engine, project, group, result, merged_ids)
        merged_count += len(group)

    if merged_count > 0:
        result.strategies_applied.append("merge_errors")
        unique_groups = sum(1 for g in hash_groups.values() if len(g) > 1)
        detail = f"merge_errors: consolidated {merged_count} → {unique_groups} error facts"
        result.details.append(detail)
        logger.info(_LOG_FMT, project, detail)


async def _merge_error_group(
    engine: "CortexEngine",
    project: str,
    group: list,
    result: "CompactionResult",
    merged_ids: set[int],
) -> None:
    """Merge a single group of identical error facts."""
    import asyncio
    # Ensure deterministic ordering by ID to keep the oldest as canonical
    group.sort(key=lambda x: x.id)
    canonical = group[0]
    contents = [f.content for f in group]
    merged_content = merge_error_contents(contents)

    new_id = await engine.store(
        project=project,
        content=merged_content,
        tenant_id=canonical.tenant_id,
        fact_type="error",
        tags=canonical.tags,
        confidence=canonical.confidence,
        source="compactor:merge_errors",
    )
    result.new_fact_ids.append(new_id)

    tasks = []
    deprecated_in_group = []
    for fact in group:
        if fact.id not in merged_ids:
            merged_ids.add(fact.id)
            deprecated_in_group.append(fact.id)
            tasks.append(
                engine.deprecate(fact.id, f"compacted:merge_errors→#{new_id}")
            )

    if tasks:
        await asyncio.gather(*tasks)
        result.deprecated_ids.extend(deprecated_in_group)
