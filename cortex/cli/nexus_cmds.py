import sqlite3
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from cortex.cli.errors import err_execution_failed, err_skill_not_found
from cortex.core.paths import find_skill_path, resolve_skill_script

__all__ = [
    "bridge",
    "nexus_skill_path",
    "ghosts",
    "nexus_cmds",
    "pulse",
    "run_nexus_skill",
    "sync",
]

console = Console()


def nexus_skill_path() -> Path:
    return find_skill_path(
        "singularity-nexus",
        "scripts/singularity_engine.py",
        "singularity_engine.py",
    ) or resolve_skill_script("singularity-nexus", "scripts", "singularity_engine.py")


def run_nexus_skill(args: list[str]):
    """Execute the singularity-nexus skill script natively streaming output."""
    skill_path = nexus_skill_path()
    if not skill_path.exists():
        err_skill_not_found("Singularity Nexus", str(skill_path))

    cmd = ["python3", str(skill_path)] + args

    try:
        # We don't capture output because we want Rich to render directly to the terminal
        # with full color support preserving the original aesthetics of Nexus.
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except (sqlite3.Error, OSError, RuntimeError) as e:
        err_execution_failed(" ".join(cmd), str(e))


@click.group(name="nexus")
def nexus_cmds():
    """🌌 Singularity Nexus v∞: Cross-Project Unification."""
    pass


@nexus_cmds.command()
def pulse():
    """System health audit across all MOSKV projects."""
    code = run_nexus_skill(["pulse"])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command()
def ghosts():
    """Sync ghosts across CORTEX (Handoffs) and local codebases."""
    code = run_nexus_skill(["ghosts"])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command()
@click.argument("source_project")
@click.argument("target_project")
@click.argument("pattern")
def bridge(source_project, target_project, pattern):
    """Bridge a sovereign pattern from source to target project."""
    code = run_nexus_skill(["bridge", source_project, target_project, pattern])
    if code != 0:
        sys.exit(code)


@nexus_cmds.command()
def sync():
    """Full unification pipeline (discover -> ghosts -> pulse)."""
    code = run_nexus_skill(["sync"])
    if code != 0:
        sys.exit(code)
