# [C5-REAL] Exergy-Maximized
"""
Forensic Import Resolution Ledger for BABYLON-60.
Logs module resolution events at import-time with process-safe locking (fcntl)
to support concurrent testing (pytest-xdist) and runtime traceability.
"""

import os
import sys
import json
import time
import uuid
import fcntl
from pathlib import Path
from datetime import datetime, timezone

class ImportResolutionLedger:
    """
    Process-safe ledger for recording import resolutions during coexistence.
    Ensures that multiple concurrent Python processes can write to the same log
    without interleaved lines or file corruption.
    """
    def __init__(self, filepath: str = None):
        if filepath:
            self.filepath = Path(filepath)
        else:
            # Default to project root
            project_root = Path(__file__).resolve().parent.parent
            self.filepath = project_root / "import_resolution_ledger.jsonl"
            
        self.session_id = str(uuid.uuid4())
        self.pid = os.getpid()

    def _write_entry(self, entry: dict):
        """Appends an entry to the JSONL ledger file using process-exclusive locking."""
        # Ensure parent directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Format entry as string with newline
        line = json.dumps(entry) + "\n"
        
        # Open in append mode and acquire an exclusive lock
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                try:
                    # Block until lock is acquired
                    fcntl.flock(f, fcntl.LOCK_EX)
                    f.write(line)
                    f.flush()
                    # Flush OS buffers
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except IOError as e:
            # Fallback to stderr if logging fails to avoid breaking application import logic
            sys.stderr.write(f"\n[LEDGER ERROR] Failed to write import ledger: {e}\n")
            sys.stderr.flush()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def start_session(self):
        """Logs the start of a tracing session with environment metadata."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "SESSION_START",
            "session_id": self.session_id,
            "pid": self.pid,
            "metadata": {
                "python_version": sys.version,
                "os": sys.platform,
                "cwd": os.getcwd()
            }
        }
        self._write_entry(entry)

    def log_resolution(self, caller: str, source: str, resolution_type: str, target: str):
        """Logs a single import resolution decision."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "RESOLUTION",
            "session_id": self.session_id,
            "pid": self.pid,
            "caller": caller,
            "source": source,
            "type": resolution_type,
            "target": target
        }
        self._write_entry(entry)

    def end_session(self):
        """Logs the completion of a tracing session."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "SESSION_END",
            "session_id": self.session_id,
            "pid": self.pid
        }
        self._write_entry(entry)

