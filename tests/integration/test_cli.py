import sys
import subprocess

def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "cortex.integration.cli", "--help"], capture_output=True, text=True)
    assert "emit" in result.stdout
    assert "snapshot" in result.stdout
    assert "bridge" in result.stdout
    assert "verify" in result.stdout
