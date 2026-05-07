from __future__ import annotations

import datetime
import hashlib

from cortex.utils.canonical import (
    canonical_json,
    compute_fact_hash,
    compute_tx_hash,
    compute_tx_hash_v1,
    now_iso,
)


def test_canonical_json_sorts_keys_removes_whitespace_and_escapes_unicode() -> None:
    payload = {"z": 2, "a": "cafe", "nested": {"b": 1, "a": "nino"}}

    assert canonical_json(payload) == '{"a":"cafe","nested":{"a":"nino","b":1},"z":2}'


def test_canonical_json_stringifies_unknown_objects() -> None:
    value = datetime.date(2026, 5, 6)

    assert canonical_json({"date": value}) == '{"date":"2026-05-06"}'


def test_compute_tx_hash_uses_null_byte_separated_v2_input_without_tenant() -> None:
    expected = hashlib.sha256(b"prev\x00proj\x00store\x00{}\x002026").hexdigest()

    assert compute_tx_hash("prev", "proj", "store", "{}", "2026") == expected


def test_compute_tx_hash_binds_tenant_when_supplied() -> None:
    expected = hashlib.sha256(b"tenant-a\x00prev\x00proj\x00store\x00{}\x002026").hexdigest()

    assert (
        compute_tx_hash("prev", "proj", "store", "{}", "2026", tenant_id="tenant-a")
        == expected
    )
    assert compute_tx_hash("prev", "proj", "store", "{}", "2026") != expected


def test_compute_tx_hash_v1_uses_legacy_colon_delimiter() -> None:
    expected = hashlib.sha256(b"prev:proj:store:{}:2026").hexdigest()

    assert compute_tx_hash_v1("prev", "proj", "store", "{}", "2026") == expected


def test_compute_fact_hash_hashes_content_bytes() -> None:
    assert compute_fact_hash("fact") == hashlib.sha256(b"fact").hexdigest()


def test_now_iso_returns_timezone_aware_utc_timestamp() -> None:
    parsed = datetime.datetime.fromisoformat(now_iso())

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == datetime.timedelta(0)
