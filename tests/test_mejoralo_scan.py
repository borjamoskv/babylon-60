from __future__ import annotations

from cortex.extensions.mejoralo.scan import scan


class _ExplodingProcessPool:
    def __init__(self, *args, **kwargs) -> None:
        raise PermissionError("shared process pool unavailable")


def test_scan_falls_back_when_process_pool_is_unavailable(tmp_path, monkeypatch) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def useful(value: int) -> int:\n"
        "    if value > 0:\n"
        "        return value + 1\n"
        "    return 0\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "cortex.extensions.mejoralo.scan.ProcessPoolExecutor",
        _ExplodingProcessPool,
    )
    monkeypatch.setattr("cortex.extensions.mejoralo.scan.is_safe_path", lambda path: True)

    result = scan("docs-surface", tmp_path)

    assert result.project == "docs-surface"
    assert result.total_files == 1
    assert result.total_loc > 0
    assert result.dead_code is False
