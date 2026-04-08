from __future__ import annotations

import sqlite3
from pathlib import Path

from cortex.mcp.toolbox_watchdog import ToolboxWatchdog


def _create_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO facts (content) VALUES ('shadow-copy-ok')")
        conn.commit()
    finally:
        conn.close()


def test_refresh_snapshot_copies_live_db(tmp_path: Path) -> None:
    live_db = tmp_path / "cortex.db"
    snapshot_db = tmp_path / "shadow.db"
    _create_db(live_db)

    watchdog = ToolboxWatchdog(
        db_path=live_db,
        snapshot_path=snapshot_db,
        log_dir=tmp_path / "logs",
    )

    watchdog._refresh_snapshot()

    conn = sqlite3.connect(snapshot_db)
    try:
        row = conn.execute("SELECT content FROM facts").fetchone()
    finally:
        conn.close()

    assert row == ("shadow-copy-ok",)


def test_spawn_uses_snapshot_database(tmp_path: Path, monkeypatch) -> None:
    live_db = tmp_path / "cortex.db"
    snapshot_db = tmp_path / "shadow.db"
    tools_yaml = tmp_path / "tools.yaml"
    _create_db(live_db)
    tools_yaml.write_text("kind: sources\nname: cortex-db\ntype: sqlite\ndatabase: ${CORTEX_DB}\n")

    watchdog = ToolboxWatchdog(
        tools_yaml=tools_yaml,
        db_path=live_db,
        snapshot_path=snapshot_db,
        log_dir=tmp_path / "logs",
    )

    captured: dict[str, object] = {}

    class DummyPopen:
        def __init__(self, cmd, env, stdout, stderr):
            captured["cmd"] = cmd
            captured["env"] = env
            captured["stdout"] = stdout
            captured["stderr"] = stderr
            self.pid = 4242

        def poll(self):
            return None

    monkeypatch.setattr("cortex.mcp.toolbox_watchdog.subprocess.Popen", DummyPopen)

    watchdog._spawn("/tmp/toolbox-bin")

    assert snapshot_db.exists()
    assert captured["cmd"] == [
        "/tmp/toolbox-bin",
        "--tools-file",
        str(tools_yaml),
        "--port",
        "5050",
    ]
    assert captured["env"]["CORTEX_DB"] == str(snapshot_db)
