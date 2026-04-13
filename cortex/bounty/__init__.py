"""
Cortex-Persist Bounty Bridge.
Provides cryptographic sealing of bug bounty findings into the L3 event ledger.
"""
from cortex.bounty.ledger_bridge import BountyLedgerBridge, get_sealed_findings, seal_finding

__all__ = ["BountyLedgerBridge", "seal_finding", "get_sealed_findings"]
