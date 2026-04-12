#!/usr/bin/env python3
"""Reconcile non-canonical top-level workspace residue.

This script keeps the CORTEX core checkout readable without moving or deleting
local data. It reports top-level untracked directories that sit outside the
tracked source-of-truth tree and can append them to ``.git/info/exclude`` so
they stop polluting ``git status`` locally.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_MARKERS = frozenset(
    {
        ".git",
        ".gitmodules",
        "Cargo.toml",
        "foundry.toml",
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
        "yarn.lock",
    }
)
GENERATED_RESIDUE_NAMES = frozenset({"artifacts", "output", "scratch"})


@dataclass(frozen=True)
class ResidueEntry:
    """Describe a top-level directory that does not belong to the canonical tree."""

    name: str
    path: Path
    size_bytes: int
    classification: str
    markers: tuple[str, ...]
    destination_hint: str


def _run_git(repo_root: Path, args: list[str]) -> str:
    """Run a git command inside ``repo_root`` and return stripped stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _paths_from_output(output: str) -> list[Path]:
    """Convert newline-separated git output into normalized relative paths."""

    paths: list[Path] = []
    for line in output.splitlines():
        normalized = line.strip().rstrip("/")
        if normalized:
            paths.append(Path(normalized))
    return paths


def _resolve_repo_root(candidate: Path) -> Path:
    """Resolve ``candidate`` to a git repository root."""

    if not candidate.exists():
        raise FileNotFoundError(f"Repository path does not exist: {candidate}")

    resolved = candidate.resolve()
    try:
        repo_root = _run_git(resolved, ["rev-parse", "--show-toplevel"])
    except subprocess.CalledProcessError as err:
        raise ValueError(f"Not a git repository: {resolved}") from err

    return Path(repo_root)


def _tracked_top_level_entries(repo_root: Path) -> set[str]:
    """Return the tracked top-level names from the current git index."""

    tracked = _paths_from_output(_run_git(repo_root, ["ls-files"]))
    return {path.parts[0] for path in tracked if path.parts}


def _candidate_top_level_directories(repo_root: Path) -> list[Path]:
    """Return untracked top-level directories that are outside tracked roots."""

    tracked_top_level = _tracked_top_level_entries(repo_root)
    untracked = _paths_from_output(
        _run_git(repo_root, ["ls-files", "--others", "--exclude-standard", "--directory"])
    )

    candidates: dict[str, Path] = {}
    for entry in untracked:
        if not entry.parts:
            continue

        top_level_name = entry.parts[0]
        if top_level_name in tracked_top_level:
            continue

        top_level_path = repo_root / top_level_name
        if top_level_path.is_dir():
            candidates[top_level_name] = top_level_path

    return [candidates[name] for name in sorted(candidates)]


def _directory_size_bytes(path: Path) -> int:
    """Return the recursive byte size of ``path``.

    Files that vanish during traversal or cannot be stat-ed are skipped so the
    report remains resilient on live workspaces.
    """

    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _project_markers(path: Path) -> tuple[str, ...]:
    """Return project marker files that hint the directory is an external clone."""

    found = [marker for marker in PROJECT_MARKERS if (path / marker).exists()]
    return tuple(sorted(found))


def _classify_residue(path: Path, markers: tuple[str, ...]) -> str:
    """Classify residue according to its likely operational role."""

    if path.name in GENERATED_RESIDUE_NAMES:
        return "generated-residue"
    if markers:
        return "cloned-subproject"
    return "top-level-residue"


def _destination_hint(name: str, classification: str) -> str:
    """Return a concise operator hint for where the residue should live."""

    if classification == "generated-residue":
        return "keep local-only"
    if classification == "cloned-subproject":
        return "move to sibling repo or quarantine"
    if name.startswith("X-"):
        return "quarantine or delete after review"
    return "classify ownership before tracking"


def discover_workspace_residue(repo_root: Path) -> list[ResidueEntry]:
    """Discover top-level untracked directories that sit outside tracked roots."""

    resolved_root = _resolve_repo_root(repo_root)
    entries: list[ResidueEntry] = []

    for path in _candidate_top_level_directories(resolved_root):
        markers = _project_markers(path)
        classification = _classify_residue(path, markers)
        entries.append(
            ResidueEntry(
                name=path.name,
                path=path,
                size_bytes=_directory_size_bytes(path),
                classification=classification,
                markers=markers,
                destination_hint=_destination_hint(path.name, classification),
            )
        )

    return entries


def _format_size(size_bytes: int) -> str:
    """Format a byte count with a compact binary unit suffix."""

    if size_bytes < 1024:
        return f"{size_bytes} B"

    units = ("KiB", "MiB", "GiB", "TiB")
    value = float(size_bytes)
    for unit in units:
        value /= 1024.0
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
    return f"{size_bytes} B"


def render_report(entries: list[ResidueEntry]) -> str:
    """Render a human-readable residue report."""

    if not entries:
        return "[workspace] No non-canonical top-level directories detected."

    lines = [
        "[workspace] Non-canonical top-level directories:",
    ]
    for entry in entries:
        marker_suffix = ""
        if entry.markers:
            marker_suffix = f" | markers: {', '.join(entry.markers)}"
        lines.append(
            f"- {entry.name} | {entry.classification} | {_format_size(entry.size_bytes)}"
            f" | hint: {entry.destination_hint}{marker_suffix}"
        )
    return "\n".join(lines)


def write_local_exclude(repo_root: Path, entries: list[ResidueEntry]) -> tuple[int, list[str]]:
    """Append residue entries to ``.git/info/exclude`` without touching tracked ignore rules."""

    resolved_root = _resolve_repo_root(repo_root)
    exclude_path = resolved_root / ".git" / "info" / "exclude"
    existing_text = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    existing_lines = existing_text.splitlines()
    existing_set = set(existing_lines)

    additions: list[str] = []
    for entry in entries:
        pattern = f"{entry.name}/"
        if pattern not in existing_set:
            additions.append(pattern)
            existing_set.add(pattern)

    if not additions:
        return 0, []

    lines = existing_lines[:]
    if lines and lines[-1] != "":
        lines.append("")
    lines.append("# Local workspace reconciliation")
    lines.extend(additions)
    exclude_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(additions), additions


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, report residue, and optionally update local excludes."""

    parser = argparse.ArgumentParser(
        description="Report and locally isolate non-canonical top-level directories."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the repository to inspect. Defaults to the current directory.",
    )
    parser.add_argument(
        "--write-local-exclude",
        action="store_true",
        help="Append detected directories to .git/info/exclude.",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = _resolve_repo_root(Path(args.repo_root))
        entries = discover_workspace_residue(repo_root)
    except (FileNotFoundError, ValueError) as err:
        print(f"[workspace] {err}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as err:
        print(f"[workspace] git command failed: {err}", file=sys.stderr)
        return 2

    print(render_report(entries))
    if not entries:
        return 0

    if args.write_local_exclude:
        try:
            added_count, additions = write_local_exclude(repo_root, entries)
        except (FileNotFoundError, ValueError) as err:
            print(f"[workspace] {err}", file=sys.stderr)
            return 2
        except OSError as err:
            print(f"[workspace] could not update .git/info/exclude: {err}", file=sys.stderr)
            return 2

        if added_count == 0:
            print("[workspace] Local exclude already covered all detected directories.")
        else:
            print(
                "[workspace] Added to .git/info/exclude: "
                + ", ".join(additions)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
