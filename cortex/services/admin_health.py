from __future__ import annotations

from collections.abc import Callable
from typing import Any

from starlette.concurrency import run_in_threadpool

from cortex.types.models import DeepHealthResponse, HealthCheckDetail

HealthProbe = Callable[[], tuple[str, bool, dict[str, Any]]]


async def execute_health_probes(
    probes: dict[str, HealthProbe],
) -> tuple[dict[str, HealthCheckDetail], bool]:
    """Run deep-health probes off the event loop and normalize their output."""

    def _run_probes() -> tuple[dict[str, HealthCheckDetail], bool]:
        checks: dict[str, HealthCheckDetail] = {}
        overall_healthy = True
        for name, probe in probes.items():
            try:
                status, ok, details = probe()
            except AttributeError:
                status, ok, details = (
                    "unavailable",
                    True,
                    {"detail": f"{name} not configured"},
                )
            except (OSError, RuntimeError, ValueError) as exc:
                status, ok, details = (
                    "error",
                    False,
                    {"detail": str(exc)},
                )
            overall_healthy = overall_healthy and ok
            checks[name] = HealthCheckDetail.model_validate(
                {
                    "status": status,
                    **details,
                }
            )
        return checks, overall_healthy

    return await run_in_threadpool(_run_probes)


def build_deep_health_response(
    *,
    overall_healthy: bool,
    version: str,
    schema_version: str,
    checks: dict[str, HealthCheckDetail],
    latency_ms: float,
    p95_latency_ms: float | None,
) -> DeepHealthResponse:
    """Build the route response model for the deep health endpoint."""

    return DeepHealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version=version,
        schema_version=schema_version,
        checks=checks,
        latency_ms=latency_ms,
        p95_latency_ms=p95_latency_ms,
        stale_ratio=None,
    )
