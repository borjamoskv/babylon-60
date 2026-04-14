"""Tests for Crypto-Shredding Engine — Phase 2."""

import sqlite3

import pytest

from cortex.crypto.shredder import CryptoShredder


@pytest.fixture
def db():
    """In-memory SQLite with facts table."""
    conn = sqlite3.Connection(":memory:")
    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT,
            project TEXT,
            source TEXT,
            tenant_id TEXT DEFAULT 'default'
        )
    """)
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (1, 'secret data', 'test', 'user:alice')"
    )
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (2, 'more data', 'test', 'user:alice')"
    )
    conn.execute(
        "INSERT INTO facts (id, content, project, source) VALUES (3, 'other data', 'test', 'user:bob')"
    )
    conn.commit()
    return conn


class TestCryptoShredder:
    """Crypto-shredding tests (sync API)."""

    def test_shred_single_fact(self, db):
        shredder = CryptoShredder(db)
        result = shredder.shred_fact(1)
        assert result.success
        assert not result.was_already_shredded
        assert shredder.is_shredded(1)

    def test_shred_already_shredded(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1)
        result = shredder.shred_fact(1)
        assert result.success
        assert result.was_already_shredded

    def test_is_shredded_false(self, db):
        shredder = CryptoShredder(db)
        assert not shredder.is_shredded(999)

    def test_get_shredded_ids(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1)
        shredder.shred_fact(3)
        ids = shredder.get_shredded_fact_ids()
        assert ids == {1, 3}

    def test_shred_with_reason(self, db):
        shredder = CryptoShredder(db)
        result = shredder.shred_fact(1, reason="user_request", shredded_by="admin")
        assert result.success
        assert result.reason == "user_request"

    def test_audit_shredding(self, db):
        shredder = CryptoShredder(db)
        shredder.shred_fact(1, reason="gdpr_erasure")
        shredder.shred_fact(2, reason="gdpr_erasure")
        shredder.shred_fact(3, reason="project_erasure")

        audit = shredder.audit_shredding()
        assert audit["total_shredded"] == 3
        assert audit["compliant"]
        assert "gdpr_erasure" in audit["by_reason"]
        assert audit["by_reason"]["gdpr_erasure"]["count"] == 2

    def test_empty_audit(self, db):
        shredder = CryptoShredder(db)
        audit = shredder.audit_shredding()
        assert audit["total_shredded"] == 0
        assert audit["compliant"]


# ─── Per-fact encryption + engine-level shredding ─────────────────────────────

import pytest

from cortex.crypto.aes import SHREDDED_CONTENT_MARKER, CortexEncrypter


class TestPerFactEncryption:
    """Unit tests for the per-fact AES-256-GCM encryption primitives."""

    def test_encrypt_returns_prefix_and_key(self):
        enc = CortexEncrypter(b"\x00" * 32)
        ciphertext, fact_key = enc.encrypt_str_for_fact("hello world", "default")
        assert ciphertext is not None
        assert ciphertext.startswith(CortexEncrypter.FACT_ENC_PREFIX)
        assert fact_key is not None
        assert len(fact_key) == 32

    def test_decrypt_roundtrip(self):
        enc = CortexEncrypter(b"\x00" * 32)
        plaintext = "sensitive personal data"
        ciphertext, fact_key = enc.encrypt_str_for_fact(plaintext, "default")
        recovered = enc.decrypt_str_for_fact(ciphertext, fact_key)
        assert recovered == plaintext

    def test_decrypt_with_none_key_returns_shredded_marker(self):
        enc = CortexEncrypter(b"\x00" * 32)
        ciphertext, _ = enc.encrypt_str_for_fact("secret", "default")
        # Simulate shredded state (key is gone)
        result = enc.decrypt_str_for_fact(ciphertext, None)
        assert result == SHREDDED_CONTENT_MARKER

    def test_decrypt_wrong_key_returns_shredded_marker(self):
        enc = CortexEncrypter(b"\x00" * 32)
        ciphertext, _ = enc.encrypt_str_for_fact("secret", "default")
        wrong_key = b"\xff" * 32
        result = enc.decrypt_str_for_fact(ciphertext, wrong_key)
        assert result == SHREDDED_CONTENT_MARKER

    def test_legacy_prefix_is_passed_through(self):
        enc = CortexEncrypter(b"\x00" * 32)
        # A v6 tenant-encrypted blob should NOT be handled by decrypt_str_for_fact
        legacy = enc.encrypt_str("data", tenant_id="default")
        # decrypt_str_for_fact should return the raw value (not per-fact prefix)
        result = enc.decrypt_str_for_fact(legacy, None)
        assert result == legacy  # passed through unchanged

    def test_empty_content_passthrough(self):
        enc = CortexEncrypter(b"\x00" * 32)
        ct, key = enc.encrypt_str_for_fact("", "default")
        assert ct == ""
        assert key is None

    def test_encrypt_produces_unique_ciphertexts(self):
        """Each call must use a fresh nonce → same plaintext → different ciphertexts."""
        enc = CortexEncrypter(b"\x00" * 32)
        ct1, _ = enc.encrypt_str_for_fact("same data", "default")
        ct2, _ = enc.encrypt_str_for_fact("same data", "default")
        assert ct1 != ct2  # non-deterministic due to random nonce + random key


class TestCryptoShredderKeyStore:
    """Integration tests: engine stores per-fact keys and shred() deletes them."""

    def _make_engine(self, tmp_db_path: str):
        from cortex.engine import CortexEngine
        return CortexEngine(tmp_db_path)

    @pytest.mark.asyncio
    async def test_per_fact_key_stored_in_crypto_keys(self, tmp_path):
        """Storing a fact must create an entry in crypto_keys."""
        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        fact_id = await eng.store("project", "personal data here", tenant_id="default")
        assert isinstance(fact_id, int)

        async with eng.session() as conn:
            cursor = await conn.execute(
                "SELECT fact_key FROM crypto_keys WHERE fact_id = ?", (fact_id,)
            )
            row = await cursor.fetchone()

        assert row is not None, "Per-fact key must be stored in crypto_keys"
        assert row[0] is not None
        assert len(row[0]) == 32  # 256-bit AES key

        await eng.close()

    @pytest.mark.asyncio
    async def test_shred_deletes_key_from_crypto_keys(self, tmp_path):
        """shred_fact() must delete the key from crypto_keys."""
        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        fact_id = await eng.store("project", "PII data to erase", tenant_id="default")

        result = await eng.shred_fact(fact_id, tenant_id="default")
        assert result["success"]
        assert not result["was_already_shredded"]

        async with eng.session() as conn:
            cursor = await conn.execute(
                "SELECT fact_key FROM crypto_keys WHERE fact_id = ?", (fact_id,)
            )
            row = await cursor.fetchone()

        assert row is None, "Key must be deleted from crypto_keys after shredding"

        await eng.close()

    @pytest.mark.asyncio
    async def test_shredded_fact_returns_shredded_marker(self, tmp_path):
        """After shredding, retrieving the fact must return SHREDDED_DATA."""
        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        fact_id = await eng.store("project", "private user data — full name and address stored here", tenant_id="default")

        # Verify the fact is readable before shredding
        fact_before = await eng.get_fact(fact_id)
        assert fact_before is not None
        assert fact_before.content == "private user data — full name and address stored here"

        # Shred the fact
        await eng.shred_fact(fact_id, tenant_id="default", reason="gdpr_erasure")

        # After shredding the content must be unreadable
        fact_after = await eng.get_fact(fact_id)
        assert fact_after is not None
        assert fact_after.content == SHREDDED_CONTENT_MARKER

        await eng.close()

    @pytest.mark.asyncio
    async def test_hash_chain_intact_after_shredding(self, tmp_path):
        """The transaction ledger must still have a valid prev_hash chain after shredding."""
        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        fact_id = await eng.store("project", "data to be erased", tenant_id="default")
        await eng.shred_fact(fact_id)

        # The transactions table still has the record
        async with eng.session() as conn:
            cursor = await conn.execute(
                "SELECT hash, prev_hash FROM transactions ORDER BY id ASC"
            )
            rows = await cursor.fetchall()

        assert len(rows) > 0, "Transaction log must persist after shredding"
        # Verify chain: every row's prev_hash equals the previous row's hash
        for i in range(1, len(rows)):
            cur_row_prev = rows[i][1]
            prev_row_hash = rows[i - 1][0]
            assert cur_row_prev == prev_row_hash, (
                f"Hash chain broken between tx {i - 1} and {i}"
            )

        await eng.close()

    @pytest.mark.asyncio
    async def test_ciphertext_hash_in_transaction_detail(self, tmp_path):
        """Storing a fact must include a ciphertext hash in the transaction detail."""
        import json

        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        await eng.store("proj", "important data", tenant_id="default")

        async with eng.session() as conn:
            cursor = await conn.execute(
                "SELECT detail FROM transactions WHERE action = 'store' LIMIT 1"
            )
            row = await cursor.fetchone()

        assert row is not None
        detail = json.loads(row[0])
        assert "content_ciphertext_hash" in detail, (
            "Transaction detail must contain content_ciphertext_hash for the hash chain"
        )
        ciphertext_hash = detail["content_ciphertext_hash"]
        assert len(ciphertext_hash) == 64  # SHA-256 hex digest

        await eng.close()

    @pytest.mark.asyncio
    async def test_shred_idempotent(self, tmp_path):
        """Calling shred_fact twice must succeed without error."""
        db_path = str(tmp_path / "test.db")
        eng = self._make_engine(db_path)
        await eng.init_db()

        fact_id = await eng.store("project", "this is sufficiently long content for the thalamus filter to pass", tenant_id="default")

        r1 = await eng.shred_fact(fact_id)
        r2 = await eng.shred_fact(fact_id)

        assert r1["success"]
        assert r2["success"]
        assert r2["was_already_shredded"]

        await eng.close()

