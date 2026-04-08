from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def test_mega_tools_import_does_not_require_tempdir(monkeypatch) -> None:
    import cortex.mcp.mega_tools as mega_tools

    calls = 0

    def _missing_tempdir() -> str:
        nonlocal calls
        calls += 1
        raise FileNotFoundError("tempdir unavailable")

    monkeypatch.setattr(tempfile, "gettempdir", _missing_tempdir)

    reloaded = importlib.reload(mega_tools)

    assert calls == 0
    assert reloaded._safe_bases() == (
        str(Path.home()),
        "/tmp",
        "/private/tmp",
    )
    assert calls == 1
