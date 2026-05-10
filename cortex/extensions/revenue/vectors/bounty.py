"""CORTEX Revenue Vector — Bounty Strike Pipeline.

Wires the Ouroboros strike pipeline into the RevenueEngine as a
first-class revenue vector. Scans for active bounty programs,
estimates ROI, and tracks payout status.

This is the INPUT side of the circular economy loop.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from cortex.extensions.revenue.models import (
    ExecutionResult,
    Opportunity,
    OpportunityStatus,
    VectorType,
)
from cortex.guards.autodidact import AutodidactGuard
from cortex.crypto.keys import ZKSwarmIdentity

logger = logging.getLogger("cortex.extensions.revenue.vectors.bounty")

# Extend VectorType with BOUNTY if not present
# Since VectorType is an Enum, we register it dynamically
BOUNTY_VECTOR_TYPE = "bounty"

# Ouroboros strike ledger location
STRIKE_LEDGER_PATH = os.environ.get(
    "CORTEX_STRIKE_LEDGER",
    os.path.expanduser(
        "~/10_PROJECTS/cortex-persist/.scratch/ouroboros/"
        "ouroboros_strike_ledger.jsonl"
    ),
)


@dataclass
class BountyProgram:
    """An active bounty program on Immunefi/Code4rena/etc."""
    platform: str       # "immunefi", "code4rena", "sherlock"
    project: str        # "firedancer-v1", "exactly-protocol"
    max_payout: Decimal  # Maximum bounty payout in USD
    scope_urls: list[str]
    tvl_usd: Decimal = Decimal("0")
    active: bool = True
    meta: dict[str, Any] | None = None


class BountyStrikeVector:
    """Bounty hunting as a revenue vector.

    Scans the Ouroboros strike ledger for submitted findings,
    estimates payouts based on severity and program maxima,
    and tracks the pipeline from submission to payout.

    Implements the RevenueVector protocol from cortex.extensions.revenue.models.
    """

    def __init__(
        self,
        ledger_path: str = STRIKE_LEDGER_PATH,
        active_programs: list[BountyProgram] | None = None,
    ) -> None:
        self._id = BOUNTY_VECTOR_TYPE
        self._name = "Ouroboros Bounty Strikes"
        self._enabled = True
        self.ledger_path = ledger_path
        self.active_programs = active_programs or []
        self._payout_estimates = self._load_payout_estimates()
        
        # Initialize Autodidact Guard for L2 Hardening
        # In a real scenario, this would use a persistent key from vault
        kp = ZKSwarmIdentity.generate_keypair()
        self.guard = AutodidactGuard(kp.private_key_b64, "bounty-vector-01")

    def _save_ledger(self, entries: list[dict[str, Any]]) -> None:
        """Atomically save the strike ledger."""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        temp_path = f"{self.ledger_path}.tmp"
        try:
            with open(temp_path, "w") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
            os.replace(temp_path, self.ledger_path)
        except OSError as e:
            logger.error("Failed to save strike ledger: %s", e)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @property
    def id(self) -> Any:
        """Vector identifier."""
        return self._id

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._name

    @property
    def enabled(self) -> bool:
        """Whether this vector is active."""
        return self._enabled

    async def scan(self) -> list[Opportunity]:
        """Scan the strike ledger for submitted/pending findings.

        Each submitted finding becomes an Opportunity with estimated
        payout based on severity classification.

        Returns:
            List of bounty opportunities sorted by estimated payout.
        """
        entries = self._read_ledger()
        modified = False

        opportunities: list[Opportunity] = []
        for entry in entries:
            status = entry.get("status", "").upper()
            if status not in ("SUBMITTED", "PREPARED", "TRIAGED"):
                continue

            # --- L2 Conformance Gate ---
            # If the entry lacks a PDR, we force validation now.
            if not entry.get("pdr_id"):
                logger.info("🛡️ [BOUNTY] Hardening strike %s (L2 Conformance)...", entry.get("vulnerability_id"))
                
                proposal = {
                    "operations": entry.get("operations", [
                        {
                            "type": "bounty_submission",
                            "target": entry.get("target"),
                            "severity": entry.get("severity")
                        }
                    ]),
                    "metadata": {
                        "title": entry.get("title"),
                        "project": entry.get("target"),
                        "severity": entry.get("severity")
                    }
                }
                
                is_valid, pdr = await self.guard.validate_proposal(
                    proposal=proposal,
                    chain_id=entry.get("chain_id", 1),
                    sender="0xBOUNTY_VECTOR"
                )
                
                if is_valid:
                    entry["pdr_id"] = pdr.decision_id
                    entry["intent_id"] = pdr.intent_id
                    modified = True
                    logger.info("✅ [BOUNTY] Strike %s validated. PDR: %s", entry.get("vulnerability_id"), pdr.decision_id)
                else:
                    logger.warning("❌ [BOUNTY] Strike %s FAILED validation. Skipping.", entry.get("vulnerability_id"))
                    continue

            # --- L2+ Anvil Simulation Gate ---
            # If an .anv spec exists for this strike, require formal verification
            anv_path = self._find_anv_spec(entry)
            if anv_path:
                from cortex.verification.simulation import SimulationGate
                from cortex.extensions.security.tis_schema import TransactionIntentSchema

                sim_gate = SimulationGate(use_anvil=True)
                tis = TransactionIntentSchema(
                    intent_id=entry.get("intent_id", entry.get("vulnerability_id", "unknown")),
                    chain_id=entry.get("chain_id", 1),
                    sender="0xBOUNTY_VECTOR",
                    operations=entry.get("operations", [
                        {"type": "bounty_submission", "target": entry.get("target")}
                    ]),
                    metadata={"strike_id": entry.get("vulnerability_id", "")},
                )
                sim_result, anv_result = await sim_gate.full_gate(tis, anv_path=anv_path)

                if anv_result and anv_result.verified:
                    entry["anvil_verified"] = True
                    entry["anvil_proof_hashes"] = anv_result.proof_hashes
                    entry["poc_verified"] = True
                    modified = True
                    logger.info(
                        "🔬 [ANVIL] Strike %s formally verified (%d invariants, %s)",
                        entry.get("vulnerability_id"),
                        anv_result.invariants_proven,
                        anv_result.reality_level,
                    )
                elif anv_result and not anv_result.verified:
                    entry["anvil_verified"] = False
                    entry["anvil_counterexamples"] = anv_result.counterexamples
                    modified = True
                    logger.warning(
                        "⚠️ [ANVIL] Strike %s has counterexamples — downgrading to PREPARED",
                        entry.get("vulnerability_id"),
                    )
                    if entry.get("status", "").upper() == "SUBMITTED":
                        entry["status"] = "PREPARED"

            severity = entry.get("severity", "medium").lower()
            estimated_payout = self._estimate_payout(
                severity=severity,
                platform=entry.get("platform", "immunefi"),
                project=entry.get("project", ""),
            )

            opp = Opportunity(
                vector=VectorType.ARBITRAGE,  # Reuse closest type
                title=f"Bounty: {entry.get('title', entry.get('id', 'unknown'))}",
                description=(
                    f"[{severity.upper()}] {entry.get('project', 'unknown')} — "
                    f"{entry.get('description', entry.get('title', ''))}"
                ),
                estimated_value=estimated_payout,
                confidence="C5" if entry.get("poc_verified") else "C4",
                effort_hours=self._estimate_effort(severity),
                status=OpportunityStatus.DETECTED,
                source_url=entry.get("submission_url", ""),
                meta={
                    "strike_id": entry.get("vulnerability_id", entry.get("id", "")),
                    "intent_id": entry.get("intent_id", ""),
                    "pdr_id": entry.get("pdr_id", ""),
                    "chain_id": entry.get("chain_id", 0),
                    "platform": entry.get("platform", "immunefi"),
                    "project": entry.get("project", ""),
                    "severity": severity,
                    "taint_hash": entry.get("taint_hash", ""),
                    "submitted_at": entry.get("timestamp", entry.get("synced_at", "")),
                },
            )
            opportunities.append(opp)

        if modified:
            self._save_ledger(entries)

        logger.info(
            "🎯 [BOUNTY] Scanned ledger: %d active submissions found.",
            len(opportunities),
        )
        return opportunities

    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Track a bounty through to payout.

        Since bounty payouts are external (platform-mediated),
        execution here means:
        1. Verify submission status on the platform
        2. Update ledger with status change
        3. Record payout when confirmed

        Returns:
            Execution result (success = payout confirmed).
        """
        strike_id = opportunity.meta.get("strike_id", "")
        platform = opportunity.meta.get("platform", "")

        logger.info(
            "📬 [BOUNTY] Tracking payout for %s on %s...",
            strike_id, platform,
        )

        # In C5-REAL: Query Immunefi API for submission status
        # Currently: Mark as pending (manual verification required)
        return ExecutionResult(
            opportunity_id=opportunity.id,
            success=False,  # Not yet paid
            revenue_actual=Decimal("0"),
            cost_actual=Decimal("0"),
            error="Payout pending — requires manual platform verification.",
            meta={
                "strike_id": strike_id,
                "platform": platform,
                "status": "PENDING_REVIEW",
            },
        )

    def _read_ledger(self) -> list[dict[str, Any]]:
        """Read the JSONL strike ledger."""
        if not os.path.exists(self.ledger_path):
            logger.debug(
                "Strike ledger not found at %s, returning empty.",
                self.ledger_path,
            )
            return []

        entries: list[dict[str, Any]] = []
        try:
            with open(self.ledger_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError as e:
            logger.warning("Failed to read strike ledger: %s", e)

        return entries

    def _estimate_payout(
        self,
        severity: str,
        platform: str,
        project: str,
    ) -> Decimal:
        """Estimate bounty payout based on severity and program.

        Severity tiers (Immunefi standard):
        - Critical: $10,000 — $1,000,000
        - High: $5,000 — $50,000
        - Medium: $1,000 — $10,000
        - Low: $100 — $1,000
        """
        base_estimates = {
            "critical": Decimal("50000"),
            "high": Decimal("10000"),
            "medium": Decimal("3000"),
            "low": Decimal("500"),
        }
        return base_estimates.get(severity, Decimal("1000"))

    def _estimate_effort(self, severity: str) -> float:
        """Estimate hours of effort per severity level."""
        effort_map = {
            "critical": 40.0,   # Deep audit + PoC
            "high": 20.0,       # Focused analysis + PoC
            "medium": 8.0,      # Targeted check
            "low": 2.0,         # Quick scan
        }
        return effort_map.get(severity, 10.0)

    def _load_payout_estimates(self) -> dict[str, Decimal]:
        """Load historical payout data for calibration."""
        # Will be populated from actual payout history
        return {}

    def _find_anv_spec(self, entry: dict[str, Any]) -> Any:
        """Search for an Anvil-lang .anv specification file for a strike.

        Search locations (in order):
          1. cortex-bounties/targets/<project>/*.anv
          2. anvil-lang/examples/*.anv (by project name match)
          3. anvil-lang/targets/<project>/*.anv

        Returns:
            Path to the first matching .anv file, or None.
        """
        from pathlib import Path

        vuln_id = entry.get("vulnerability_id", "").lower().replace("-", "_")
        project = entry.get("project", "").lower().replace("-", "_").replace(" ", "_")
        target = entry.get("target", "").lower().replace("-", "_").replace(" ", "_")

        search_dirs = [
            Path.home() / "10_PROJECTS" / "cortex-bounties" / "targets",
            Path.home() / "10_PROJECTS" / "anvil-lang" / "examples",
            Path.home() / "10_PROJECTS" / "anvil-lang" / "targets",
        ]

        search_terms = [t for t in (vuln_id, project, target) if t]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            # Search recursively for .anv files
            for anv_file in search_dir.rglob("*.anv"):
                name_lower = anv_file.stem.lower().replace("-", "_")
                for term in search_terms:
                    if term in name_lower or name_lower in term:
                        logger.debug("Found .anv spec: %s (matched term: %s)", anv_file, term)
                        return anv_file

        return None
