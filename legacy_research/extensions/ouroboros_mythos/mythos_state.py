# [C5-REAL] Exergy-Maximized
"""
Mythos State Module.
Maintains the self-model and enforces strict integer invariants (BABYLON-60).
"""

import hashlib
import logging
import struct

logger = logging.getLogger(__name__)

class MythosState:
    """
    Sovereign State representation.
    Enforces the i32/u32 bounds, explicit endianness, and deterministic serialization.
    """

    def __init__(self):
        self.state_hash: int = 0
        self.cycle_count: int = 0
        self.identity_anchor = b"C5-REAL-MYTHOS-1"

    def commit_state_hash(self, action_data: dict):
        """
        Computes a new state hash using strict struct serialization and SHA-256.
        """
        # Deterministic serialization (Extracting known keys, fallback to static bytes if missing)
        action_bytes = action_data.get("action_type", b"unknown_action")
        
        # Hash deterministic bytes instead of Python dict strings
        sha = hashlib.sha256()
        sha.update(action_bytes)
        sha.update(self.identity_anchor)
        
        # Extract first 4 bytes as u32 (Little Endian explicit)
        raw_hash = struct.unpack('<I', sha.digest()[:4])[0]
        
        # Mix with previous state
        mixed = (self.state_hash ^ raw_hash) & 0xFFFFFFFF
        
        # Advance cycle deterministically
        self.cycle_count = (self.cycle_count + 1) & 0xFFFFFFFF
        
        self.state_hash = mixed
        logger.info(f"[C5-REAL] State Mutated. Cycle: {self.cycle_count}, Hash: {hex(self.state_hash)}")

    def get_self_model(self) -> dict:
        """
        Returns the current state representation.
        """
        return {
            "identity": self.identity_anchor,
            "cycle": self.cycle_count,
            "hash": self.state_hash
        }
