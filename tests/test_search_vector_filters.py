from __future__ import annotations

from cortex.search.vector import _build_semantic_query


def test_build_semantic_query_includes_fact_type_and_tags_filters() -> None:
    sql, params = _build_semantic_query(
        tenant_id="tenant-a",
        embedding_json="[0.1, 0.2]",
        top_k=5,
        project="alpha",
        as_of=None,
        fact_type="decision",
        tags=["policy", "edge"],
        confidence=None,
    )

    assert "f.project = ?" in sql
    assert "f.valid_until IS NULL" in sql
    assert "f.fact_type = ?" in sql
    assert sql.count("json_extract(f.tags, '$') LIKE ?") == 2
    assert params == [
        "tenant-a",
        "[0.1, 0.2]",
        15,
        "alpha",
        "decision",
        "%policy%",
        "%edge%",
    ]
