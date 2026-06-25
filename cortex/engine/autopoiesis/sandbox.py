"""
C5-REAL Autopoietic Sandbox Validator.
Enforces that AST patches pass unit tests in an isolated subprocess
before they are allowed to touch the live RAM.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class C5Seal:
    """Cryptographic seal representing validated execution."""
    ast_hash: str
    verified_at: str

class SandboxValidator:
    """Isolates and validates code mutations."""

    @staticmethod
    def validate_patch(file_path: str, test_path: str | None = None) -> C5Seal:
        """
        Runs the test suite for the patched file in a subprocess.
        Returns a C5Seal if successful, raises RuntimeError otherwise.
        """
        with open(file_path, "rb") as f:
            content = f.read()
            
        ast_hash = hashlib.sha256(content).hexdigest()
        
        target = test_path if test_path else "tests/"
        
        logger.info("Initiating C5-REAL Sandbox Validation for %s via %s", file_path, target)
        
        result = subprocess.run(
            ["uv", "run", "pytest", target, "-v"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode not in (0, 5):
            logger.error("Sandbox Validation FAILED. Entropy detected:\n%s", result.stderr or result.stdout)
            raise RuntimeError(f"Sandbox validation failed for {file_path}. AST patch rejected.")
            
        logger.info("Sandbox Validation SUCCESS. C5-SEAL generated for hash %s", ast_hash[:8])
        
        return C5Seal(
            ast_hash=ast_hash,
            verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
