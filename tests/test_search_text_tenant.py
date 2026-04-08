from __future__ import annotations

from cortex.search.utils import _parse_row_sync, _row_to_result


class _FakeEncrypter:
    PREFIX = "v6_aesgcm:"

    def __init__(self) -> None:
        self.decrypt_calls: list[tuple[str, str]] = []

    def decrypt_str(self, content: str, tenant_id: str = "default") -> str:
        self.decrypt_calls.append((content, tenant_id))
        return f"decrypted:{tenant_id}:{content}"

    def decrypt_json(self, content, tenant_id: str = "default"):
        self.decrypt_calls.append((str(content), tenant_id))
        return {"tenant": tenant_id}


def test_row_to_result_uses_requested_tenant(monkeypatch) -> None:
    fake = _FakeEncrypter()
    monkeypatch.setattr(
        "cortex.crypto.get_default_encrypter",
        lambda: fake,
    )

    row = (
        1,
        "v6_aesgcm:payload",
        "alpha",
        "decision",
        "C4",
        "2026-04-04T00:00:00Z",
        None,
        '["policy"]',
        "source",
        None,
        "2026-04-04T00:00:00Z",
        "2026-04-04T00:00:01Z",
        99,
        "hash-123",
        1.5,
        0.7,
    )

    result = _row_to_result(row, tenant_id="tenant-a")

    assert result.content == "decrypted:tenant-a:v6_aesgcm:payload"
    assert fake.decrypt_calls[0] == ("v6_aesgcm:payload", "tenant-a")


def test_parse_row_sync_uses_requested_tenant(monkeypatch) -> None:
    fake = _FakeEncrypter()
    monkeypatch.setattr(
        "cortex.crypto.get_default_encrypter",
        lambda: fake,
    )

    row = (
        2,
        "v6_aesgcm:payload",
        "alpha",
        "decision",
        "C4",
        "source",
        '["policy"]',
        0.2,
    )

    result = _parse_row_sync(row, has_rank=True, tenant_id="tenant-b")

    assert result.content == "decrypted:tenant-b:v6_aesgcm:payload"
    assert fake.decrypt_calls[0] == ("v6_aesgcm:payload", "tenant-b")
