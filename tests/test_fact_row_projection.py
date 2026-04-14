from __future__ import annotations

import json

from cortex.engine.models import row_to_fact


class _StubEncrypter:
    def decrypt_str(self, value: str, tenant_id: str = "default") -> str:
        return value

    def decrypt_json(self, value: str, tenant_id: str = "default"):
        return json.loads(value)


def test_row_to_fact_preserves_tx_id_for_full_facts_schema_layout(monkeypatch) -> None:
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: _StubEncrypter())

    row = (
        1,
        "tenant-a",
        "proj",
        "plaintext-content",
        "knowledge",
        "{}",
        "hash-1",
        77,
        "2026-01-01T00:00:00Z",
        None,
        "agent:test",
        "verified",
        5,
        1.0,
        "2026-01-01T00:00:00Z",
        "2026-01-01T00:00:01Z",
        0,
        0,
        None,
        None,
        "ACTIVE",
        "HOT",
        1.0,
        "general",
        "pending",
        None,
        12,
        "derived_from",
        0.8,
        '["tag-a"]',
    )

    fact = row_to_fact(row)

    assert fact.tx_id == 77
    assert fact.parent_id == 12
    assert fact.parent_decision_id == 12
    assert fact.tags == ["tag-a"]
