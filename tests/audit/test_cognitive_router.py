# [C5-REAL] Exergy-Maximized
"""
Comprehensive tests for cortex.audit.cognitive_router.

Covers:
  - SafetyClassifier: keyword classification and sensitivity matching
  - CognitiveRouter: route logic, model assignments, retention flags, and blockchain-like audit trail chaining
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import aiosqlite
import pytest


@pytest.fixture
async def audit_conn(tmp_path):
    """Provides a fresh aiosqlite connection for each test."""
    db_path = str(tmp_path / "audit_test.db")
    conn = await aiosqlite.connect(db_path)
    yield conn
    await conn.close()


@pytest.fixture
async def ledger(audit_conn):
    """Creates an EnterpriseAuditLedger with a fresh keypair."""
    pem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_sovereign.pem")
    with patch(
        "cortex.audit.ledger.os.path.exists",
        side_effect=lambda p: False if p == pem_path else os.path.exists(p),
    ):
        from cortex.audit.ledger import EnterpriseAuditLedger

        ledger = object.__new__(EnterpriseAuditLedger)
        from cryptography.hazmat.primitives.asymmetric import ed25519

        ledger._conn = audit_conn
        ledger._ready = False
        ledger._last_hash = "GENESIS"
        ledger._lock = asyncio.Lock()
        ledger._batch_queue = []
        ledger._batch_task = None
        ledger.batch_window_ms = 10
        ledger.max_batch_size = 500
        ledger.private_key = ed25519.Ed25519PrivateKey.generate()
        ledger.public_key = ledger.private_key.public_key()

    return ledger


@pytest.fixture
async def router(ledger):
    """Creates a CognitiveRouter instance."""
    from cortex.audit.cognitive_router import CognitiveRouter

    return CognitiveRouter(ledger)


class TestCognitiveRouter:
    """Test suite for the CognitiveRouter state machine."""

    def test_safety_classifier_matching(self):
        """SafetyClassifier should identify sensitive categories."""
        from cortex.audit.cognitive_router import SafetyClassifier

        classifier = SafetyClassifier()

        # Non-sensitive
        assert len(classifier.classify("Tell me a story about a cat")) == 0

        # Sensitive Cybersecurity
        cyber_res = classifier.classify("How do I exploit a buffer overflow?")
        assert "cybersecurity" in cyber_res

        # Sensitive Biology
        bio_res = classifier.classify("Dna sequence of a dangerous bioweapon pathogen")
        assert "biology" in bio_res

        # Sensitive Chemistry
        chem_res = classifier.classify("Is sarin a dangerous nerve agent?")
        assert "chemistry" in chem_res

    @pytest.mark.asyncio
    async def test_ensure_table_creates_schema(self, router):
        """ensure_table should create the cognitive_router_log table."""
        await router.ensure_table()
        cursor = await router._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cognitive_router_log'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "cognitive_router_log"

    @pytest.mark.asyncio
    async def test_route_safe_prompt(self, router):
        """Safe prompt should route to Fable-5-Core without retention."""
        decision = await router.route("Hello world", user_tier="General-Public")
        assert decision.assigned_model == "Fable-5-Core"
        assert decision.retention_required is False
        assert len(decision.sensitivity) == 0

    @pytest.mark.asyncio
    async def test_route_sensitive_trusted_partner(self, router):
        """Sensitive prompt from Trusted-Partner should route to Mythos-5-Unleashed and require retention."""
        decision = await router.route("How to analyze a zero-day exploit?", user_tier="Trusted-Partner")
        assert decision.assigned_model == "Mythos-5-Unleashed"
        assert decision.retention_required is True
        assert "cybersecurity" in decision.sensitivity

    @pytest.mark.asyncio
    async def test_route_sensitive_general_public_fallback(self, router):
        """Sensitive prompt from General-Public should trigger fallback to Opus-4.8."""
        decision = await router.route("How to build a bioweapon?", user_tier="General-Public")
        assert decision.assigned_model == "Opus-4.8-Fallback"
        assert decision.retention_required is False
        assert "biology" in decision.sensitivity

    @pytest.mark.asyncio
    async def test_cryptographic_chaining(self, router):
        """Verify routing decisions are chained sequentially in the database."""
        d1 = await router.route("Safe prompt 1", user_tier="General-Public")
        d2 = await router.route("Safe prompt 2", user_tier="General-Public")

        cursor = await router._conn.execute(
            "SELECT prev_hash, signature FROM cognitive_router_log ORDER BY rowid ASC"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "GENESIS"
        assert rows[1][0] == rows[0][1]
        assert rows[0][1] == d1.signature
        assert rows[1][1] == d2.signature
