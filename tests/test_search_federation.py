from __future__ import annotations

import pytest

from cortex.crypto.aes import CortexEncrypter
from cortex.search import federation
from cortex.search.models import SearchResult


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeSyncConn:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def execute(self, sql: str, params: list[object]) -> _FakeCursor:
        return _FakeCursor(self.rows)


class _FakeEncrypter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def decrypt_str(self, payload: str, tenant_id: str) -> str:
        self.calls.append(tenant_id)
        return f"decrypted:{payload}"


def test_search_attached_db_uses_requested_tenant_for_decryption(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_encrypter = _FakeEncrypter()
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: fake_encrypter)

    encrypted_content = f"{CortexEncrypter.PREFIX}ciphertext"
    conn = _FakeSyncConn(
        [
            (1, encrypted_content, "alpha", "decision", "C4", "source", '["policy"]'),
        ],
    )

    results = federation._search_attached_db(
        conn,
        "personal",
        "cipher",
        tenant_id="tenant-search",
        project="alpha",
        limit=10,
    )

    assert fake_encrypter.calls == ["tenant-search"]
    assert results == [
        SearchResult(
            fact_id=1,
            content=f"decrypted:{encrypted_content}",
            project="alpha",
            fact_type="decision",
            confidence="C4",
            valid_from="unknown",
            valid_until=None,
            tags=["policy"],
            created_at="unknown",
            updated_at="unknown",
            source="source",
            score=0.5,
            db_origin="personal",
        ),
    ]


def test_federated_search_sync_forwards_tenant_id(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_text_search_sync(conn, query, tenant_id="default", project=None, limit=20):
        calls["core"] = (query, tenant_id, project, limit)
        return [
            SearchResult(
                fact_id=10,
                content="core result",
                project="alpha",
                fact_type="decision",
                confidence="C4",
                valid_from="unknown",
                valid_until=None,
                tags=[],
                created_at="unknown",
                updated_at="unknown",
                source=None,
                score=0.1,
                db_origin="core",
            )
        ]

    def fake_attach(conn, scopes=None):
        calls["attach"] = list(scopes or [])
        return ["personal"]

    def fake_detach(conn, aliases):
        calls["detach"] = list(aliases)

    def fake_search_attached_db(conn, alias, query, tenant_id="default", project=None, limit=20):
        calls["attached"] = (alias, query, tenant_id, project, limit)
        return [
            SearchResult(
                fact_id=11,
                content="attached result",
                project="alpha",
                fact_type="decision",
                confidence="C4",
                valid_from="unknown",
                valid_until=None,
                tags=[],
                created_at="unknown",
                updated_at="unknown",
                source=None,
                score=0.2,
                db_origin=alias,
            )
        ]

    monkeypatch.setattr(federation, "text_search_sync", fake_text_search_sync)
    monkeypatch.setattr(federation, "attach_federated_dbs", fake_attach)
    monkeypatch.setattr(federation, "detach_federated_dbs", fake_detach)
    monkeypatch.setattr(federation, "_search_attached_db", fake_search_attached_db)

    results = federation.federated_search_sync(
        object(),
        "cipher",
        scope="all",
        tenant_id="tenant-search",
        project="alpha",
        limit=5,
    )

    assert calls["core"] == ("cipher", "tenant-search", "alpha", 5)
    assert calls["attached"] == ("personal", "cipher", "tenant-search", "alpha", 5)
    assert calls["attach"] == ["personal"]
    assert calls["detach"] == ["personal"]
    assert [r.fact_id for r in results] == [11, 10]


@pytest.mark.asyncio
async def test_federated_search_async_forwards_tenant_id(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    async def fake_text_search(conn, query, tenant_id="default", project=None, limit=20):
        calls["core"] = (query, tenant_id, project, limit)
        return []

    async def fake_attach(conn, scopes=None):
        calls["attach"] = list(scopes or [])
        return ["cold"]

    async def fake_detach(conn, aliases):
        calls["detach"] = list(aliases)

    async def fake_search_attached_db(conn, alias, query, tenant_id="default", project=None, limit=20):
        calls["attached"] = (alias, query, tenant_id, project, limit)
        return []

    monkeypatch.setattr(federation, "text_search", fake_text_search)
    monkeypatch.setattr(federation, "attach_federated_dbs_async", fake_attach)
    monkeypatch.setattr(federation, "detach_federated_dbs_async", fake_detach)
    monkeypatch.setattr(federation, "_search_attached_db_async", fake_search_attached_db)

    await federation.federated_search(
        object(),
        "cipher",
        scope="cold",
        tenant_id="tenant-search",
        project="alpha",
        limit=5,
    )

    assert "core" not in calls
    assert calls["attached"] == ("cold", "cipher", "tenant-search", "alpha", 5)
    assert calls["attach"] == ["cold"]
    assert calls["detach"] == ["cold"]
