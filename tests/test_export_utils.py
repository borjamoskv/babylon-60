from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO
from typing import Any

import pytest

from cortex.utils.export import export_facts


@dataclass
class FactStub:
    id: int
    project: str
    content: str
    fact_type: str = "knowledge"
    tags: list[str] | None = None
    confidence: str = "C3"
    valid_from: str = "2026-01-01"
    valid_until: str | None = None
    source: str = "agent:test"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "content": self.content,
            "fact_type": self.fact_type,
            "tags": self.tags or [],
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "source": self.source,
            "extra": "ignored-by-csv",
        }


def test_export_facts_json_is_pretty_unicode_json() -> None:
    output = export_facts([FactStub(1, "cortex", "nino")], fmt=" JSON ")

    parsed = json.loads(output)
    assert parsed[0]["content"] == "nino"
    assert "\n  {" in output


def test_export_facts_jsonl_writes_one_object_per_line() -> None:
    output = export_facts(
        [FactStub(1, "a", "alpha"), FactStub(2, "b", "beta")],
        fmt="jsonl",
    )

    lines = output.splitlines()
    assert [json.loads(line)["content"] for line in lines] == ["alpha", "beta"]


def test_export_facts_csv_flattens_tags_and_ignores_extra_fields() -> None:
    output = export_facts([FactStub(1, "cortex", "alpha", tags=["x", "y"])], fmt="csv")
    rows = list(csv.DictReader(StringIO(output)))

    assert rows == [
        {
            "id": "1",
            "project": "cortex",
            "content": "alpha",
            "fact_type": "knowledge",
            "tags": "x;y",
            "confidence": "C3",
            "valid_from": "2026-01-01",
            "valid_until": "",
            "source": "agent:test",
        }
    ]


def test_export_facts_empty_csv_and_notebooklm_are_empty() -> None:
    assert export_facts([], fmt="csv") == ""
    assert export_facts([], fmt="notebooklm") == ""


def test_export_facts_notebooklm_groups_by_project_and_type() -> None:
    output = export_facts(
        [
            FactStub(1, "beta", "rule text", fact_type="rule", tags=["guard"]),
            FactStub(2, "alpha", "decision text", fact_type="decision"),
        ],
        fmt="notebooklm",
    )

    assert output.startswith("# CORTEX Master Digest\n")
    assert output.index("## Domain: ALPHA") < output.index("## Domain: BETA")
    assert "### Decision" in output
    assert "- **rule text** (Confidence: C3) [tags: guard]" in output


def test_export_facts_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_facts([], fmt="xml")
