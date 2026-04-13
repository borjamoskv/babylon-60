from pathlib import Path


def test_api_surface_docs_point_to_ledger_verify():
    doc = Path("docs/ortu-omega/API-SURFACE.md").read_text(encoding="utf-8")

    assert "/v1/ledger/verify" in doc
    assert "/v1/trust/verify" not in doc
    assert "/v1/projects/{project}/facts" in doc
    assert "DELETE` | `/v1/facts/{id}" in doc
    assert "/v1/facts/{id}/chain" in doc
    assert "/v1/facts/recall" not in doc
    assert "/v1/facts/{id}/deprecate" not in doc
    assert "/v1/facts/{id}/trace" not in doc
    assert "/v1/facts/{id}/consensus" not in doc
    assert "class CortexMemory:" not in doc
