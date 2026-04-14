from __future__ import annotations

import pytest

from cortex.storage import StorageMode, get_storage_mode


def test_get_storage_mode_defaults_to_local_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORTEX_STORAGE", raising=False)

    assert get_storage_mode() is StorageMode.LOCAL


def test_get_storage_mode_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "definitely-not-a-backend")

    with pytest.raises(ValueError, match="Unknown CORTEX_STORAGE='definitely-not-a-backend'"):
        get_storage_mode()
