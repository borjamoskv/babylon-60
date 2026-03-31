import logging
from typing import Any

logger = logging.getLogger("cortex.guards.settlement")


class SettlementVerifierGuard:
    """
    Ω₁ / Ω₂: The Settlement Verifier Guard.
    Ensures that any stochastic claim about financial yield (EVM/Stripe)
    is backed by cryptographic or API verification before
    allowing it to be persisted as a C5 Fact.
    """

    def check_settlement_authenticity(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        Validates if a claim about yield contains verified settlement data.
        """
        content_lower = content.lower()

        # Fast path: if it doesn't mention financial keywords, bypass check
        financial_keywords = (
            "wallet",
            "eth",
            "stripe",
            "bounty",
            "yield",
            "recompensa",
            "usd",
            "eur",
        )
        if not any(k in content_lower for k in financial_keywords):
            return True

        meta = metadata or {}

        # Check for EVM or Stripe verification artifacts
        has_tx = "tx_hash" in meta or "transaction_hash" in meta
        has_stripe = "stripe_charge_id" in meta or "stripe_session_id" in meta
        has_verification = meta.get("verified", False) is True

        if not (has_tx or has_stripe or has_verification):
            logger.error("Ω₁ Violation: Unverified financial claim detected.")
            raise ValueError(
                "Epistemic Violation: A stochastic claim about financial yield "
                "was intercepted without cryptographic (EVM) or API (Stripe) verification. "
                "Claims must include 'tx_hash' or 'stripe_charge_id' in metadata "
                "to be classified as C5-Dynamic Exergy."
            )

        logger.info("SettlementVerifierGuard: Financial claim verified.")
        return True
