from __future__ import annotations

import os
from pathlib import Path

import pytest

from cortex.core.lineage import LineageVerifier
from cortex.engine import CortexEngine
from cortex.search.text import text_search


class _FakeEnc:
    def encrypt_str(self, value: str, **_: object) -> str:
        return value

    def decrypt_str(self, value: str, **_: object) -> str:
        return value

    def encrypt_json(self, value: object, **_: object) -> str:
        import json

        return json.dumps(value)

    def decrypt_json(self, value: object, **_: object):
        import json

        return json.loads(str(value))


class _FakeSigner:
    can_sign = False


@pytest.mark.asyncio
async def test_new_fact_persists_tx_id_and_search_uses_fact_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: _FakeEnc())
    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: _FakeSigner(),
    )

    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    engine = CortexEngine(db_path=str(tmp_path / "lineage-fresh.db"), auto_embed=False)

    try:
        await engine.init_db()
        fact_id = await engine.store(
            project="lineage",
            content="lineage search anchor fact",
            fact_type="knowledge",
            source="test-suite",
            bicameral=False,
        )

        fact = await engine.get_fact(fact_id)
        assert fact is not None
        assert fact.tx_id is not None
        assert fact.hash is not None

        async with engine.session() as conn:
            results = await text_search(
                conn,
                "lineage anchor",
                tenant_id="default",
                project="lineage",
                limit=5,
            )

        assert len(results) == 1
        assert results[0].fact_id == fact_id
        assert results[0].tx_id == fact.tx_id
        assert results[0].hash == fact.hash

        lineage = await LineageVerifier(engine).get_lineage(fact_id)
        assert lineage.is_valid is True
    finally:
        await engine.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)
