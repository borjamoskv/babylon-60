# [C5-REAL] Exergy-Maximized
"""
Git Spam Guard
Enforces Rule R9 (Prevención de Bucles Sucios) by automatically excluding
recurrent temporary files and logs from git tracking to prevent infinite commit loops.
"""

import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_ignored(file_path: str, workspace_root: str = ".") -> None:
    """
    Ensures that a given file_path is ignored by Git,
    either via .gitignore or .git/info/exclude.
    """
    try:
        root = Path(workspace_root).resolve()
        
        # Try .git/info/exclude first for local ignores without mutating the repo structure
        git_dir = root / ".git"
        if git_dir.exists() and git_dir.is_dir():
            exclude_file = git_dir / "info" / "exclude"
            if exclude_file.exists():
                _append_if_missing(exclude_file, file_path)
                return
                
        # Fallback to .gitignore
        gitignore = root / ".gitignore"
        _append_if_missing(gitignore, file_path)

    except Exception as e:
        logger.error(f"GitSpamGuard: Failed to ignore {file_path}: {e}")

def _append_if_missing(ignore_file: Path, pattern: str) -> None:
    if not ignore_file.exists():
        with open(ignore_file, "w", encoding="utf-8") as f:
            f.write(f"{pattern}\n")
        logger.info(f"GitSpamGuard: Created {ignore_file.name} and ignored {pattern}")
        return

    with open(ignore_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if pattern not in lines:
        with open(ignore_file, "a", encoding="utf-8") as f:
            # Ensure it starts on a new line
            if lines and lines[-1].strip() != "":
                f.write("\n")
            f.write(f"{pattern}\n")
        logger.info(f"GitSpamGuard: Added {pattern} to {ignore_file.name}")
