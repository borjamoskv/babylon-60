"""Tests for the canonical MCP Toolbox configuration.

Validates flat YAML structure, SQL syntax, and toolset references without
requiring the Toolbox binary. Creates an in-memory SQLite database with
the full CORTEX schema and prepares each tool's statement.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
import yaml

TOOLS_YAML = Path(__file__).resolve().parent.parent / "cortex" / "mcp" / "toolbox" / "tools.yaml"
TOOLBOX_DIR = TOOLS_YAML.parent
PROFILE_TOOL_FILES = {
    "cortex-summary.yaml": {"cortex-stats"},
    "cortex-readonly.yaml": {
        "query-facts",
        "query-ghosts",
        "query-decisions",
        "query-signals",
        "cortex-stats",
    },
    "cortex-graph.yaml": {
        "trace-impact",
        "cluster-signals",
        "ghost-mapping",
    },
}

VALID_TOOL_PARAM_TYPES = {"string", "integer", "float", "boolean"}
EXPECTED_TOOLS = {
    "query-facts",
    "query-ghosts",
    "query-decisions",
    "query-signals",
    "cortex-stats",
    "trace-impact",
    "cluster-signals",
    "ghost-mapping",
}


@pytest.fixture(scope="module")
def config() -> dict:
    """Load and parse the canonical Toolbox config."""
    assert TOOLS_YAML.exists(), f"tools.yaml not found at {TOOLS_YAML}"
    with TOOLS_YAML.open() as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "tools.yaml must parse to a mapping"
    return data


@pytest.fixture(scope="module")
def tools(config: dict) -> dict[str, dict]:
    """Extract tool definitions keyed by name."""
    raw = config.get("tools", {})
    assert isinstance(raw, dict), "tools section must be a mapping"
    return raw


@pytest.fixture(scope="module")
def toolsets(config: dict) -> dict[str, list[str]]:
    """Extract toolset definitions keyed by name."""
    raw = config.get("toolsets", {})
    assert isinstance(raw, dict), "toolsets section must be a mapping"
    return raw


@pytest.fixture(scope="module")
def sources(config: dict) -> dict[str, dict]:
    """Extract source definitions keyed by name."""
    raw = config.get("sources", {})
    assert isinstance(raw, dict), "sources section must be a mapping"
    return raw


@pytest.fixture(scope="module")
def cortex_db() -> sqlite3.Connection:
    """Create in-memory SQLite DB with CORTEX schema for SQL validation."""
    from cortex.database.schema import ALL_SCHEMA

    conn = sqlite3.connect(":memory:")
    for stmt in ALL_SCHEMA:
        try:
            conn.executescript(stmt)
        except sqlite3.OperationalError:
            pass
    return conn


def test_yaml_loads(config: dict) -> None:
    """tools.yaml must parse without errors."""
    assert config


def test_has_source(sources: dict[str, dict]) -> None:
    """The canonical CORTEX SQLite source must be defined."""
    assert "cortex-db" in sources
    assert sources["cortex-db"]["kind"] == "sqlite"
    assert sources["cortex-db"]["database"] == "${CORTEX_DB}"


def test_has_tools(tools: dict[str, dict]) -> None:
    """All expected tools must be defined."""
    assert EXPECTED_TOOLS.issubset(tools.keys()), f"Missing tools: {EXPECTED_TOOLS - set(tools)}"


def test_tool_required_fields(tools: dict[str, dict]) -> None:
    """Every tool must include the required Toolbox fields."""
    for name, tool in tools.items():
        for field in ("kind", "source", "description", "statement"):
            assert field in tool, f"Tool '{name}' missing field '{field}'"


def test_tool_param_types(tools: dict[str, dict]) -> None:
    """All parameter types must be valid."""
    for name, tool in tools.items():
        for param in tool.get("parameters", []):
            assert param["type"] in VALID_TOOL_PARAM_TYPES, (
                f"Tool '{name}' param '{param['name']}' has invalid type '{param['type']}'"
            )


def test_has_toolsets(toolsets: dict[str, list[str]]) -> None:
    """Must expose the expected named toolsets."""
    assert "cortex-readonly" in toolsets
    assert "graph-analysis" in toolsets
    assert "cortex-summary" in toolsets


def test_toolset_membership(toolsets: dict[str, list[str]]) -> None:
    """Readonly and analysis toolsets should stay intentionally scoped."""
    assert toolsets["cortex-readonly"] == [
        "query-facts",
        "query-ghosts",
        "query-decisions",
        "query-signals",
        "cortex-stats",
    ]
    assert toolsets["graph-analysis"] == [
        "trace-impact",
        "cluster-signals",
        "ghost-mapping",
    ]
    assert toolsets["cortex-summary"] == ["cortex-stats"]


def test_toolset_references(tools: dict[str, dict], toolsets: dict[str, list[str]]) -> None:
    """Every tool referenced in a toolset must exist."""
    tool_names = set(tools)
    for toolset_name, refs in toolsets.items():
        for ref in refs:
            assert ref in tool_names, (
                f"Toolset '{toolset_name}' references non-existent tool '{ref}'"
            )


@pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOLS))
def test_sql_prepares(tool_name: str, tools: dict[str, dict], cortex_db: sqlite3.Connection) -> None:
    """Each tool's SQL statement must prepare successfully against the schema."""
    stmt = tools[tool_name]["statement"]
    prepared = stmt.replace("?", "NULL")

    try:
        cortex_db.execute(prepared)
    except sqlite3.OperationalError as exc:
        pytest.fail(f"SQL validation failed for tool '{tool_name}': {exc}\n\nSQL:\n{prepared}")


def test_all_tools_read_only(tools: dict[str, dict]) -> None:
    """No tool statement should contain write operations."""
    write_keywords = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}
    for name, tool in tools.items():
        stmt_upper = tool["statement"].upper()
        for keyword in write_keywords:
            if re.search(rf"\b{keyword}\b", stmt_upper):
                pytest.fail(
                    f"Tool '{name}' contains write keyword '{keyword}' — "
                    "Toolbox tools must be read-only"
                )


@pytest.mark.parametrize(
    ("filename", "expected_tools"),
    sorted(PROFILE_TOOL_FILES.items()),
)
def test_split_toolbox_profiles(filename: str, expected_tools: set[str], cortex_db: sqlite3.Connection) -> None:
    """Profile-specific toolbox entrypoints must expose the expected compact tool sets."""
    path = TOOLBOX_DIR / filename
    assert path.exists(), f"Split toolbox profile missing: {path}"

    with path.open() as fh:
        data = yaml.safe_load(fh)

    assert data["sources"]["cortex-db"]["database"] == "${CORTEX_DB}"
    tools = data["tools"]
    assert set(tools) == expected_tools

    for tool_name, tool in tools.items():
        prepared = tool["statement"].replace("?", "NULL")
        try:
            cortex_db.execute(prepared)
        except sqlite3.OperationalError as exc:
            pytest.fail(
                f"SQL validation failed for split profile '{filename}' tool '{tool_name}': {exc}"
            )
