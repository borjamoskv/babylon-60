from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def mock_local_embedder() -> None:
    """Override the global embedder fixture for low-level crypto regressions."""
    return None
