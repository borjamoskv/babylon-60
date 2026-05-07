from __future__ import annotations

import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.middleware import SecurityFraudMiddleware, TracingMiddleware


def test_firewall_signature_redacts_user_agent_payload() -> None:
    middleware = SecurityFraudMiddleware(FastAPI())
    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/v1/facts"),
        headers={
            "user-agent": (
                "scanner Bearer ctx_supersecretfirewalltoken "
                "alice@example.com /Users/example/private/request.txt"
            )
        },
    )
    response = SimpleNamespace(status_code=401)

    middleware._log_security_event(request, response, "203.0.113.10")

    event = json.loads(middleware._buffer[-1])
    payload = event["payload"]
    assert "ctx_supersecretfirewalltoken" not in payload
    assert "alice@example.com" not in payload
    assert "/Users/example" not in payload
    assert "[REDACTED_TOKEN]" in payload
    assert "[REDACTED_PATH]" in payload


def test_tracing_middleware_redacts_exception_log(caplog) -> None:
    app = FastAPI()
    app.add_middleware(TracingMiddleware)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(
            "token=ctx_supersecrettracingtoken "
            "alice@example.com /Users/example/private/error.log"
        )

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        response = TestClient(app).get("/boom")

    assert response.status_code == 500
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "ctx_supersecrettracingtoken" not in log_text
    assert "alice@example.com" not in log_text
    assert "/Users/example" not in log_text
    assert "[REDACTED_TOKEN]" in log_text
    assert "[REDACTED_PATH]" in log_text
