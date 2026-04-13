import sys
import types

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

module = types.ModuleType("cortex.vsa_engine")
module.VSAEngine = object
sys.modules.setdefault("cortex.vsa_engine", module)

from cortex.api.core import app


def test_legacy_memories_surface_is_only_redirect():
    memory_paths = {
        route.path for route in app.routes if isinstance(route, APIRoute) and route.path.startswith("/v1/memories")
    }

    assert memory_paths == {"/v1/memories/{path:path}"}


def test_legacy_memories_search_redirects_to_facts():
    client = TestClient(app)

    response = client.post("/v1/memories/search", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].endswith("/v1/facts/search")
