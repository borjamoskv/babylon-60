from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_cli_reference_matches_current_command_surface() -> None:
    doc = _read("src/content/docs/cli.md")

    required = [
        "cortex status [--json]",
        "cortex list [--project PROJECT] [--type TYPE] [--limit N] [--tenant-id TENANT]",
        "cortex edit FACT_ID NEW_CONTENT [--tenant-id TENANT]",
        "cortex delete FACT_ID [-r TEXT] [--tenant-id TENANT]",
        "cortex compact PROJECT [--strategy dedup|merge_errors|staleness_prune|ttl_prune|drift_check]",
        "cortex handoff generate",
        "cortex handoff load",
        "cortex timeline log",
        "cortex ghost status",
        "cortex swarm up",
        "cortex mejoralo antipatterns",
        "cortex entropy report",
        "cortex purge project PROJECT",
        'cortex reflect PROJECT "Session summary"',
    ]
    for snippet in required:
        assert snippet in doc

    stale = [
        "--json-output",
        "--as-of",
        "cortex episodic",
        "cortex context",
        "cortex autorouter",
        "cortex swarm dispatch",
        "cortex swarm status",
        "cortex ghost resolve",
        "cortex mejoralo fix PATH",
        "cortex entropy dashboard",
        "cortex purge --project PROJECT [--before DATE] [--dry-run]",
        "Analyze current session patterns",
        "Visual temporal memory browsing.",
        "cortex timeline PROJECT [--days N]",
    ]
    for snippet in stale:
        assert snippet not in doc


def test_api_reference_tracks_mounted_public_routes() -> None:
    doc = _read("src/content/docs/api.md")

    for stale in [
        "/v1/trust/guard",
        "/v1/trust/profiles/{agent_id}",
        "/v1/trust/compliance",
        "/v1/agents",
    ]:
        assert stale not in doc

    assert "POST /v1/search" in doc
    assert "GET /v1/search" in doc
    assert "/v1/facts/search" in doc

    from cortex.api.core import app

    paths = {route.path for route in app.routes}
    expected_paths = {
        "/v1/facts",
        "/v1/facts/batch",
        "/v1/projects/{project}/facts",
        "/v1/facts/{fact_id}",
        "/v1/facts/{fact_id}/history",
        "/v1/facts/{fact_id}/chain",
        "/v1/facts/{fact_id}/vote",
        "/v1/facts/{fact_id}/vote-v2",
        "/v1/facts/{fact_id}/votes",
        "/v1/facts/{fact_id}/taint",
        "/v1/facts/verify",
        "/v1/search",
        "/v1/status",
        "/v1/health/deep",
        "/v1/admin/keys",
        "/v1/projects/{project}/export",
        "/v1/daemon/status",
        "/v1/runtime/health",
        "/v1/runtime/boot_recovery",
        "/v1/llm/status",
        "/v1/events/stream",
        "/v1/swarm/status",
        "/v1/swarm/worktrees",
        "/v1/swarm/worktrees/{worktree_id}",
        "/v1/swarm/psychohistory",
        "/v1/ask",
        "/v1/ask/stream",
        "/health",
    }
    missing = expected_paths - paths
    assert not missing, f"Mounted API paths missing from runtime: {sorted(missing)}"


def test_quickstart_rest_examples_match_current_api_contract() -> None:
    doc = _read("src/content/docs/quickstart.md")

    assert "/v1/search" in doc
    assert '"k": 5' in doc
    assert "Authorization: Bearer YOUR_API_KEY" in doc
    assert "python -m webbrowser http://localhost:8484/docs" in doc

    assert "/v1/facts/search" not in doc
    assert '"top_k": 5' not in doc
    assert "open http://localhost:8484/docs" not in doc


def test_audit_and_failure_docs_use_real_verification_commands() -> None:
    audit_pack = _read("src/content/docs/audit_pack_anatomy.md")
    impossible_failures = _read("src/content/docs/impossible-failures.md")

    assert '"verification_command": "cortex verify 42042"' in audit_pack
    assert "cortex verify record" not in audit_pack

    assert "cortex trust-ledger verify" in impossible_failures
    assert "cortex lineage trace 42" in impossible_failures
    assert "cortex verify --full" not in impossible_failures
    assert "cortex lineage --fact-id 42" not in impossible_failures
