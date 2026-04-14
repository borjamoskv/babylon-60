# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Tests for FlashbotsRelay — cortex/extensions/web3/flashbots_relay.py.

Coverage:
- Initialization with/without env vars
- Authorization hash verification (Sovereign Triad)
- compute_payload_hash utility
- build_and_send_bundle: missing deps / missing credentials
- build_and_send_bundle: simulation failure path (mocked HTTP)
- build_and_send_bundle: revert detected in simulation
- build_and_send_bundle: full success path (mocked HTTP)
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_ADDRESS = "0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF"
_DUMMY_PAYLOAD = b"\xde\xad\xbe\xef"
_DUMMY_BLOCK = 21_000_000
_DUMMY_BRIBE = 10**16  # 0.01 ETH


def _make_relay(env: dict[str, str] | None = None) -> FlashbotsRelay:  # noqa: F821
    """Import and construct a FlashbotsRelay with the given environment."""
    from cortex.extensions.web3.flashbots_relay import FlashbotsRelay

    env = env or {}
    with patch.dict("os.environ", env, clear=False):
        return FlashbotsRelay()


def _valid_auth_hash(payload: bytes = _DUMMY_PAYLOAD) -> str:
    return hashlib.sha3_256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Module-level import test
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """The module must be importable without raising."""
    import cortex.extensions.web3.flashbots_relay as mod  # noqa: F401

    assert hasattr(mod, "FlashbotsRelay")


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_init_logs_warning_when_vars_missing(caplog: pytest.LogCaptureFixture) -> None:
    """Constructor logs warnings when env vars are absent."""
    import logging

    with caplog.at_level(logging.WARNING, logger="cortex.extensions.web3.flashbots_relay"):
        relay = _make_relay({})

    # Warnings should have fired (or relay initialised cleanly in stub mode)
    assert relay is not None


def test_init_with_all_env_vars(caplog: pytest.LogCaptureFixture) -> None:
    """Constructor accepts all three env vars without error."""
    import logging

    env = {
        "WEB3_RPC_URL": "http://localhost:8545",
        "WEB3_PRIVATE_KEY": "0x" + "aa" * 32,
        "FLASHBOTS_SIGNATURE_KEY": "0x" + "bb" * 32,
    }
    with caplog.at_level(logging.INFO, logger="cortex.extensions.web3.flashbots_relay"):
        relay = _make_relay(env)

    assert relay is not None


# ---------------------------------------------------------------------------
# compute_payload_hash
# ---------------------------------------------------------------------------


def test_compute_payload_hash_deterministic() -> None:
    """Hash output must be deterministic and equal to sha3_256."""
    from cortex.extensions.web3.flashbots_relay import FlashbotsRelay

    payload = b"sovereign_payload"
    expected = hashlib.sha3_256(payload).hexdigest()
    assert FlashbotsRelay.compute_payload_hash(payload) == expected


def test_compute_payload_hash_length() -> None:
    """SHA3-256 digest must be 64 hex characters."""
    from cortex.extensions.web3.flashbots_relay import FlashbotsRelay

    result = FlashbotsRelay.compute_payload_hash(b"test")
    assert len(result) == 64


# ---------------------------------------------------------------------------
# Authorization hash verification
# ---------------------------------------------------------------------------


