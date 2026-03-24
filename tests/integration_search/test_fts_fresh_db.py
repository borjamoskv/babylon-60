from __future__ import annotations

import os
from pathlib import Path

import pytest

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
async def test_fresh_db_uses_single_manual_fts_indexing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: _FakeEnc())
    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: _FakeSigner(),
    )

    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    engine = CortexEngine(db_path=str(tmp_path / "fts-fresh.db"), auto_embed=False)

    try:
        await engine.init_db()
        fact_id = await engine.store(
            project="search-policy",
            content="fresh db searchable plaintext fact",
            fact_type="knowledge",
            source="test-suite",
        )

        async with engine.session() as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM facts_fts WHERE rowid = ?",
                (fact_id,),
            ) as cursor:
                row_count = (await cursor.fetchone())[0]

            results = await text_search(
                conn,
                "searchable plaintext",
                tenant_id="default",
                project="search-policy",
                limit=5,
            )

        assert row_count == 1
        assert [result.fact_id for result in results] == [fact_id]
    finally:
        await engine.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)
