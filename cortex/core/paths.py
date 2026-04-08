# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX — Canonical Path Resolution.

Single source of truth for ALL filesystem paths in the codebase.
Every path is overridable via environment variables for portability,
CI, Docker, and third-party onboarding.

Usage::

    from cortex.core.paths import CORTEX_DIR, AGENT_DIR, CORTEX_DB

Environment variables::

    CORTEX_DIR          → ~/.cortex (default)
    CORTEX_AGENT_DIR    → ~/.agent (default)
    CORTEX_DB_PATH      → absolute DB path override (preferred)
    CORTEX_DB          → legacy DB path override
    CORTEX_DB_NAME      → cortex.db (default, relative to CORTEX_DIR)
    CORTEX_SKILLS_DIR   → ~/.gemini/antigravity/skills (default)
    CORTEX_MODELS_DIR   → ~/.cortex/models (default)
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "AGENT_DIR",
    "canonical_skill_name",
    "COLD_STORAGE_DB",
    "CORTEX_DB",
    "CORTEX_DIR",
    "DAEMON_CONFIG_FILE",
    "DAEMON_STATUS_FILE",
    "find_skill_path",
    "iter_skill_name_candidates",
    "MEMORY_DIR",
    "MODELS_DIR",
    "PERSONAL_DB",
    "require_skill_path",
    "resolve_skill_dir",
    "resolve_skill_name",
    "resolve_skill_script",
    "resolve_skill_scripts_dir",
    "SKILLS_DIR",
    "SYNC_STATE_FILE",
]

# ─── Core Directories ───────────────────────────────────────────────

CORTEX_DIR: Path = Path(os.environ.get("CORTEX_DIR", Path.home() / ".cortex"))
"""Root CORTEX data directory. Override: CORTEX_DIR env var."""

AGENT_DIR: Path = Path(os.environ.get("CORTEX_AGENT_DIR", Path.home() / ".agent"))
"""Agent configuration and memory directory. Override: CORTEX_AGENT_DIR env var."""

# ─── Database ────────────────────────────────────────────────────────

def _resolve_cortex_db() -> Path:
    """Resolve the main SQLite DB path from supported env aliases."""
    override = os.environ.get("CORTEX_DB_PATH") or os.environ.get("CORTEX_DB")
    if override:
        return Path(override).expanduser()
    return CORTEX_DIR / os.environ.get("CORTEX_DB_NAME", "cortex.db")


CORTEX_DB: Path = _resolve_cortex_db()
"""Path to the main CORTEX SQLite database."""

PERSONAL_DB: Path = CORTEX_DIR / "personal_memories.db"
"""Repatriated personal/side-project memories (NAROA, LIVENOTCH, etc.)."""

COLD_STORAGE_DB: Path = CORTEX_DIR / "cold_storage.db"
"""Archived test/junk projects. Read-only cold storage."""

# ─── Derived Paths ───────────────────────────────────────────────────

MEMORY_DIR: Path = AGENT_DIR / "memory"
"""Agent memory file directory (ghosts, system, daemon status)."""

DAEMON_CONFIG_FILE: Path = CORTEX_DIR / "daemon_config.json"
"""Daemon configuration file."""

DAEMON_STATUS_FILE: Path = MEMORY_DIR / "daemon_status.json"
"""Daemon status output file."""

SYNC_STATE_FILE: Path = CORTEX_DIR / "sync_state.json"
"""Sync engine state tracking file."""

MODELS_DIR: Path = Path(os.environ.get("CORTEX_MODELS_DIR", str(CORTEX_DIR / "models")))
"""Embedding model cache directory. Override: CORTEX_MODELS_DIR env var."""

SKILLS_DIR: Path = Path(
    os.environ.get(
        "CORTEX_SKILLS_DIR",
        str(Path.home() / ".gemini" / "antigravity" / "skills"),
    )
)
"""Skills base directory. Override: CORTEX_SKILLS_DIR env var."""