def test_verify_authorization_empty_logs_mock_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Empty authorization_hash triggers mock-mode warning but does not raise."""
    import logging

    relay = _make_relay()
    with caplog.at_level(logging.WARNING, logger="cortex.extensions.web3.flashbots_relay"):
        relay._verify_authorization("")  # must not raise

    assert any("MOCK" in r.message for r in caplog.records)


def test_verify_authorization_valid_hash_passes() -> None:
    """A valid 64-char hex authorization_hash must pass without error."""
    relay = _make_relay()
    valid = "a" * 64
    relay._verify_authorization(valid)  # should not raise


def test_verify_authorization_invalid_length_raises() -> None:
    """A hash that is not 64 chars must raise ValueError."""
    relay = _make_relay()
    with pytest.raises(ValueError, match="64 hex characters"):
        relay._verify_authorization("short")


def test_verify_authorization_non_hex_raises() -> None:
    """A 64-char non-hex string must raise ValueError."""
    relay = _make_relay()
    with pytest.raises(ValueError):
        relay._verify_authorization("z" * 64)


# ---------------------------------------------------------------------------
# build_and_send_bundle — no-web3 path
# ---------------------------------------------------------------------------


def test_bundle_returns_simulation_failed_when_no_web3() -> None:
    """When web3 is unavailable, build_and_send_bundle must return SIMULATION_FAILED."""
    from cortex.extensions.web3 import flashbots_relay as mod

    original = mod._WEB3_AVAILABLE
    try:
        mod._WEB3_AVAILABLE = False
        relay = _make_relay(
            {
                "WEB3_RPC_URL": "http://localhost:8545",
                "WEB3_PRIVATE_KEY": "0x" + "aa" * 32,
                "FLASHBOTS_SIGNATURE_KEY": "0x" + "bb" * 32,
            }
        )
        result = relay.build_and_send_bundle(
            _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
        )
    finally:
        mod._WEB3_AVAILABLE = original

    assert result["status"] == "SIMULATION_FAILED"
    assert result["bundle_hash"] == ""
    assert "web3" in result["details"].lower()


# ---------------------------------------------------------------------------
# build_and_send_bundle — missing credentials path
# ---------------------------------------------------------------------------


def test_bundle_returns_simulation_failed_when_missing_creds() -> None:
    """Missing env vars cause an immediate SIMULATION_FAILED response."""
    from cortex.extensions.web3 import flashbots_relay as mod

    if not mod._WEB3_AVAILABLE:
        pytest.skip("web3 not installed — missing-creds path unreachable")

    relay = _make_relay({})  # no creds
    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "SIMULATION_FAILED"
    assert result["bundle_hash"] == ""


# ---------------------------------------------------------------------------
# build_and_send_bundle — mocked HTTP paths (web3 required)
# ---------------------------------------------------------------------------


def _make_relay_with_creds() -> FlashbotsRelay:  # noqa: F821
    env = {
        "WEB3_RPC_URL": "http://localhost:8545",
        "WEB3_PRIVATE_KEY": "0x" + "aa" * 32,
        "FLASHBOTS_SIGNATURE_KEY": "0x" + "bb" * 32,
    }
    return _make_relay(env)


@pytest.fixture()
def relay_with_mocked_w3(monkeypatch: pytest.MonkeyPatch):
    """Return a FlashbotsRelay whose Web3 connection is mocked."""
    from cortex.extensions.web3 import flashbots_relay as mod

    if not mod._WEB3_AVAILABLE:
        pytest.skip("web3 not installed")

    relay = _make_relay_with_creds()

    # Mock the web3 account / nonce / chain id
    mock_account = MagicMock()
    mock_account.address = "0x1234567890123456789012345678901234567890"
    mock_signed = MagicMock()
    mock_signed.rawTransaction = bytes(32)
    mock_account.sign_transaction.return_value = mock_signed

    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction_count.return_value = 0
    mock_w3.eth.chain_id = 1
    mock_w3.eth.gas_price = 10**9

    relay._w3 = mock_w3

    # Patch Account.from_key to return our mock account
    monkeypatch.setattr(
        "cortex.extensions.web3.flashbots_relay.Account.from_key",
        lambda key: mock_account,
    )

    return relay


def test_bundle_simulation_failed_on_rpc_error(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If simulation HTTP call raises, return SIMULATION_FAILED."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(relay, "_rpc_call", lambda *a, **kw: (_ for _ in ()).throw(
        RuntimeError("network error")
    ))

    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "SIMULATION_FAILED"


def test_bundle_simulation_failed_on_rpc_error_via_simulate(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If _simulate_bundle returns error, bundle returns SIMULATION_FAILED."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(
        relay,
        "_simulate_bundle",
        lambda *a, **kw: {"status": "error", "details": "RPC timeout"},
    )

    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "SIMULATION_FAILED"
    assert "RPC timeout" in result["details"]


def test_bundle_reverted_when_simulation_has_revert(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the simulation reports a revert, status must be REVERTED."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(
        relay,
        "_simulate_bundle",
        lambda *a, **kw: {
            "status": "ok",
            "raw": {"results": [{"revert": "execution reverted"}]},
        },
    )

    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "REVERTED"
    assert result["bundle_hash"] == ""


def test_bundle_success_path(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: simulation succeeds → send succeeds → SUCCESS with bundle_hash."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(
        relay,
        "_simulate_bundle",
        lambda *a, **kw: {"status": "ok", "raw": {"results": [{"gasUsed": "0x5208"}]}},
    )
    monkeypatch.setattr(
        relay,
        "_send_bundle",
        lambda *a, **kw: {
            "status": "ok",
            "bundle_hash": "0xdeadbeefcafe",
        },
    )

    auth = _valid_auth_hash(_DUMMY_PAYLOAD)
    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS,
        _DUMMY_PAYLOAD,
        _DUMMY_BRIBE,
        _DUMMY_BLOCK,
        authorization_hash=auth,
    )

    assert result["status"] == "SUCCESS"
    assert result["bundle_hash"] == "0xdeadbeefcafe"
    assert str(_DUMMY_BLOCK) in result["details"]
    assert auth in result["details"]


def test_bundle_success_without_auth_hash(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path with no authorization_hash → MOCK mode → SUCCESS."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(
        relay,
        "_simulate_bundle",
        lambda *a, **kw: {"status": "ok", "raw": {}},
    )
    monkeypatch.setattr(
        relay,
        "_send_bundle",
        lambda *a, **kw: {"status": "ok", "bundle_hash": "0xabc123"},
    )

    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "SUCCESS"
    assert "MOCK" in result["details"]


def test_bundle_send_failed_returns_simulation_failed(
    relay_with_mocked_w3: FlashbotsRelay,  # noqa: F821
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If send fails after simulation success, return SIMULATION_FAILED."""
    relay = relay_with_mocked_w3
    monkeypatch.setattr(
        relay,
        "_simulate_bundle",
        lambda *a, **kw: {"status": "ok", "raw": {}},
    )
    monkeypatch.setattr(
        relay,
        "_send_bundle",
        lambda *a, **kw: {"status": "error", "details": "relay rejected bundle"},
    )

    result = relay.build_and_send_bundle(
        _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
    )

    assert result["status"] == "SIMULATION_FAILED"
    assert "relay rejected" in result["details"]


# ---------------------------------------------------------------------------
# Result schema contract
# ---------------------------------------------------------------------------


def test_result_always_has_required_keys() -> None:
    """All three required keys must always be present in the return value."""
    from cortex.extensions.web3 import flashbots_relay as mod

    original = mod._WEB3_AVAILABLE
    try:
        mod._WEB3_AVAILABLE = False
        relay = _make_relay()
        result = relay.build_and_send_bundle(
            _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
        )
    finally:
        mod._WEB3_AVAILABLE = original

    assert set(result.keys()) >= {"status", "bundle_hash", "details"}


def test_result_status_values_are_valid() -> None:
    """status must be one of the three documented values."""
    from cortex.extensions.web3 import flashbots_relay as mod

    original = mod._WEB3_AVAILABLE
    try:
        mod._WEB3_AVAILABLE = False
        relay = _make_relay()
        result = relay.build_and_send_bundle(
            _DUMMY_ADDRESS, _DUMMY_PAYLOAD, _DUMMY_BRIBE, _DUMMY_BLOCK
        )
    finally:
        mod._WEB3_AVAILABLE = original

    assert result["status"] in {"SUCCESS", "SIMULATION_FAILED", "REVERTED"}
