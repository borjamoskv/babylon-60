# cortex/sovereign/bridge.py
"""Sovereign Bridge — The interface between CORTEX and Antigravity skills.

Provides the `SovereignBridge` class, which handles dynamic loading and
execution of Antigravity skills (aether-1, keter-omega, legion-1, etc.)
within the CORTEX environment.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from cortex.core.paths import SKILLS_DIR, resolve_skill_dir

logger = logging.getLogger(__name__)

# Base directory for Antigravity skills
SKILLS_ROOT = SKILLS_DIR


class SovereignBridge:
    """Orchestrates interaction with the Antigravity skill ecosystem."""

    def __init__(self, skills_root: Optional[Path] = None) -> None:
        self.skills_root = skills_root or SKILLS_ROOT
        self.registry: dict[str, Any] = {}
        self.discover_and_load()

    def discover_and_load(self) -> None:
        """Scan SKILLS_ROOT for skill packages and register them for lazy loading."""
        if not self.skills_root.exists():
            logger.warning("Sovereign Bridge: SKILLS_ROOT %s not found.", self.skills_root)
            return

        for entry in self.skills_root.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").exists():
                self.registry[entry.name] = None

        logger.info("Sovereign Bridge: %s skills registered (lazy load).", len(self.registry))

    def _load_skill(self, skill_name: str) -> None:
        """Load a skill from the filesystem without relying on antigravity.skills."""
        skill_dir = self._resolve_skill_dir(skill_name)
        if not skill_dir.exists():
            raise ImportError(f"Sovereign skill '{skill_name}' not found at {skill_dir}")

        candidates = self._candidate_entrypoints(skill_name, skill_dir)
        if not candidates:
            raise ImportError(
                f"Sovereign skill '{skill_name}' has no Python entrypoint under {skill_dir}"
            )

        first_loaded: Any | None = None
        first_loaded_path: Path | None = None
        last_error: Exception | None = None

        for candidate in candidates:
            try:
                module = self._load_module_from_path(skill_name, skill_dir, candidate)
            except (ImportError, OSError, SyntaxError, ValueError) as e:
                last_error = e
                logger.debug(
                    "Failed to load candidate %s for skill %s: %s", candidate, skill_name, e
                )
                continue

            if first_loaded is None:
                first_loaded = module
                first_loaded_path = candidate

            if self._has_entrypoint(module):
                self.registry[skill_name] = module
                logger.debug("Skill loaded: %s from %s", skill_name, candidate)
                return

        if first_loaded is not None:
            self.registry[skill_name] = first_loaded
            logger.warning(
                "Skill %s loaded from %s but exposes no callable main/run entrypoint",
                skill_name,
                first_loaded_path,
            )
            return

        detail = f": {last_error}" if last_error else ""
        raise ImportError(f"Failed to load sovereign skill '{skill_name}'{detail}")

    def _resolve_skill_dir(self, skill_name: str) -> Path:
        if self.skills_root == SKILLS_ROOT:
            return resolve_skill_dir(skill_name)
        return self.skills_root / skill_name

    def _candidate_entrypoints(self, skill_name: str, skill_dir: Path) -> list[Path]:
        normalized = skill_name.replace("-", "_").lower()
        preferred_stems = [
            "main",
            normalized,
            f"{normalized}_engine",
            f"{normalized}_bridge",
            f"{normalized}_server",
            "engine",
            "bridge",
            "bridge_server",
            "server",
            "ghost",
        ]
        candidates: list[Path] = []
        seen: set[Path] = set()

        for base in (skill_dir, skill_dir / "scripts"):
            if not base.is_dir():
                continue
            for stem in preferred_stems:
                candidate = base / f"{stem}.py"
                if candidate.is_file() and candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)

        py_files = sorted(
            p for p in skill_dir.rglob("*.py") if p.is_file() and p.name != "__init__.py"
        )
        if len(py_files) == 1 and py_files[0] not in seen:
            candidates.append(py_files[0])
            return candidates

        fallback = [
            p
            for p in py_files
            if p.stem.endswith(("_engine", "_bridge", "_server")) and p not in seen
        ]
        if len(fallback) == 1:
            candidates.append(fallback[0])

        return candidates

    @contextmanager
    def _skill_import_paths(self, skill_dir: Path) -> Iterator[None]:
        added: list[str] = []
        path_candidates = [skill_dir, skill_dir / "scripts"]

        for path in path_candidates:
            if path.is_dir():
                path_str = str(path)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)
                    added.append(path_str)

        try:
            yield
        finally:
            for path_str in reversed(added):
                try:
                    sys.path.remove(path_str)
                except ValueError:
                    pass

    @staticmethod
    def _module_origin(module: Any) -> Path | None:
        module_dict = getattr(module, "__dict__", None)
        if not isinstance(module_dict, dict):
            return None

        origin = module_dict.get("__file__")
        if not origin:
            spec = module_dict.get("__spec__")
            origin = getattr(spec, "origin", None)

        if origin in {None, "built-in", "frozen"}:
            return None
        if not isinstance(origin, (str, os.PathLike)):
            return None
        try:
            return Path(origin).resolve()
        except (OSError, RuntimeError, TypeError, ValueError):
            return None

    @staticmethod
    def _import_roots(skill_dir: Path) -> tuple[Path, ...]:
        roots: list[Path] = []
        for path in (skill_dir, skill_dir / "scripts"):
            if path.is_dir():
                roots.append(path.resolve())
        return tuple(roots)

    @classmethod
    def _module_belongs_to_roots(cls, module: Any, roots: tuple[Path, ...]) -> bool:
        origin = cls._module_origin(module)
        if origin is None:
            return False
        return any(origin.is_relative_to(root) for root in roots)

    def _local_import_names(self, skill_dir: Path) -> set[str]:
        names: set[str] = set()
        for root in self._import_roots(skill_dir):
            for entry in root.iterdir():
                if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
                    names.add(entry.stem)
                    continue
                if entry.is_dir() and (entry / "__init__.py").is_file():
                    names.add(entry.name)
        return names

    @contextmanager
    def _skill_module_scope(self, skill_dir: Path) -> Iterator[None]:
        roots = self._import_roots(skill_dir)
        local_import_names = self._local_import_names(skill_dir)
        displaced_modules: dict[str, Any] = {}
        preexisting_local_modules = {
            name
            for name, module in sys.modules.items()
            if self._module_belongs_to_roots(module, roots)
        }

        for module_name in local_import_names:
            module = sys.modules.get(module_name)
            if module is None or self._module_belongs_to_roots(module, roots):
                continue
            displaced_modules[module_name] = module
            sys.modules.pop(module_name, None)

        try:
            yield
        finally:
            loaded_local_modules = [
                name
                for name, module in list(sys.modules.items())
                if name not in preexisting_local_modules
                and self._module_belongs_to_roots(module, roots)
            ]
            for module_name in loaded_local_modules:
                sys.modules.pop(module_name, None)
            for module_name, module in displaced_modules.items():
                sys.modules[module_name] = module

    @contextmanager
    def _skill_scope(self, skill_dir: Path) -> Iterator[None]:
        with self._skill_module_scope(skill_dir):
            with self._skill_import_paths(skill_dir):
                yield

    def _load_module_from_path(self, skill_name: str, skill_dir: Path, module_path: Path) -> Any:
        module_name = f"cortex_antigravity_{skill_name.replace('-', '_')}_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_path}")

        module = importlib.util.module_from_spec(spec)
        with self._skill_scope(skill_dir):
            spec.loader.exec_module(module)
        return module

    @staticmethod
    def _has_entrypoint(module: Any) -> bool:
        return (hasattr(module, "main") and callable(module.main)) or (
            hasattr(module, "run") and callable(module.run)
        )

    def execute(self, skill_name: str, *args, **kwargs) -> Any:
        """Execute the 'main' entry point of a registered skill."""
        skill = self.registry.get(skill_name)
        if not skill:
            # Try to load it lazily if not found
            self._load_skill(skill_name)
            skill = self.registry.get(skill_name)

        if not skill:
            raise ImportError(f"Sovereign skill '{skill_name}' is not available.")

        skill_dir = self._resolve_skill_dir(skill_name)
        with self._skill_scope(skill_dir):
            if hasattr(skill, "main") and callable(skill.main):
                logger.info("Executing Sovereign Skill: %s", skill_name)
                return skill.main(*args, **kwargs)

            # Fallback for skills that might expose other entry points
            if hasattr(skill, "run") and callable(skill.run):
                return skill.run(*args, **kwargs)

        raise AttributeError(f"Skill '{skill_name}' has no callable 'main' or 'run' entry point.")

    def list_skills(self) -> list[str]:
        """Return a list of all available skill names."""
        return list(self.registry.keys())
