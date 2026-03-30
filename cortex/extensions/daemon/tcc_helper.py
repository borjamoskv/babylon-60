"""
TCC Authorization Helper
Guiding the user through macOS Full Disk Access.
"""

import os
import subprocess
from pathlib import Path


def open_fda_settings() -> None:
    """Open macOS Security & Privacy -> Full Disk Access settings."""
    # This URL works on macOS 13+ (Ventura/Sonoma).
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
    try:
        subprocess.run(["open", url], check=False)
    except Exception:
        # Fallback to general security pane
        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security"],
            check=False,
        )


def prime_tcc_dialog() -> bool:
    """
    Attempt to access a protected folder to trigger the TCC dialog.
    This gives the user the initial prompt that will then show up in
    Full Disk Access settings.
    """
    protected_paths = [
        Path.home() / "Desktop",
        Path.home() / "Documents",
    ]

    for path in protected_paths:
        try:
            # listdir is usually enough to trigger TCC
            os.listdir(str(path))
            return True
        except PermissionError:
            # This is expected if not authorized
            continue
        except Exception:
            continue
    return False


def check_folder_access(path: Path) -> bool:
    """Return True if we have read access to the specified path."""
    try:
        os.listdir(str(path))
        return True
    except (PermissionError, OSError):
        return False


def get_fda_instruction() -> str:
    """Return instructions for the user to grant Full Disk Access."""
    return (
        "\n"
        "─── macOS Full Disk Access (FDA) Instruction ───\n"
        "1. System Settings has been opened to Privacy & Security > Full Disk Access.\n"
        "2. Find your Terminal (iTerm2, terminal, or Code) in the list and toggle it ON.\n"
        "3. If not in the list, click the '+' button and add your terminal application.\n"
        "4. This is REQUIRED for the daemon to persist while running from the Desktop.\n"
        "5. Once enabled, restart the daemon: 'cortex daemons start'.\n"
        "────────────────────────────────────────────────\n"
    )
