import os
import subprocess
import sys


def _route_flags(*, experimental: bool) -> tuple[bool, bool, bool]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    if experimental:
        env["CORTEX_ENABLE_EXPERIMENTAL_API"] = "1"
    else:
        env.pop("CORTEX_ENABLE_EXPERIMENTAL_API", None)

    code = """
from cortex.api.core import app
paths = {getattr(route, 'path', '') for route in app.routes}
print('/v1/facts' in paths)
print('/v1/ask' in paths)
print('/v1/swarm/status' in paths)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip() in {"True", "False"}]
    return tuple(line == "True" for line in lines[-3:])


def test_operator_routes_are_gated_by_default() -> None:
    facts, ask, swarm = _route_flags(experimental=False)

    assert facts is True
    assert ask is False
    assert swarm is False


def test_operator_routes_mount_when_experimental_api_enabled() -> None:
    facts, ask, swarm = _route_flags(experimental=True)

    assert facts is True
    assert ask is True
    assert swarm is True
