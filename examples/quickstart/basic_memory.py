#!/usr/bin/env python3
"""CORTEX Quickstart: Store and verify a decision.

This example shows the core CORTEX workflow:
1. Store a fact with cryptographic integrity
2. Verify its hash chain
3. Check the full ledger integrity

Usage:
    python examples/quickstart/basic_memory.py
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def main() -> None:
    # Use a temporary database for this example
    db_path = Path(tempfile.mkdtemp()) / "quickstart.db"

    # Import CortexEngine — the single entry point for all operations
    from cortex import CortexEngine

    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    await engine.init_db()

    print("🧠 CORTEX Quickstart — Basic Memory\n")

    # --- Step 1: Store facts ---
    print("1️⃣  Storing decisions...")
    fact1_id = await engine.store(
        content="Chose OAuth2 PKCE for authentication",
        fact_type="decision",
        project="quickstart",
        source="human:developer",
    )
    fact1 = await engine.get_fact(fact1_id)
    print(f"   ✅ Fact #{fact1_id} stored (hash: {(fact1.hash or '')[:12]}...)")

    fact2_id = await engine.store(
        content="Selected PostgreSQL over MongoDB for audit compliance",
        fact_type="decision",
        project="quickstart",
        source="human:architect",
    )
    fact2 = await engine.get_fact(fact2_id)
    print(f"   ✅ Fact #{fact2_id} stored (hash: {(fact2.hash or '')[:12]}...)")

    # --- Step 2: Verify ledger integrity ---
    print("\n2️⃣  Verifying ledger integrity...")
    result = await engine.verify_ledger()
    status = "✅ VERIFIED" if result["valid"] else "❌ BROKEN"
    print(f"   {status} — Transactions checked: {result.get('tx_checked', 0)}")

    # --- Step 3: Search facts ---
    print("\n3️⃣  Searching memory...")
    facts = await engine.search(query="authentication", project="quickstart", top_k=5)
    print(f"   Found {len(facts)} matching fact(s)")
    for f in facts:
        print(f"   → [{f.fact_type}] {f.content[:60]}")

    # --- Step 4: Inspect stats ---
    print("\n4️⃣  Stats snapshot...")
    stats = await engine.stats()
    print(f"   Total facts: {stats.get('total_facts', 0)}")
    print(f"   Active facts: {stats.get('active_facts', 0)}")

    print("\n✨ Done! CORTEX verified all decisions with cryptographic integrity.")
    print(f"   Database: {db_path}")
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
