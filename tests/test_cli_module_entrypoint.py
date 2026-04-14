from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_module_cli(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CORTEX_NO_EMBED"] = "1"
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{pythonpath}" if pythonpath else str(REPO_ROOT)
    )
    return subprocess.run(
        [sys.executable, "-m", "cortex", *args, "--db", str(db_path)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_python_module_entrypoint_supports_root_memory_aliases(tmp_path: Path) -> None:
    db_path = tmp_path / "cortex.db"

    init_result = _run_module_cli(db_path, "init")
    assert init_result.returncode == 0, init_result.stderr or init_result.stdout

    store_result = _run_module_cli(
        db_path,
        "store",
        "my-api",
        "Rate limit is 100 req/min per API key",
        "--type",
        "config",
        "--tags",
        "api,limits",
        "--source",
        "agent:claude",
    )
    assert store_result.returncode == 0, store_result.stderr or store_result.stdout
    assert "Stored fact" in store_result.stdout

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM facts WHERE project = ? ORDER BY id DESC LIMIT 1",
            ("my-api",),
        ).fetchone()
    assert row is not None
    fact_id = str(row[0])

    search_result = _run_module_cli(db_path, "search", "rate limit", "-k", "1")
    assert search_result.returncode == 0, search_result.stderr or search_result.stdout
    assert "Results for" in search_result.stdout

    verify_result = _run_module_cli(db_path, "verify", fact_id)
    assert verify_result.returncode == 0, verify_result.stderr or verify_result.stdout
    assert "VERIFIED" in verify_result.stdout


def test_python_module_store_accepts_verified_confidence(tmp_path: Path) -> None:
    db_path = tmp_path / "cortex.db"

    init_result = _run_module_cli(db_path, "init")
    assert init_result.returncode == 0, init_result.stderr or init_result.stdout

    store_result = _run_module_cli(
        db_path,
        "store",
        "fraud-ops",
        "Confirmed IP mismatch from payment processor",
        "--source",
        "agent:risk-bot",
        "--confidence",
        "verified",
    )
    assert store_result.returncode == 0, store_result.stderr or store_result.stdout
    assert "Stored fact" in store_result.stdout


def test_python_module_timeline_checkout_reconstructs_by_transaction_id(tmp_path: Path) -> None:
    db_path = tmp_path / "cortex.db"

    init_result = _run_module_cli(db_path, "init")
    assert init_result.returncode == 0, init_result.stderr or init_result.stdout

    store_result = _run_module_cli(
        db_path,
        "store",
        "timeline-proj",
        "Timeline checkout must reconstruct the fact anchored to its transaction id",
        "--source",
        "agent:test-suite",
    )
    assert store_result.returncode == 0, store_result.stderr or store_result.stdout

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT tx_id FROM facts WHERE project = ? ORDER BY id DESC LIMIT 1",
            ("timeline-proj",),
        ).fetchone()
    assert row is not None
    tx_id = str(row[0])

    checkout_result = _run_module_cli(
        db_path,
        "timeline",
        "checkout",
        tx_id,
        "--project",
        "timeline-proj",
    )
    assert checkout_result.returncode == 0, checkout_result.stderr or checkout_result.stdout
    assert f"State at TX #{tx_id}" in checkout_result.stdout
    assert "timeline-proj" in checkout_result.stdout
