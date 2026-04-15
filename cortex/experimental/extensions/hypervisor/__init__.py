"""CORTEX Hypervisor — Public API.

The Telescope Inversion: maximum simplicity on the outside.

Usage::

    from cortex.experimental.extensions.hypervisor import AgencyHypervisor, Memory, HealthReport

    hypervisor = AgencyHypervisor(engine)
    handle = hypervisor.create_handle("tenant-abc", "my-project")

    receipt = await handle.remember("The launch date is Q2 2026")
    memories = await handle.recall("when is the launch?")
    health = await handle.reflect()
"""

from cortex.experimental.extensions.hypervisor.belief_engine import BeliefEngine
from cortex.experimental.extensions.hypervisor.belief_object import BeliefObject, BeliefVerdict
from cortex.experimental.extensions.hypervisor.core import AgencyHypervisor
from cortex.experimental.extensions.hypervisor.handle import AgentHandle
from cortex.experimental.extensions.hypervisor.models import HealthReport, Memory, Receipt

__all__ = [
    "AgencyHypervisor",
    "AgentHandle",
    "BeliefEngine",
    "BeliefObject",
    "BeliefVerdict",
    "HealthReport",
    "Memory",
    "Receipt",
]
