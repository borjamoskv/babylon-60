"""SupervisorAgent with explicit ops and stable response envelopes."""

from __future__ import annotations

import logging

from cortex.agents.builtins._explicit_ops import (
    ExplicitOpsAgent,
    SupervisorLike,
    SupervisorManagerOps,
    coerce_supervisor_ops,
)
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


class SupervisorAgent(ExplicitOpsAgent):
    """Reactive agent — exposes Supervisor lifecycle ops over the message bus."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        supervisor: Supervisor | SupervisorLike | SupervisorManagerOps,
    ) -> None:
        self._supervisor_ops = coerce_supervisor_ops(supervisor)
        super().__init__(
            manifest,
            bus,
            tool_registry,
            ops_handler=self._supervisor_ops,
        )

    async def tick(self) -> None:
        """Periodic health-check tick — detects stale agents."""
        await self._supervisor_ops.health_check()
