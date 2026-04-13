"""Guard Pipeline — Composable pre-store, mutate, and post-store chain.

Replaces the hardcoded try/except ImportError blocks in store_mixin._store_impl
with a registered list of protocol-conforming guards, mutators, and hooks.

Guards that fail to import at registration time are silently skipped.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from cortex.extensions.interfaces.store_pipeline import ContentMutator, PostStoreHook, StoreGuard

__all__ = ["GuardPipeline"]

logger = logging.getLogger("cortex.engine")


class GuardPipeline:
    """Orchestrates pre-store guards, content mutators, and post-store hooks."""

    def __init__(self) -> None:
        self._guards: list[StoreGuard] = []
        self._mutators: list[ContentMutator] = []
        self._post_hooks: list[PostStoreHook] = []

    # ─── Registration ─────────────────────────────────────────────

    def add_guard(self, guard: StoreGuard) -> None:
        self._guards.append(guard)

    def add_mutator(self, mutator: ContentMutator) -> None:
        self._mutators.append(mutator)

    def add_post_hook(self, hook: PostStoreHook) -> None:
        self._post_hooks.append(hook)

    # ─── Execution ────────────────────────────────────────────────

    async def run_guards(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Run all pre-store guards. First rejection raises ValueError."""
        for guard in self._guards:
            await guard.check(content, project, fact_type, meta, conn, tenant_id=tenant_id)

    async def run_mutators(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Run all content mutators in order. Each receives the previous output."""
        for mutator in self._mutators:
            content, fact_type, meta = await mutator.transform(
                content,
                project,
                fact_type,
                meta,
                conn,
                tenant_id=tenant_id,
                source=source,
            )
        return content, fact_type, meta

    async def run_post_hooks(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
        after_commit: bool | None = None,
    ) -> None:
        """Run post-store hooks for the requested commit phase.

        Critical hooks fail closed. Non-critical hooks are surfaced via logs
        but do not break the write path.
        """
        for hook in self._post_hooks:
            requires_committed_write = getattr(hook, "requires_committed_write", False) is True
            if after_commit is not None and requires_committed_write != after_commit:
                continue

            try:
                await hook.on_stored(
                    fact_id,
                    project,
                    fact_type,
                    conn,
                    tenant_id=tenant_id,
                    source=source,
                    db_path=db_path,
                )
            except Exception as e:  # noqa: BLE001
                hook_name = type(hook).__name__
                if getattr(hook, "critical", False) is True:
                    logger.exception("[GuardPipeline] Critical post-hook %s failed", hook_name)
                    raise RuntimeError(f"Critical post-store hook failed: {hook_name}") from e
                logger.warning("[GuardPipeline] Post-hook %s failed", hook_name, exc_info=True)

    @property
    def guard_count(self) -> int:
        return len(self._guards)

    @property
    def mutator_count(self) -> int:
        return len(self._mutators)

    @property
    def hook_count(self) -> int:
        return len(self._post_hooks)
