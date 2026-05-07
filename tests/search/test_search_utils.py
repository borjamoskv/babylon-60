from __future__ import annotations

import pytest

from cortex.search import utils as search_utils


class FakeEncrypter:
    def decrypt_str(self, value: str, *, tenant_id: str) -> str:
        if value.endswith("bad"):
            raise ValueError("bad ciphertext")
        return f"decrypted:{tenant_id}:{value}"

    def decrypt_json(self, value: str, *, tenant_id: str) -> dict:
        if value.endswith("bad"):
            raise ValueError("bad metadata")
        return {"tenant": tenant_id, "raw": value}


def test_sanitize_fts_query_quotes_each_token_and_removes_apostrophes() -> None:
    assert search_utils._sanitize_fts_query("alpha's OR beta") == '"alphas" "OR" "beta"'
    assert search_utils._sanitize_fts_query("") == '""'
    assert search_utils._sanitize_fts_query("   ") == '""'


def test_decrypt_row_content_handles_plain_encrypted_and_failed_values() -> None:
    enc = FakeEncrypter()

    assert search_utils._decrypt_row_content("plain", "tenant-a", enc) == "plain"
    assert (
        search_utils._decrypt_row_content(f"{search_utils.V6_PREFIX}cipher", "tenant-a", enc)
        == f"decrypted:tenant-a:{search_utils.V6_PREFIX}cipher"
    )
    assert (
        search_utils._decrypt_row_content(f"{search_utils.V6_PREFIX}bad", "tenant-a", enc)
        == f"{search_utils.V6_PREFIX}bad"
    )
    assert search_utils._decrypt_row_content(None, "tenant-a", enc) == ""


def test_parse_row_meta_handles_empty_json_encrypted_and_invalid_values() -> None:
    enc = FakeEncrypter()

    assert search_utils._parse_row_meta(None, "tenant-a", enc) == {}
    assert search_utils._parse_row_meta('{"confidence":"C3"}', "tenant-a", enc) == {
        "confidence": "C3"
    }
    assert search_utils._parse_row_meta("{invalid", "tenant-a", enc) == {}
    assert search_utils._parse_row_meta(f"{search_utils.V6_PREFIX}meta", "tenant-a", enc) == {
        "tenant": "tenant-a",
        "raw": f"{search_utils.V6_PREFIX}meta",
    }
    assert search_utils._parse_row_meta(f"{search_utils.V6_PREFIX}bad", "tenant-a", enc) == {}


def test_row_to_result_maps_tags_metadata_score_and_consensus(monkeypatch: pytest.MonkeyPatch) -> None:
    import cortex.crypto

    monkeypatch.setattr(cortex.crypto, "get_default_encrypter", lambda: FakeEncrypter())
    row = (
        7,
        "content",
        "project",
        "knowledge",
        "C3",
        "2026-01-01",
        None,
        '["tag"]',
        "agent:test",
        '{"extra":true}',
        "created",
        "updated",
        42,
        "hash",
        2.0,
        "rank",
        0.0,
    )

    result = search_utils._row_to_result(row, is_fts=True)

    assert result.fact_id == 7
    assert result.content == "content"
    assert result.tags == ["tag"]
    assert result.meta == {"extra": True}
    assert result.confidence == "verified"
    assert result.score == 0.5
    assert result.tx_id == 42
    assert result.hash == "hash"


def test_parse_row_sync_handles_bad_tags_and_rank(monkeypatch: pytest.MonkeyPatch) -> None:
    import cortex.crypto

    monkeypatch.setattr(cortex.crypto, "get_default_encrypter", lambda: FakeEncrypter())
    row = (1, "content", "project", "knowledge", "C3", "source", "{bad", 0.0)

    result = search_utils._parse_row_sync(row, has_rank=True)

    assert result.fact_id == 1
    assert result.tags == []
    assert result.score == 0.5
