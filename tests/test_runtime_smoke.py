from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient


def test_cli_module_loader_has_no_failures() -> None:
    from cortex.cli.main import FAILED_COMMAND_MODULES, LOADED_COMMAND_MODULES

    assert FAILED_COMMAND_MODULES == {}
    assert "demiurge_cmds" in LOADED_COMMAND_MODULES
    assert "grammy_cmds" in LOADED_COMMAND_MODULES


def test_cli_loader_prefers_tracked_sortu_scripts() -> None:
    local_sortu = Path(__file__).resolve().parents[1] / "scripts" / "sortu" / "sortu_engine.py"
    if not local_sortu.exists():
        pytest.skip("Tracked Sortu scripts are not present in this checkout.")

    sys.modules.pop("sortu_engine", None)
    import cortex.cli.main  # noqa: F401

    sortu_engine = importlib.import_module("sortu_engine")
    assert Path(sortu_engine.__file__).resolve() == local_sortu.resolve()


def test_cli_help_exposes_recovered_command_groups() -> None:
    from cortex.cli import cli

    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "agent" in result.output
    assert "demiurge" in result.output
    assert "grammy" in result.output


def test_api_app_mounts_core_runtime_routes(tmp_path, monkeypatch) -> None:
    from cortex import config as cortex_config

    monkeypatch.setattr(cortex_config, "DB_PATH", str(tmp_path / "runtime-smoke.db"))
    from cortex.api import app

    with TestClient(app) as client:
        paths = {route.path for route in client.app.routes}

    assert "/" in paths
    assert "/health" in paths
    assert "/v1/facts/{fact_id}/history" in paths
    assert len(paths) >= 50


def test_engine_initializes_with_temp_db(tmp_path) -> None:
    from cortex.engine import CortexEngine

    db_path = tmp_path / "runtime-smoke.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)

    try:
        assert isinstance(engine, CortexEngine)
    finally:
        close_sync = getattr(engine, "close_sync", None)
        if callable(close_sync):
            close_sync()


@pytest.mark.asyncio
async def test_engine_verify_ledger_uses_real_backend(tmp_path, monkeypatch) -> None:
    from cortex.engine import CortexEngine

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    db_path = tmp_path / "runtime-ledger.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)

    try:
        await engine.init_db()
        report = await engine.verify_ledger()
        assert report["valid"] is True
        assert report["tx_count"] == 0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_engine_create_checkpoint_uses_real_backend(tmp_path, monkeypatch) -> None:
    from cortex.engine import CortexEngine

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    db_path = tmp_path / "runtime-checkpoint.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)

    try:
        await engine.init_db()
        checkpoint = await engine.create_checkpoint()
        assert checkpoint is None
    finally:
        await engine.close()


def test_admin_and_translate_routes_import_cleanly() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import cortex.routes.admin, cortex.routes.translate; print('ok')",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
    assert "Failed to initialize audit log file" not in result.stderr
