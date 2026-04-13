from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_module_cli(db_path: Path, *args: str, no_embed: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if no_embed:
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


def test_python_module_help_exposes_ledger_names() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cortex", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ledger" in result.stdout
    assert "trust-ledger" in result.stdout
    assert "vote-ledger" in result.stdout


def test_python_module_supports_trust_and_vote_ledger_flows(tmp_path: Path) -> None:
    db_path = tmp_path / "cortex.db"

    init_result = _run_module_cli(db_path, "init")
    assert init_result.returncode == 0, init_result.stderr or init_result.stdout

    store_result = _run_module_cli(
        db_path,
        "store",
        "fraud-ops",
        "Transaction flagged: IP mismatch",
        "--source",
        "agent:risk-bot",
    )
    assert store_result.returncode == 0, store_result.stderr or store_result.stdout

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM facts WHERE project = ? ORDER BY id DESC LIMIT 1",
            ("fraud-ops",),
        ).fetchone()
    assert row is not None
    fact_id = str(row[0])

    ledger_result = _run_module_cli(db_path, "ledger", "verify", no_embed=False)
    assert ledger_result.returncode == 0, ledger_result.stderr or ledger_result.stdout
    assert "Ledger is VALID" in ledger_result.stdout

    vote_result = _run_module_cli(
        db_path,
        "vote",
        fact_id,
        "1",
        "--agent",
        "agent:claude",
        no_embed=False,
    )
    assert vote_result.returncode == 0, vote_result.stderr or vote_result.stdout
    assert "votó 1" in vote_result.stdout

    vote_ledger_result = _run_module_cli(db_path, "vote-ledger", "verify", no_embed=False)
    assert vote_ledger_result.returncode == 0, vote_ledger_result.stderr or vote_ledger_result.stdout
    assert "Integridad de Cadena de Hashes: OK" in vote_ledger_result.stdout
