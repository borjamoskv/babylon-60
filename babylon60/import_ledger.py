# [C5-REAL] Exergy-Maximized
"""
Cryptographically verifiable, append-only ledger for import resolutions.
Tracks all namespace resolution events to maintain absolute forensic traceability.
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

class ImportResolutionLedger:
    """
    Forensic ledger tracking import resolutions.
    Ensures that shadow redirects, would-breaks, and bypassed resolutions are fully auditable.
    """
    def __init__(self, filepath: Optional[str] = None):
        if filepath:
            self.filepath = Path(filepath)
        else:
            db_dir = Path(os.environ.get("CORTEX_DB_PATH", "~/.cortex")).expanduser()
            if db_dir.suffix:
                db_dir = db_dir.parent
            self.filepath = db_dir / "import_ledger.jsonl"

        self.session_id = os.urandom(16).hex()
        
        # Generate transient keypair for session-level integrity
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
        # Public key in PEM format to write in metadata
        self.public_key_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        self.last_hash = "GENESIS"
        self._entries_written = 0
        self._session_active = False

    def _get_last_hash_from_file(self) -> str:
        """Finds the last hash in the existing ledger file to maintain chain continuity."""
        if not self.filepath.exists() or self.filepath.stat().st_size == 0:
            return "GENESIS"
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line
                if last_line:
                    data = json.loads(last_line)
                    return data.get("entry_hash", "GENESIS")
        except Exception:
            pass
        return "GENESIS"

    def start_session(self) -> None:
        """Writes the session start marker and hooks into the existing hash chain."""
        if self._session_active:
            return

        # Ensure parent directories exist
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Anchor current run to historical ledger state
        self.last_hash = self._get_last_hash_from_file()
        
        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        
        # Calculate entry hash for session start
        payload = f"{self.session_id}|SESSION_START|{self.public_key_pem}|{self.last_hash}"
        entry_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        start_entry = {
            "type": "SESSION_START",
            "session_id": self.session_id,
            "timestamp": timestamp,
            "public_key_pem": self.public_key_pem,
            "prev_hash": self.last_hash,
            "entry_hash": entry_hash
        }

        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(start_entry) + "\n")

        self.last_hash = entry_hash
        self._session_active = True
        self._entries_written = 1

    def log_resolution(
        self,
        importer: str,
        imported: str,
        resolution_type: str,
        resolving_path: str
    ) -> str:
        """Logs a single import resolution and returns its entry hash."""
        if not self._session_active:
            self.start_session()

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        
        # Standardized normalization payload
        payload = f"{timestamp}|{importer}|{imported}|{resolution_type}|{resolving_path}|{self.last_hash}"
        entry_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        entry = {
            "type": "RESOLUTION",
            "session_id": self.session_id,
            "timestamp": timestamp,
            "importer": importer,
            "imported": imported,
            "resolution_type": resolution_type,
            "resolving_path": resolving_path,
            "prev_hash": self.last_hash,
            "entry_hash": entry_hash
        }

        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        self.last_hash = entry_hash
        self._entries_written += 1
        return entry_hash

    def end_session(self) -> str:
        """Finalizes the session and signs the state vector to prevent dynamic truncation."""
        if not self._session_active:
            return self.last_hash

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        
        # Sign the current last_hash representing the entire session's accumulator
        signature = self._private_key.sign(self.last_hash.encode("utf-8")).hex()
        
        payload = f"{self.session_id}|SESSION_END|{signature}|{self.last_hash}"
        entry_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        end_entry = {
            "type": "SESSION_END",
            "session_id": self.session_id,
            "timestamp": timestamp,
            "signature": signature,
            "prev_hash": self.last_hash,
            "entry_hash": entry_hash
        }

        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(end_entry) + "\n")

        self.last_hash = entry_hash
        self._session_active = False
        return entry_hash

    @classmethod
    def verify_ledger(cls, filepath: str) -> Dict[str, Any]:
        """
        Verifies the cryptographic integrity of an import resolution ledger.
        Ensures all hash chains link correctly and session signatures are valid.
        """
        path = Path(filepath)
        if not path.exists():
            return {
                "status": "failed",
                "reason": "ledger_file_not_found"
            }

        # Keep track of active session states
        session_keys: Dict[str, ed25519.Ed25519PublicKey] = {}
        expected_prev_hash = "GENESIS"
        line_num = 0

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line_num += 1
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    entry_type = entry.get("type")
                    session_id = entry.get("session_id")
                    prev_hash = entry.get("prev_hash")
                    entry_hash = entry.get("entry_hash")

                    # Verify overall chain linking
                    if prev_hash != expected_prev_hash:
                        return {
                            "status": "failed",
                            "line": line_num,
                            "reason": f"chain_broken (expected {expected_prev_hash}, got {prev_hash})"
                        }

                    if entry_type == "SESSION_START":
                        pub_pem = entry.get("public_key_pem")
                        if not pub_pem:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "missing_public_key"
                            }
                        
                        # Load session public key
                        pub_key = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
                        if not isinstance(pub_key, ed25519.Ed25519PublicKey):
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "invalid_public_key_type"
                            }
                        session_keys[session_id] = pub_key
                        
                        # Reconstruct hash
                        expected_payload = f"{session_id}|SESSION_START|{pub_pem}|{prev_hash}"
                        recomputed_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
                        if recomputed_hash != entry_hash:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "session_start_hash_mismatch"
                            }

                    elif entry_type == "RESOLUTION":
                        timestamp = entry.get("timestamp")
                        importer = entry.get("importer")
                        imported = entry.get("imported")
                        resolution_type = entry.get("resolution_type")
                        resolving_path = entry.get("resolving_path")
                        
                        # Reconstruct hash
                        expected_payload = f"{timestamp}|{importer}|{imported}|{resolution_type}|{resolving_path}|{prev_hash}"
                        recomputed_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
                        if recomputed_hash != entry_hash:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "resolution_hash_mismatch"
                            }

                    elif entry_type == "SESSION_END":
                        signature = entry.get("signature")
                        if not signature:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "missing_signature"
                            }
                        
                        pub_key = session_keys.get(session_id)
                        if not pub_key:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": f"unknown_session_id: {session_id}"
                            }

                        # Verify signature of the state accumulator (which is prev_hash here)
                        try:
                            pub_key.verify(bytes.fromhex(signature), prev_hash.encode("utf-8"))
                        except InvalidSignature:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "invalid_session_signature"
                            }

                        # Reconstruct hash
                        expected_payload = f"{session_id}|SESSION_END|{signature}|{prev_hash}"
                        recomputed_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
                        if recomputed_hash != entry_hash:
                            return {
                                "status": "failed",
                                "line": line_num,
                                "reason": "session_end_hash_mismatch"
                            }

                    else:
                        return {
                            "status": "failed",
                            "line": line_num,
                            "reason": f"unknown_entry_type: {entry_type}"
                        }

                    # Progress expected chain hash
                    expected_prev_hash = entry_hash

        except Exception as e:
            return {
                "status": "failed",
                "reason": f"parsing_error: {e}"
            }

        return {
            "status": "verified",
            "total_lines_read": line_num,
            "final_hash": expected_prev_hash
        }
