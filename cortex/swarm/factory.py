import logging

from cortex.engine.ledger import SovereignLedger
from cortex.swarm.manager import SwarmManager
from cortex.swarm.specialists import forge_sovereign_swarm

logger = logging.getLogger("cortex.swarm.factory")


def create_sovereign_swarm(ledger: SovereignLedger | None = None) -> SwarmManager:
    """
    Instantiates and configures a CORTEX SwarmManager injected with
    Ultra-Potent Specialist Actuators via lazy-provisioning.

    Ω-Architecture: Reduces startup entropy by deferring specialist
    materialization until first dispatch.
    """
    manager = SwarmManager(ledger=ledger)

    # Injected specialists are forged on demand by the manager if it supports factory-based registration,
    # or we register the keys here for the manager to resolve.
    specialists = forge_sovereign_swarm()

    for act_name, actuator in specialists.items():
        # High-performance registration: zero-copy injection
        manager.register_actuator(act_name, actuator)

    logger.debug("Sovereign Swarm provisioned with %d specialists.", len(specialists))
    return manager