# Canonical MOSKV-1 identifiers do not always match the installed Antigravity
# directory names. This alias table keeps path resolution and skill lookups
# aligned without forcing every caller to know the current filesystem label.
SKILL_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "aether-1": ("Devin-Apex", "MCP-Forge-Omega", "Moltbook-App-Forge-Omega"),
    "boveda-1": ("CORTEX-Guard-Omega",),
    "comms-hub-omega": ("Comms-Hub-Omega",),
    "cortex": ("vsa-sdm-memory-omega",),
    "impactv-1": ("Aesthetic-Foundry-Omega", "steve-jobs-omega"),
    "keter-omega": ("CORTEX-Orchestra-Omega",),
    "legion-1": ("CORTEX-Swarm-Prime",),
    "singularity-nexus": ("Cognitive-Crystallizer-Omega",),
    "sortu": ("Sortu",),
}


def _normalize_skill_name(skill_name: str) -> str:
    """Normalize a skill identifier for alias matching."""
    return skill_name.strip().lower().replace(" ", "-").replace("_", "-")


def iter_skill_name_candidates(skill_name: str) -> tuple[str, ...]:
    """Return the ordered candidate names for a logical skill identifier."""
    original = skill_name.strip()
    if not original:
        return ("",)

    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in (original, *SKILL_NAME_ALIASES.get(_normalize_skill_name(original), ())):
        key = _normalize_skill_name(candidate)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return tuple(candidates)


def canonical_skill_name(skill_name: str) -> str:
    """Return the canonical MOSKV-1 identifier for a skill or alias."""
    normalized = _normalize_skill_name(skill_name)
    if normalized in SKILL_NAME_ALIASES:
        return normalized

    for canonical, aliases in SKILL_NAME_ALIASES.items():
        if any(_normalize_skill_name(alias) == normalized for alias in aliases):
            return canonical

    return normalized


def _existing_skill_dir_name(candidate: str) -> str | None:
    """Return the actual directory name for a candidate if it exists."""
    if not SKILLS_DIR.exists():
        return None

    normalized = _normalize_skill_name(candidate)
    exact_match: str | None = None
    normalized_match: str | None = None

    for entry in SKILLS_DIR.iterdir():
        if not entry.is_dir():
            continue
        if entry.name == candidate:
            exact_match = entry.name
            break
        if normalized_match is None and _normalize_skill_name(entry.name) == normalized:
            normalized_match = entry.name

    return exact_match or normalized_match


def resolve_skill_name(skill_name: str) -> str:
    """Resolve a logical skill identifier to the installed directory name."""
    for candidate in iter_skill_name_candidates(skill_name):
        resolved = _existing_skill_dir_name(candidate)
        if resolved is not None:
            return resolved
    return skill_name


def resolve_skill_dir(skill_name: str) -> Path:
    """Return the canonical filesystem directory for a skill."""
    return SKILLS_DIR / resolve_skill_name(skill_name)


def resolve_skill_scripts_dir(skill_name: str) -> Path:
    """Return the canonical scripts directory for a skill."""
    return resolve_skill_dir(skill_name) / "scripts"


def resolve_skill_script(skill_name: str, *relative_parts: str) -> Path:
    """Return the canonical path to a file inside a skill directory."""
    return resolve_skill_dir(skill_name).joinpath(*relative_parts)


def find_skill_path(skill_name: str, *relative_candidates: str) -> Path | None:
    """Return the first existing relative path inside a skill directory."""
    base_dir = resolve_skill_dir(skill_name)
    for relative in relative_candidates:
        candidate = base_dir / Path(relative)
        if candidate.exists():
            return candidate
    return None


def require_skill_path(skill_name: str, *relative_candidates: str) -> Path:
    """Resolve the first existing path inside a skill directory or raise."""
    path = find_skill_path(skill_name, *relative_candidates)
    if path is not None:
        return path

    requested = ", ".join(relative_candidates) or "<no candidates>"
    raise FileNotFoundError(
        f"Skill '{skill_name}' is missing required path(s): {requested} under {resolve_skill_dir(skill_name)}"
    )

# ─── Convenience ─────────────────────────────────────────────────────

AUDIT_LOG_PATH: Path = CORTEX_DIR / "audit.log"
"""Append-only audit log for admin/CLI operations."""

DRIFT_DIR: Path = CORTEX_DIR / "drift"
"""Topological drift signature storage."""
