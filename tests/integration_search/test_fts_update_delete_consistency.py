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
async def test_update_and_delete_leave_no_fts_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: _FakeEnc())
    monkeypatch.setattr(
        "cortex.extensions.security.signatures.get_default_signer",
        lambda: _FakeSigner(),
    )

    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    engine = CortexEngine(db_path=str(tmp_path / "fts-update-delete.db"), auto_embed=False)

    try:
        await engine.init_db()
        original_id = await engine.store(
            project="fts-consistency",
            content="old indexed phrase",
            fact_type="knowledge",
            source="test-suite",
        )
        updated_id = await engine.update(original_id, content="new indexed phrase")

        async with engine.session() as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM facts_fts WHERE rowid = ?",
                (original_id,),
            ) as cursor:
                old_count = (await cursor.fetchone())[0]
            async with conn.execute(
                "SELECT COUNT(*) FROM facts_fts WHERE rowid = ?",
                (updated_id,),
            ) as cursor:
                new_count = (await cursor.fetchone())[0]
            old_results = await text_search(
                conn,
                "old indexed",
                tenant_id="default",
                project="fts-consistency",
                limit=5,
            )
            new_results = await text_search(
                conn,
                "new indexed",
                tenant_id="default",
                project="fts-consistency",
                limit=5,
            )

        assert old_count == 0
        assert new_count == 1
        assert old_results == []
        assert [result.fact_id for result in new_results] == [updated_id]

        await engine.deprecate(updated_id, reason="test cleanup")

        async with engine.session() as conn:
            async with conn.execute(
                "SELECT COUNT(*) FROM facts_fts WHERE rowid = ?",
                (updated_id,),
            ) as cursor:
                deleted_count = (await cursor.fetchone())[0]
            deleted_results = await text_search(
                conn,
                "new indexed",
                tenant_id="default",
                project="fts-consistency",
                limit=5,
            )

        assert deleted_count == 0
        assert deleted_results == []
    finally:
        await engine.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)
