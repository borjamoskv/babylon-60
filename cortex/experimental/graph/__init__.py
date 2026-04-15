"""Cortex Graph Module.

Entities, Relationships, and Graph Processing.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.experimental.graph.backends import GraphBackend, SQLiteBackend
    from cortex.experimental.graph.engine import (
        detect_relationships,
        extract_entities,
        find_path,
        get_backend,
        get_context_subgraph,
        get_graph,
        get_graph_sync,
        process_fact_graph,
        process_fact_graph_sync,
        query_entity,
        query_entity_sync,
    )
    from cortex.experimental.graph.models import Entity, Ghost, Relationship

__all__ = [
    "Entity",
    "Relationship",
    "Ghost",
    "GraphBackend",
    "SQLiteBackend",
    "extract_entities",
    "detect_relationships",
    "process_fact_graph",
    "process_fact_graph_sync",
    "get_graph",
    "get_graph_sync",
    "query_entity",
    "query_entity_sync",
    "find_path",
    "get_context_subgraph",
    "get_backend",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Entity": ("cortex.experimental.graph.models", "Entity"),
    "Relationship": ("cortex.experimental.graph.models", "Relationship"),
    "Ghost": ("cortex.experimental.graph.models", "Ghost"),
    "GraphBackend": ("cortex.experimental.graph.backends", "GraphBackend"),
    "SQLiteBackend": ("cortex.experimental.graph.backends", "SQLiteBackend"),
    "extract_entities": ("cortex.experimental.graph.engine", "extract_entities"),
    "detect_relationships": ("cortex.experimental.graph.engine", "detect_relationships"),
    "process_fact_graph": ("cortex.experimental.graph.engine", "process_fact_graph"),
    "process_fact_graph_sync": ("cortex.experimental.graph.engine", "process_fact_graph_sync"),
    "get_graph": ("cortex.experimental.graph.engine", "get_graph"),
    "get_graph_sync": ("cortex.experimental.graph.engine", "get_graph_sync"),
    "query_entity": ("cortex.experimental.graph.engine", "query_entity"),
    "query_entity_sync": ("cortex.experimental.graph.engine", "query_entity_sync"),
    "find_path": ("cortex.experimental.graph.engine", "find_path"),
    "get_context_subgraph": ("cortex.experimental.graph.engine", "get_context_subgraph"),
    "get_backend": ("cortex.experimental.graph.engine", "get_backend"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.graph' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
