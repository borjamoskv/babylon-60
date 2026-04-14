"""Validation for the official product demo."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_demo_module():
    repo_root = Path(__file__).resolve().parent.parent
    demo_path = repo_root / "examples" / "demo_canonical.py"
    spec = importlib.util.spec_from_file_location("demo_canonical", demo_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_demo_runs_and_exports_evidence(tmp_path: Path) -> None:
    module = _load_demo_module()
    module.reset_default_encrypter()

    previous_master_key = module.os.environ.pop("CORTEX_MASTER_KEY", None)
    previous_vault_key = module.os.environ.pop("CORTEX_VAULT_KEY", None)
    previous_testing = module.os.environ.pop("CORTEX_TESTING", None)

    try:
        result = module.run_demo(output_dir=tmp_path)
    finally:
        module.reset_default_encrypter()
        if previous_master_key is not None:
            module.os.environ["CORTEX_MASTER_KEY"] = previous_master_key
        if previous_vault_key is not None:
            module.os.environ["CORTEX_VAULT_KEY"] = previous_vault_key
        if previous_testing is not None:
            module.os.environ["CORTEX_TESTING"] = previous_testing

    assert result["fact_id"] > 0
    assert result["db_path"].exists()
    assert result["audit_path"].exists()
    assert result["integrity"]["valid"] is True
    assert module.os.environ.get("CORTEX_MASTER_KEY")

    exported = json.loads(result["audit_path"].read_text(encoding="utf-8"))
    assert exported["project"] == module.DEMO_PROJECT
    assert exported["integrity"]["valid"] is True
    assert exported["eu_ai_act"]["score"] == "5/5"
    assert exported["facts_summary"]["total_facts"] == 1
    assert len(exported["facts"]) == 1
    assert exported["facts"][0]["source"] == module.DEMO_AGENT
