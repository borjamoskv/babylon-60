from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.extensions.scraper.models import ScrapeRequest, validate_public_scrape_url
from cortex.routes.scraper import router


def _client(auth_result: AuthResult | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    if auth_result is not None:
        app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def test_validate_public_scrape_url_rejects_loopback() -> None:
    try:
        validate_public_scrape_url("http://127.0.0.1/admin")
    except ValueError as exc:
        assert "Local and private network targets are not allowed" in str(exc)
    else:
        raise AssertionError("Expected localhost URL to be rejected")


def test_scrape_request_normalizes_public_url() -> None:
    request = ScrapeRequest(url="example.com")
    assert request.url == "https://example.com"


def test_scraper_routes_require_auth() -> None:
    client = _client()

    response = client.post("/api/scraper/scrape", json={"url": "https://example.com"})

    assert response.status_code == 401


def test_scraper_route_rejects_private_target_with_auth() -> None:
    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-scrape",
            permissions=["read"],
            key_name="scraper-key",
        )
    )

    response = client.post("/api/scraper/scrape", json={"url": "http://localhost:8080/private"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Local and private network targets are not allowed"
