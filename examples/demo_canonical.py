"""CORTEX Persist — Official product demo.

Demonstrates the canonical product flow in under 3 minutes:
  1. Register an AI decision.
  2. Verify cryptographic integrity.
  3. Export audit evidence as JSON.

Run:
    pip install -e .
    PYTHONPATH=. python examples/demo_canonical.py
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cortex.compliance import ComplianceTracker
from cortex.crypto.aes import reset_default_encrypter

DEMO_PROJECT = "official-product-demo"
DEMO_AGENT = "agent:credit-risk"


def _ensure_demo_master_key() -> None:
    """Bootstrap a process-local master key for clean demo environments."""
    if os.environ.get("CORTEX_MASTER_KEY") or os.environ.get("CORTEX_VAULT_KEY"):
        return

    os.environ.setdefault("CORTEX_TESTING", "1")
    os.environ["CORTEX_MASTER_KEY"] = base64.b64encode(os.urandom(32)).decode("ascii")
    reset_default_encrypter()


def run_demo(output_dir: Path | None = None) -> dict[str, Any]:
    """Run the official demo and return the generated artifacts."""
    _ensure_demo_master_key()

    artifact_dir = output_dir or Path(tempfile.mkdtemp(prefix="cortex-demo-"))
    artifact_dir.mkdir(parents=True, exist_ok=True)

    db_path = artifact_dir / "official-demo.db"
    audit_path = artifact_dir / "official-demo-audit.json"

    with ComplianceTracker(db_path=str(db_path), project=DEMO_PROJECT) as tracker:
        fact_id = tracker.log_decision(
            content="approved loan application 443 after review pass and policy checks.",
            agent_id=DEMO_AGENT,
            decision_type="approval",
            confidence="C4",
            meta={
                "customer_id": "cust-443",
                "risk_score": "0.18",
                "policy_version": "credit-v3",
            },
            tags=["official-demo", "credit-risk"],
        )
        integrity = tracker.verify_chain()
        audit_report = tracker.export_audit(include_facts=True)

    audit_path.write_text(
        json.dumps(audit_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "artifact_dir": artifact_dir,
        "db_path": db_path,
        "audit_path": audit_path,
        "fact_id": fact_id,
        "integrity": integrity,
        "audit_report": audit_report,
    }


def main() -> None:
    """Print the official demo walkthrough and artifact locations."""
    result = run_demo()
    integrity = result["integrity"]
    audit_report = result["audit_report"]

    print("CORTEX Persist — Official product demo")
    print("=" * 40)
    print("1. Register decision")
    print(f"   Stored fact #{result['fact_id']} for {DEMO_PROJECT} from {DEMO_AGENT}.")
    print("2. Verify integrity")
    print(
        f"   Ledger valid: {integrity.get('valid', False)} "
        f"({integrity.get('tx_checked', 0)} transaction(s) checked)."
    )
    print("3. Export evidence")
    print(
        f"   Wrote JSON audit evidence with score "
        f"{audit_report['eu_ai_act']['score']} to {result['audit_path']}"
    )
    print()
    print(f"Artifacts: {result['artifact_dir']}")
    print(f"Database: {result['db_path']}")


if __name__ == "__main__":
    main()
