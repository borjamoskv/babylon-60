"""GitHub Sovereign Agent — Proactive GitHub Monitoring and Sync.

This agent extends the base CORTEX agent to provide:
1. Periodic synchronization of Issues/PRs (via GitHubCortexBridge).
2. Monitoring of repo metrics (Stars, Forks, Watchers) stored as metric facts.
3. Interactive manual sync via message bus.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cortex.agents.base import BaseAgent
from cortex.agents.message_schema import MessageKind
from cortex.extensions.sync.github_bridge import GitHubCortexBridge
from cortex.memory.temporal import now_iso

if TYPE_CHECKING:
    from cortex.agents.manifest import AgentManifest
    from cortex.agents.message_schema import AgentMessage
    from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.github")

_PROJECT = "github-agent"
_SOURCE = "agent:github"


class GitHubSovereignAgent(BaseAgent):
    """Sovereign agent for GitHub interaction and intelligence gathering."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        token: str,
        owner: str = "borjamoskv",
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._token = token
        self._owner = owner
        self._bridge: GitHubCortexBridge | None = None
        self._last_metrics_sync: float = 0
        self._metrics_interval: float = 3600  # 1 hour

    async def on_start(self) -> None:
        """Initialize the bridge on start."""
        from cortex.cli.common import get_engine

        engine = get_engine(
            self.manifest.tenant_id
        )  # Using tenant_id as DB path for now or similar logic
        await engine.init_db()
        self._bridge = GitHubCortexBridge(engine, self._token, self._owner)
        logger.info("[%s] GitHub bridge initialized for owner: %s", self.agent_id, self._owner)

    async def on_stop(self) -> None:
        """Close the bridge on stop."""
        if self._bridge:
            await self._bridge.close()

    async def handle_message(self, message: AgentMessage) -> None:
        """Handle incoming sync requests."""
        if message.kind == MessageKind.TASK_REQUEST:
            action = message.payload.get("action")
            repo = message.payload.get("repo")

            if action == "sync":
                result = await self._sync_repo(repo)
                await self.send_result(
                    message.sender,
                    {"status": "ok", "result": result},
                    correlation_id=message.message_id,
                )
            elif action == "metrics":
                result = await self._sync_metrics(repo)
                await self.send_result(
                    message.sender,
                    {"status": "ok", "metrics": result},
                    correlation_id=message.message_id,
                )
            else:
                await self.send_result(
                    message.sender, {"status": "error", "message": f"Unknown action: {action}"}
                )

    async def tick(self) -> None:
        """Periodic background work."""
        if not self._bridge:
            return

        # 1. Sync all repos (once per day or similar, but here we can do it more often if needed)
        # For a demo/agent mode, we'll do a light sync
        import time

        now = time.time()

        if now - self._last_metrics_sync > self._metrics_interval:
            await self._sync_all_metrics()
            self._last_metrics_sync = now

    async def _sync_repo(self, repo: str | None) -> dict[str, Any]:
        """Sync a specific repo or all."""
        if not self._bridge:
            return {}
        res = await self._bridge.sync_all(repo_filter=repo)
        return {
            "repos": res.repos_scanned,
            "issues": res.issues_synced,
            "prs": res.prs_synced,
            "crystallized": res.crystallized,
            "errors": res.errors,
        }

    async def _sync_all_metrics(self) -> None:
        """Fetch and store stats for all discovered repos."""
        if not self._bridge:
            return
        repos = await self._bridge.discover_repos()
        for repo in repos:
            await self._sync_metrics(repo)

    async def _sync_metrics(self, repo: str) -> dict[str, Any]:
        """Fetch and store stats for a single repo."""
        if not self._bridge:
            return {}
        try:
            stats = await self._bridge.get_repo_stats(repo)

            # Store as a metric fact
            content = (
                f"[GitHub Metrics] {repo}: Stars: {stats['stars']}, "
                f"Forks: {stats['forks']}, Watchers: {stats['watchers']}. "
                f"Updated: {stats['updated_at']}"
            )

            await self._bridge._engine.store(
                project=_PROJECT,
                content=content,
                fact_type="metric",
                tags=["github", "metrics", repo.split("/")[-1]],
                confidence="C5",  # Official API data
                source=_SOURCE,
                meta={"repo": repo, "metrics": stats, "synced_at": now_iso()},
            )
            logger.debug("[%s] Metrics synced for %s", self.agent_id, repo)
            return stats
        except Exception as e:
            logger.warning("[%s] Failed to sync metrics for %s: %s", self.agent_id, repo, e)
            return {"error": str(e)}
