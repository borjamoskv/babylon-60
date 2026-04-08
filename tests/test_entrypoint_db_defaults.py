from __future__ import annotations

import importlib
import importlib.util
import inspect
from pathlib import Path


def _reload_paths():
    import cortex.core.paths as core_paths

    return importlib.reload(core_paths)


def _load_script_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_swarm_cli_defaults_follow_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    _reload_paths()
    import cortex.cli.swarm_cmds as swarm_cmds

    reloaded = importlib.reload(swarm_cmds)
    deploy_db = next(param.default for param in reloaded.swarm_deploy.params if param.name == "db")
    board_db = next(param.default for param in reloaded.swarm_board_cmd.params if param.name == "db")

    assert deploy_db == str(preferred)
    assert board_db == str(preferred)


def test_swarm_board_default_follows_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    _reload_paths()
    import cortex.extensions.ui.swarm_board as swarm_board

    reloaded = importlib.reload(swarm_board)

    assert inspect.signature(reloaded.SwarmBoard).parameters["db_path"].default == str(preferred)


def test_swarm_dashboard_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    module = _load_script_module(
        "test_swarm_dashboard",
        Path(__file__).resolve().parent.parent / "scripts" / "swarm_dashboard.py",
    )

    assert module.DB_PATH == preferred


def test_toolbox_launcher_exports_db_path_aliases() -> None:
    script = (
        Path(__file__).resolve().parent.parent
        / "cortex"
        / "mcp"
        / "toolbox"
        / "run_toolbox.sh"
    ).read_text()

    assert 'export CORTEX_DB_PATH="${CORTEX_DB_PATH:-${CORTEX_DB:-${HOME}/.cortex/cortex.db}}"' in script
    assert 'export CORTEX_DB="${CORTEX_DB:-${CORTEX_DB_PATH}}"' in script


def test_forensic_hunter_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    module = _load_script_module(
        "test_forensic_hunter",
        Path(__file__).resolve().parent.parent / "scripts" / "forensic_hunter.py",
    )

    assert module.DEFAULT_DB_PATH == str(preferred)
    assert inspect.signature(module.hunt).parameters["db_path"].default == str(preferred)


def test_sky_stalker_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    module = _load_script_module(
        "test_sky_stalker",
        Path(__file__).resolve().parent.parent / "scripts" / "forensic_hunters" / "sky_stalker.py",
    )

    assert module.DEFAULT_DB_PATH == str(preferred)
    assert inspect.signature(module.hunt_sky).parameters["db_path"].default == str(preferred)


def test_lido_warden_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    module = _load_script_module(
        "test_lido_warden",
        Path(__file__).resolve().parent.parent / "scripts" / "forensic_hunters" / "lido_warden.py",
    )

    assert module.DEFAULT_DB_PATH == str(preferred)
    assert inspect.signature(module.hunt_lido).parameters["db_path"].default == str(preferred)
