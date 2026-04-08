from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_github_agent_demo.py"


def _run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def test_status_demo_script_returns_ok_payload() -> None:
    result = _run_demo("--op", "status")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["op"] == "status"
    assert payload["result"]["status"] == "ok"
    assert payload["result"]["repo"]


def test_permalink_demo_script_returns_url() -> None:
    result = _run_demo(
        "--op",
        "permalink",
        "--path",
        "cortex/cli/github_cmds.py",
        "--lines",
        "10-25",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["op"] == "permalink"
    assert payload["result"]["url"].startswith("https://")
    assert "#L10-L25" in payload["result"]["url"]
