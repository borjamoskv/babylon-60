# [C5-REAL] Exergy-Maximized

import os
import signal
from unittest.mock import patch

import pytest

from babylon60.security.vesicular_runtime import VesicularRuntime

@pytest.fixture(autouse=True)
def reset_vesicular_runtime():
    """Reset the singleton state and restore original os.environ methods after each test."""
    original_get = os.environ.get
    original_getitem = os.environ.__getitem__
    
    yield
    
    os.environ.get = original_get
    os.environ.__getitem__ = original_getitem
    VesicularRuntime._is_enforced = False


def test_vesicular_runtime_allows_safe_keys():
    VesicularRuntime.enforce()
    
    # Should not raise or kill
    os.environ["SAFE_KEY"] = "value"
    assert os.environ.get("SAFE_KEY") == "value"
    assert os.environ["SAFE_KEY"] == "value"


@patch("os.kill")
@patch("os.getpid", return_value=1234)
def test_vesicular_runtime_kills_on_exact_forbidden(mock_getpid, mock_kill):
    VesicularRuntime.enforce()
    
    os.environ["OPENAI_API_KEY"] = "sk-fake"
    
    os.environ.get("OPENAI_API_KEY")
    
    mock_kill.assert_called_once_with(1234, signal.SIGKILL)


@patch("os.kill")
@patch("os.getpid", return_value=1234)
def test_vesicular_runtime_kills_on_forbidden_suffix(mock_getpid, mock_kill):
    VesicularRuntime.enforce()
    
    os.environ["MY_SERVICE_SECRET"] = "secret"
    
    _ = os.environ["MY_SERVICE_SECRET"]
    
    mock_kill.assert_called_once_with(1234, signal.SIGKILL)


@patch("os.kill")
def test_enforce_idempotency(mock_kill):
    VesicularRuntime.enforce()
    VesicularRuntime.enforce()  # Should not double-patch or error
    
    os.environ["SAFE"] = "yes"
    assert os.environ.get("SAFE") == "yes"
    mock_kill.assert_not_called()
