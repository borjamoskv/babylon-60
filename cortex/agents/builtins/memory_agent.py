"""MemoryAgent with explicit ops and stable response envelopes."""

from __future__ import annotations

import logging

from cortex.agents.builtins._explicit_ops import (
    ExplicitOpsAgent,
    MemoryManagerLike,
    MemoryManagerOps,
    coerce_memory_manager_ops,
)
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.tools import ToolRegistry
from cortex.memory.manager import CortexMemoryManager

logger = logging.getLogger(__name__)


class MemoryAgent(ExplicitOpsAgent):
    """Reactive agent — governs read/write access to CortexMemoryManager.

    Callers must inject a fully initialised CortexMemoryManager (it requires
    l1/l2/l3/encoder components that are environment-specific).
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        manager: CortexMemoryManager | MemoryManagerLike | MemoryManagerOps,
    ) -> None:
        super().__init__(
            manifest,
            bus,
            tool_registry,
            ops_handler=coerce_memory_manager_ops(manager),
        )

    async def tick(self) -> None:
        logger.debug("MemoryAgent tick — idle")
