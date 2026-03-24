import logging

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier

logger = logging.getLogger("cortex.guards.capability_guard")


class CapabilityGuard:
    """
    Enforces capability and risk tier constraints on execution.
    Acts as the deterministic membrane preventing generative outputs
    from executing un-granted operations.
    """

    def __init__(
        self,
        credentials: AgentCredentials | None = None,
        allowed_capabilities: set[Capability] | None = None,
        max_allowed_tier: RiskTier | None = None,
    ):
        """Builds a deterministic guard bound to an agent's operational profile."""
        if credentials:
            self.credentials = credentials
            self.capabilities = list(credentials.capabilities)
            self.max_allowed_tier = max_allowed_tier or credentials.max_tier
        elif allowed_capabilities is not None:
            # Create dummy credentials for backward compatibility
            self.capabilities = list(allowed_capabilities)
            self.max_allowed_tier = max_allowed_tier or max(
                (cap.tier for cap in allowed_capabilities),
                default=RiskTier.TIER_0_ANALYTICAL
            )
            self.credentials = AgentCredentials(
                agent_id="legacy_agent",
                capabilities=set(self.capabilities),
                max_tier=self.max_allowed_tier
            )
        else:
            self.capabilities = []
            self.max_allowed_tier = max_allowed_tier or RiskTier.TIER_0_ANALYTICAL
            self.credentials = None

    def add_capability(self, capability: Capability) -> None:
        """Add a capability dynamically, elevating execution rights."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            # Elevate max_allowed_tier if the new capability has a higher tier
            if capability.tier.value > self.max_allowed_tier.value:
                self.max_allowed_tier = capability.tier
            logger.info("CapabilityGuard — added capability %s", capability.name)

    def can_execute(self, capability_name: str) -> bool:
        """Checks if a capability is present and not exceeding the risk tier."""
        for cap in self.capabilities:
            if cap.name == capability_name:
                if cap.tier.value <= self.max_allowed_tier.value:
                    return True
                else:
                    logger.warning(
                        "CapabilityGuard — %s blocked (Tier %s > Max %s)",
                        capability_name, cap.tier.name, self.max_allowed_tier.name
                    )
                    return False
        return False

    def validate_operation(self, operation: str, tier: RiskTier) -> bool:
        """Validates if an operation of a certain tier is allowed."""
        if tier.value <= self.max_allowed_tier.value:
            return True
        logger.warning(
            "CapabilityGuard — Operation %s blocked (Tier %s > Max %s)",
            operation, tier.name, self.max_allowed_tier.name
        )
        return False

    def validate_action(self, capability_name: str, requested_tier: RiskTier) -> None:
        """
        Validates an action against specific capability and tier constraints.
        Raises ValueError if unauthorized.
        """
        # 1. Tier Check
        if requested_tier.value > self.max_allowed_tier.value:
            raise ValueError(
                f"Execution rejected: Requested Tier {requested_tier.name} "
                f"exceeds max allowed Tier {self.max_allowed_tier.name}"
            )

        # 2. Capability Check
        # If capability_name is provided, it must exist in granted capabilities
        if capability_name:
            found = False
            for cap in self.capabilities:
                if cap.name == capability_name:
                    found = True
                    # The specific capability must also support the tier
                    if requested_tier.value > cap.tier.value:
                        raise ValueError(
                            f"Capability '{capability_name}' tier {cap.tier.name} "
                            f"insufficient for requested tier {requested_tier.name}"
                        )
                    break
            if not found:
                raise ValueError(f"Missing required capability '{capability_name}'")

    def revoke_capability(self, capability_name: str) -> None:
        """Remove a capability and dynamically recalculate max tier."""
        self.capabilities = [c for c in self.capabilities if c.name != capability_name]
        # Refresh max_allowed_tier based on remaining caps
        if self.capabilities:
            self.max_allowed_tier = max(c.tier for c in self.capabilities)
        else:
            self.max_allowed_tier = RiskTier.TIER_0_ANALYTICAL
        logger.info("CapabilityGuard — revoked capability %s", capability_name)
