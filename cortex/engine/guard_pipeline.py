"""Guard Pipeline — Composable pre-store, mutate, and post-store chain.

Replaces the hardcoded try/except ImportError blocks in store_mixin._store_impl
with a registered list of protocol-conforming guards, mutators, and hooks.

Guards that fail to import at registration time are silently skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import aiosqlite

from cortex.extensions.interfaces.store_pipeline import ContentMutator, PostStoreHook, StoreGuard

__all__ = ["GuardPipeline"]

logger = logging.getLogger("cortex.engine")


@dataclass(frozen=True)
class _PostHookRegistration:
    hook: PostStoreHook
    required: bool = False


class GuardPipeline:
    """Orchestrates pre-store guards, content mutators, and post-store hooks."""

    def __init__(self) -> None:
        self._guards: list[StoreGuard] = []
        self._mutators: list[ContentMutator] = []
        self._post_hooks: list[_PostHookRegistration] = []

    # ─── Registration ─────────────────────────────────────────────

    def add_guard(self, guard: StoreGuard) -> None:
        self._guards.append(guard)

    def add_mutator(self, mutator: ContentMutator) -> None:
        self._mutators.append(mutator)

    def add_post_hook(self, hook: PostStoreHook, *, required: bool = False) -> None:
        self._post_hooks.append(_PostHookRegistration(hook=hook, required=required))

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
        source: str | None = None,
    ) -> None:
        """Run all pre-store guards. First rejection raises ValueError."""
        for guard in self._guards:
            await guard.check(
                content, project, fact_type, meta, conn, tenant_id=tenant_id, source=source
            )

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
        required: bool | None = None,
    ) -> None:
        """Run post-store hooks.

        Optional hooks are best-effort. Required hooks run to completion as a
        group and then fail closed if any required hook failed.
        """
        failed_required: list[str] = []
        for registration in self._post_hooks:
            if required is not None and registration.required != required:
                continue
            hook = registration.hook
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
                if registration.required:
                    failed_required.append(hook_name)
                    logger.error(
                        "[GuardPipeline] Required post-hook %s failed closed (%s)",
                        hook_name,
                        type(e).__name__,
                    )
                    continue
                logger.debug(
                    "[GuardPipeline] Optional post-hook %s skipped after %s",
                    hook_name,
                    type(e).__name__,
                )

        if failed_required:
            failed = ", ".join(failed_required)
            raise RuntimeError(f"FAIL-CLOSED: required post-store hook(s) failed: {failed}")

    @property
    def guard_count(self) -> int:
        return len(self._guards)

    @property
    def mutator_count(self) -> int:
        return len(self._mutators)

    @property
    def hook_count(self) -> int:
        return len(self._post_hooks)
