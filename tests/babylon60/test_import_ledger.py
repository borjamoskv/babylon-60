# [C5-REAL] Exergy-Maximized
"""
Unit tests for the cryptographically verifiable Import Resolution Ledger.
"""

import os
import json
import pytest
from pathlib import Path
from babylon60.import_ledger import ImportResolutionLedger
from babylon60.shadow_tracer import enable_tracer, disable_tracer

def test_ledger_hashing_and_chaining(tmp_path):
    ledger_file = tmp_path / "test_import_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    # 1. Start session
    ledger.start_session()
    assert ledger._session_active is True
    
    # 2. Log several resolutions
    h1 = ledger.log_resolution("importer_a", "cortex.module_x", "REDIRECTED", "babylon60.module_x")
    h2 = ledger.log_resolution("importer_b", "cortex.module_y", "WOULD_BREAK", "None")
    h3 = ledger.log_resolution("importer_c", "cortex.module_z", "DIRECT", "None")
    
    # Verify memory states
    assert len(h1) == 64
    assert len(h2) == 64
    assert len(h3) == 64
    assert h1 != h2
    assert h2 != h3
    
    # 3. End session
    final_hash = ledger.end_session()
    assert ledger._session_active is False
    
    # 4. Verify cryptographic ledger file
    result = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert result.get("status") == "verified"
    assert result.get("total_lines_read") == 5  # START + 3 RESOLUTION + END
    assert result.get("final_hash") == final_hash

def test_ledger_tampering_detection(tmp_path):
    ledger_file = tmp_path / "tampered_import_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    ledger.start_session()
    ledger.log_resolution("module_a", "cortex.core", "REDIRECTED", "babylon60.core")
    ledger.end_session()
    
    # Read the entries and modify one line
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Verify original is fine
    assert ImportResolutionLedger.verify_ledger(str(ledger_file)).get("status") == "verified"
    
    # Tamper with the resolution name in the second entry
    entry_data = json.loads(lines[1])
    entry_data["imported"] = "cortex.hacked"
    lines[1] = json.dumps(entry_data) + "\n"
    
    with open(ledger_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Verify tampered fails
    tamper_result = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert tamper_result.get("status") == "failed"
    assert "mismatch" in tamper_result.get("reason", "") or "broken" in tamper_result.get("reason", "")

def test_ledger_tampering_signature_detection(tmp_path):
    ledger_file = tmp_path / "tampered_sig_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    ledger.start_session()
    ledger.log_resolution("module_a", "cortex.core", "REDIRECTED", "babylon60.core")
    ledger.end_session()
    
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Tamper with the signature in the SESSION_END block
    entry_data = json.loads(lines[-1])
    entry_data["signature"] = "a" * 128  # Invalid hex signature
    lines[-1] = json.dumps(entry_data) + "\n"
    
    with open(ledger_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Verify signature verification fails
    tamper_result = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert tamper_result.get("status") == "failed"
    assert "signature" in tamper_result.get("reason", "")

def test_shadow_tracer_integration_with_ledger(tmp_path, monkeypatch):
    ledger_file = tmp_path / "integrated_ledger.jsonl"
    
    monkeypatch.setenv("CORTEX_IMPORT_LEDGER", "1")
    monkeypatch.setenv("CORTEX_IMPORT_LEDGER_PATH", str(ledger_file))
    
    tracer = enable_tracer(mode="present", force=True)
    try:
        # Import something that triggers the tracer
        import cortex.database
        
    finally:
        disable_tracer(force=True)
        
    assert ledger_file.exists()
    
    result = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert result.get("status") == "verified"
    
    # Must have at least SESSION_START, RESOLUTION (for database), and SESSION_END
    assert result.get("total_lines_read", 0) >= 3
