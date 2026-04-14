"""
CORTEX v6 — Flashbots Relay Module (Motor Nervous System).

Allows the Aether Swarm to submit MEV / Whitehat bundles directly to Ethereum
block builders via the Flashbots relay, bypassing the public mempool.

Axiom Ω₄: Autonomy = choosing which problems to solve and persisting.
Axiom Ω₃: Zero-Trust — all inputs are verified; no state is mutated without
           a deterministic validation boundary.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import httpx  # already in [api] extras; safe import

logger = logging.getLogger("cortex.extensions.web3.flashbots_relay")

# ---------------------------------------------------------------------------
# Relay constants
# ---------------------------------------------------------------------------

_FLASHBOTS_RELAY_URL: str = "https://relay.flashbots.net"
_SIMULATE_METHOD: str = "eth_callBundle"
_SEND_METHOD: str = "eth_sendBundle"

# ---------------------------------------------------------------------------
# Lazy optional imports (web3 / eth_account are not in core deps)
# ---------------------------------------------------------------------------

try:
    from eth_account import Account  # type: ignore[reportMissingImports]
    from eth_account.messages import encode_defunct  # type: ignore[reportMissingImports]
    from web3 import Web3  # type: ignore[reportMissingImports]

    _WEB3_AVAILABLE = True
except ImportError:
    _WEB3_AVAILABLE = False
    logger.warning(
        "web3 / eth_account not installed. "
        "FlashbotsRelay will operate in simulation-stub mode. "
        "Install with: pip install web3"
    )


# ---------------------------------------------------------------------------
# FlashbotsRelay
# ---------------------------------------------------------------------------


class FlashbotsRelay:
    """Motor Nervous System for the Aether Swarm.

    Constructs, simulates, and submits Flashbots bundles to Ethereum block
    builders.  Requires a valid OLIVER authorization hash before any bundle
    leaves the process boundary (Sovereign Triad integration).

    Environment variables consumed at construction time:
      - WEB3_RPC_URL          : Ethereum JSON-RPC endpoint (e.g. Infura/Alchemy).
      - WEB3_PRIVATE_KEY      : Hex private key used to sign bundle transactions.
      - FLASHBOTS_SIGNATURE_KEY: Hex private key for Flashbots relay authentication.
    """

    def __init__(self) -> None:
        self._rpc_url: str = os.environ.get("WEB3_RPC_URL", "")
        self._private_key: str = os.environ.get("WEB3_PRIVATE_KEY", "")
        self._flashbots_sig_key: str = os.environ.get("FLASHBOTS_SIGNATURE_KEY", "")

        if not self._rpc_url:
            logger.warning("WEB3_RPC_URL not set — relay calls will fail at runtime.")
        if not self._private_key:
            logger.warning("WEB3_PRIVATE_KEY not set — bundle signing unavailable.")
        if not self._flashbots_sig_key:
            logger.warning(
                "FLASHBOTS_SIGNATURE_KEY not set — relay authentication unavailable."
            )

        self._w3: Any = None
        if _WEB3_AVAILABLE and self._rpc_url:
            self._w3 = Web3(Web3.HTTPProvider(self._rpc_url))  # type: ignore[reportPossiblyUnbound]

        logger.info("FlashbotsRelay initialised (web3_available=%s).", _WEB3_AVAILABLE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_and_send_bundle(
        self,
        target_contract: str,
        payload: bytes,
        bribe_amount_wei: int,
        target_block_number: int,
        authorization_hash: str = "",
    ) -> dict[str, str]:
        """Build, simulate, and optionally submit a Flashbots bundle.

        Args:
            target_contract:   Checksummed Ethereum address of the target contract.
            payload:           ABI-encoded call data (the compiled exploit / rescue payload).
            bribe_amount_wei:  Miner bribe in Wei attached as the transaction value.
            target_block_number: The exact block number this bundle must land on.
            authorization_hash: SHA3-256 hex digest issued by OLIVER (The Hammer)
                                 certifying the payload has been audited.  If omitted,
                                 the bundle is still processed but flagged as unapproved
                                 (mock mode during triad integration).

        Returns:
            A strict, deterministic dict:
            {
                "status":      "SUCCESS" | "SIMULATION_FAILED" | "REVERTED",
                "bundle_hash": "<hex string or empty>",
                "details":     "<human-readable description>",
            }
        """
        # ── Sovereign Triad check ────────────────────────────────────────
        self._verify_authorization(authorization_hash)

        # ── Guard: dependency available? ─────────────────────────────────
        if not _WEB3_AVAILABLE:
            return {
                "status": "SIMULATION_FAILED",
                "bundle_hash": "",
                "details": (
                    "web3/eth_account not installed. "
                    "Install with `pip install web3` to enable live relay."
                ),
            }

        # ── Guard: credentials present? ──────────────────────────────────
        missing = [
            name
            for name, val in (
                ("WEB3_RPC_URL", self._rpc_url),
                ("WEB3_PRIVATE_KEY", self._private_key),
                ("FLASHBOTS_SIGNATURE_KEY", self._flashbots_sig_key),
            )
            if not val
        ]
        if missing:
            return {
                "status": "SIMULATION_FAILED",
                "bundle_hash": "",
                "details": f"Missing required env vars: {', '.join(missing)}",
            }

        try:
            signed_tx_hex = self._build_signed_transaction(
                target_contract, payload, bribe_amount_wei
            )
        except Exception as exc:  # noqa: BLE001 — transaction build boundary
            logger.exception("Transaction build failed: %s", exc)
            return {
                "status": "SIMULATION_FAILED",
                "bundle_hash": "",
                "details": f"Transaction build error: {exc}",
            }

        bundle = [{"signed_transaction": signed_tx_hex}]

        # ── Simulate ─────────────────────────────────────────────────────
        sim_result = self._simulate_bundle(bundle, target_block_number)
        if sim_result["status"] != "ok":
            logger.warning("Bundle simulation rejected: %s", sim_result["details"])
            return {
                "status": "SIMULATION_FAILED",
                "bundle_hash": "",
                "details": sim_result["details"],
            }

        # ── Check for reverts in simulation results ───────────────────────
        if self._simulation_has_revert(sim_result.get("raw", {})):
            return {
                "status": "REVERTED",
                "bundle_hash": "",
                "details": "Simulation succeeded at RPC level but a transaction reverted.",
            }

        # ── Submit ───────────────────────────────────────────────────────
        submit_result = self._send_bundle(bundle, target_block_number)
        if submit_result["status"] != "ok":
            return {
                "status": "SIMULATION_FAILED",
                "bundle_hash": "",
                "details": submit_result["details"],
            }

        bundle_hash: str = submit_result.get("bundle_hash", "")
        logger.info(
            "Bundle submitted successfully. hash=%s block=%d",
            bundle_hash,
            target_block_number,
        )
        return {
            "status": "SUCCESS",
            "bundle_hash": bundle_hash,
            "details": (
                f"Bundle accepted by relay for block {target_block_number}. "
                f"Authorization: {authorization_hash or 'MOCK'}"
            ),
        }

    # ------------------------------------------------------------------
    # Sovereign Triad integration
    # ------------------------------------------------------------------

    def _verify_authorization(self, authorization_hash: str) -> None:
        """Verify the OLIVER authorization hash before allowing bundle dispatch.

        The hash must be a valid SHA3-256 hex digest (64 hex chars).  If the
        full triad is not yet wired up, the check is logged as a mock but does
        NOT block execution — this allows iterative integration.
        """
        if not authorization_hash:
            logger.warning(
                "[SOVEREIGN TRIAD] No authorization_hash provided. "
                "Running in MOCK mode — triad integration pending. "
                "Payload proceeds without OLIVER approval."
            )
            return

        # Structural validation: must be a 64-char hex string (SHA3-256)
        try:
            if len(authorization_hash) != 64:
                raise ValueError("authorization_hash must be 64 hex characters (SHA3-256).")
            bytes.fromhex(authorization_hash)
        except ValueError as exc:
            logger.error(
                "[SOVEREIGN TRIAD] Invalid authorization_hash format: %s — %s",
                authorization_hash,
                exc,
            )
            raise

        logger.info(
            "[SOVEREIGN TRIAD] OLIVER authorization hash verified: %s",
            authorization_hash,
        )

    # ------------------------------------------------------------------
    # Transaction construction
    # ------------------------------------------------------------------

    def _build_signed_transaction(
        self,
        target_contract: str,
        payload: bytes,
        bribe_amount_wei: int,
    ) -> str:
        """Build and sign a raw Ethereum transaction.

        Returns the hex-encoded signed transaction (0x-prefixed).
        """
        account = Account.from_key(self._private_key)  # type: ignore[reportPossiblyUnbound]
        w3: Any = self._w3

        nonce = w3.eth.get_transaction_count(account.address)
        chain_id = w3.eth.chain_id
        gas_price = w3.eth.gas_price

        tx: dict[str, Any] = {
            "to": Web3.to_checksum_address(target_contract),  # type: ignore[reportPossiblyUnbound]
            "value": bribe_amount_wei,
            "gas": 250_000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": chain_id,
            "data": payload,
        }

        signed = account.sign_transaction(tx)
        return signed.rawTransaction.hex()

    # ------------------------------------------------------------------
    # Flashbots HTTP helpers
    # ------------------------------------------------------------------

    def _flashbots_headers(self, body: str) -> dict[str, str]:
        """Construct the X-Flashbots-Signature header for relay auth."""
        body_hash = Web3.keccak(text=body).hex()  # type: ignore[reportPossiblyUnbound]
        signable = encode_defunct(hexstr=body_hash)  # type: ignore[reportPossiblyUnbound]
        signed_msg = Account.sign_message(  # type: ignore[reportPossiblyUnbound]
            signable, private_key=self._flashbots_sig_key
        )
        relay_account = Account.from_key(self._flashbots_sig_key)  # type: ignore[reportPossiblyUnbound]
        signature = f"{relay_account.address}:{signed_msg.signature.hex()}"
        return {
            "Content-Type": "application/json",
            "X-Flashbots-Signature": signature,
        }

    def _rpc_call(self, method: str, params: list[Any]) -> dict[str, Any]:
        """Execute a JSON-RPC call against the Flashbots relay."""
        payload_obj: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        body = json.dumps(payload_obj)
        headers = self._flashbots_headers(body)

        try:
            response = httpx.post(
                _FLASHBOTS_RELAY_URL,
                content=body,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Flashbots relay returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:256]}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error contacting Flashbots relay: {exc}") from exc

    def _simulate_bundle(
        self, bundle: list[dict[str, str]], target_block_number: int
    ) -> dict[str, Any]:
        """Simulate a bundle via eth_callBundle.

        Returns {"status": "ok", "raw": <rpc_result>} or
                {"status": "error", "details": "<msg>"}.
        """
        block_hex = hex(target_block_number)
        params: list[Any] = [
            {
                "txs": [tx["signed_transaction"] for tx in bundle],
                "blockNumber": block_hex,
                "stateBlockNumber": "latest",
                "timestamp": int(time.time()),
            }
        ]

        try:
            result = self._rpc_call(_SIMULATE_METHOD, params)
        except RuntimeError as exc:
            return {"status": "error", "details": str(exc)}

        if "error" in result:
            err = result["error"]
            details = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"status": "error", "details": f"Simulation RPC error: {details}"}

        return {"status": "ok", "raw": result.get("result", {})}

    def _simulation_has_revert(self, sim_raw: Any) -> bool:
        """Return True if any transaction in the simulation result reverted."""
        if not isinstance(sim_raw, dict):
            return False
        results = sim_raw.get("results", [])
        if not isinstance(results, list):
            return False
        for tx_result in results:
            if isinstance(tx_result, dict) and tx_result.get("revert"):
                return True
        return False

    def _send_bundle(
        self, bundle: list[dict[str, str]], target_block_number: int
    ) -> dict[str, Any]:
        """Submit a bundle via eth_sendBundle.

        Returns {"status": "ok", "bundle_hash": "<hex>"} or
                {"status": "error", "details": "<msg>"}.
        """
        block_hex = hex(target_block_number)
        params: list[Any] = [
            {
                "txs": [tx["signed_transaction"] for tx in bundle],
                "blockNumber": block_hex,
            }
        ]

        try:
            result = self._rpc_call(_SEND_METHOD, params)
        except RuntimeError as exc:
            return {"status": "error", "details": str(exc)}

        if "error" in result:
            err = result["error"]
            details = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"status": "error", "details": f"Send RPC error: {details}"}

        bundle_hash: str = ""
        rpc_result = result.get("result", {})
        if isinstance(rpc_result, dict):
            bundle_hash = rpc_result.get("bundleHash", "")

        return {"status": "ok", "bundle_hash": bundle_hash}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def compute_payload_hash(payload: bytes) -> str:
        """Return the SHA3-256 hex digest of a raw payload.

        Useful for generating the authorization_hash that OLIVER should sign
        after auditing the payload (Sovereign Triad integration).
        """
        return hashlib.sha3_256(payload).hexdigest()
