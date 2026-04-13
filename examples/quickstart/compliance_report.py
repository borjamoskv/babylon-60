#!/usr/bin/env python3
"""CORTEX Quickstart: EU AI Act Compliance Report.

Demonstrates how to generate an Article 12 report using the synchronous
ComplianceTracker wrapper shipped with CORTEX.

Usage:
    python examples/quickstart/compliance_report.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cortex.compliance.tracker import ComplianceTracker


def main() -> None:
    db_path = Path(tempfile.mkdtemp()) / "compliance.db"
    tracker = ComplianceTracker(db_path=str(db_path), project="fintech-agent")

    print("📋 CORTEX Quickstart — EU AI Act Compliance Report\n")

    # --- Step 1: Simulate an agent's decision history ---
    print("1️⃣  Simulating agent decision history...\n")

    decisions = [
        ("approval", "Approved loan application #443 — risk score 0.23"),
        ("rejection", "Rejected application #444 — income verification failed"),
        ("observation", "Risk model v2.1 deployed — AUC 0.94 on validation set"),
        ("incident", "Timeout on credit bureau API — retried 3x, succeeded"),
        ("approval", "Approved application #445 — manual review flagged"),
    ]

    for decision_type, content in decisions:
        tracker.log_decision(
            content=content,
            agent_id="agent:loan-processor",
            decision_type=decision_type,
        )
        print(f"   📝 [{decision_type}] {content[:60]}")

    # --- Step 2: Generate compliance report ---
    print("\n2️⃣  Generating EU AI Act compliance report...\n")
    report = tracker.export_audit(include_facts=True)
    eu = report["eu_ai_act"]
    integrity = report["integrity"]
    summary = report["facts_summary"]

    print("   🏛️  EU AI Act Article 12 Compliance")
    print(f"   {'=' * 40}")
    print(f"   Score:         {eu['score']}")
    print(f"   Status:        {eu['status']}")
    print(f"   Total Facts:   {summary.get('total_facts', 0)}")
    print(f"   Decisions:     {summary.get('decision_count', 0)}")

    checks = eu.get("checks", {})
    if checks:
        print("\n   Requirements:")
        for check_name, check_result in checks.items():
            icon = "✅" if check_result.get("compliant") else "❌"
            print(f"     {icon} {check_name}")

    # --- Step 3: Verify chain integrity ---
    print("\n3️⃣  Verifying ledger integrity...")
    icon = "✅" if integrity.get("valid", False) else "❌"
    print(f"   {icon} Ledger valid: {integrity.get('valid', False)}")
    print(f"   Transactions checked: {integrity.get('tx_checked', 0)}")
    print(f"   Roots checked:        {integrity.get('roots_checked', 0)}")

    print("\n✨ Compliance report ready for regulatory submission.")
    print("   All decisions are hash-chained and Merkle-sealed.")


if __name__ == "__main__":
    main()
