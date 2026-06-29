# [C5-REAL] Exergy-Maximized
"""
Tests for the Import Resolution Ledger.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure the project root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from babylon60.import_ledger import ImportResolutionLedger

def test_ledger_creation_and_logging(tmp_path):
    ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    ledger.start_session()
    ledger.log_resolution("tests.caller", "cortex.core", "REDIRECTED", "babylon60.core")
    ledger.end_session()
    
    assert ledger_file.exists()
    
    # Read the lines and verify structures
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 3
    
    start_entry = json.loads(lines[0])
    assert start_entry["event"] == "SESSION_START"
    assert "session_id" in start_entry
    
    res_entry = json.loads(lines[1])
    assert res_entry["event"] == "RESOLUTION"
    assert res_entry["caller"] == "tests.caller"
    assert res_entry["source"] == "cortex.core"
    assert res_entry["type"] == "REDIRECTED"
    assert res_entry["target"] == "babylon60.core"
    
    end_entry = json.loads(lines[2])
    assert end_entry["event"] == "SESSION_END"
    assert end_entry["session_id"] == start_entry["session_id"]
