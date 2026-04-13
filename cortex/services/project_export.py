from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from starlette.concurrency import run_in_threadpool

from cortex.utils.export import export_facts

_DANGEROUS_PATH_CHARS = frozenset("\0\r\n\t")


class UnsupportedExportFormatError(ValueError):
    """Raised when the route receives an unsupported export format."""


class InvalidExportPathCharsError(ValueError):
    """Raised when the requested path contains forbidden characters."""


class ExportPathOutsideWorkspaceError(ValueError):
    """Raised when the target export path escapes the workspace."""


class InvalidExportPathError(ValueError):
    """Raised when the requested path cannot be resolved safely."""


class ProjectExportExecutionError(RuntimeError):
    """Raised when fact export or artifact writing fails."""


class ProjectExportEngine(Protocol):
    """Minimal sync search contract used by the export workflow."""

    def search(self, *, project: str, limit: int): ...


@dataclass(frozen=True)
class ProjectExportResult:
    """Export artifact metadata returned to the HTTP layer."""

    project: str
    artifact: Path


def resolve_export_path(path: str | None, project: str) -> Path:
    """Resolve an export target without allowing traversal outside the workspace."""
    if not path:
        return Path.cwd() / f"{project}_export.json"

    if any(char in path for char in _DANGEROUS_PATH_CHARS) or ".." in path:
        raise InvalidExportPathCharsError

    try:
        base_dir = Path.cwd().resolve(strict=True)
        target_path = Path(path).resolve()
    except (ValueError, RuntimeError, OSError):
        raise InvalidExportPathError from None

    if not target_path.is_relative_to(base_dir):
        raise ExportPathOutsideWorkspaceError
    return target_path


async def export_project_artifact(
    engine: ProjectExportEngine,
    *,
    project: str,
    path: str | None,
    fmt: str,
    max_facts: int,
) -> ProjectExportResult:
    """Search, serialize, and write a project export artifact."""
    if fmt != "json":
        raise UnsupportedExportFormatError

    target_path = resolve_export_path(path, project)

    try:
        facts = await run_in_threadpool(
            engine.search,
            project=project,
            limit=max_facts,
        )
        content = export_facts(facts, fmt="json")

        def _write_export() -> Path:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return target_path

        artifact = await run_in_threadpool(_write_export)
    except (OSError, ValueError) as exc:
        raise ProjectExportExecutionError from exc

    return ProjectExportResult(project=project, artifact=artifact)
