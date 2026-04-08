from __future__ import annotations

import ast
import textwrap

from cortex.extensions.mejoralo.swarm import MejoraloSwarm


def test_extract_infected_node_prefers_innermost_enclosing_definition() -> None:
    source = textwrap.dedent(
        """
        def outer():
            def inner():
                return 42
            return inner()
        """
    )

    extracted = MejoraloSwarm._extract_infected_node(source, target_line=3)

    assert extracted is not None
    node, node_source = extracted
    assert node.name == "inner"
    parsed = ast.parse(node_source)
    top_level = [n for n in ast.iter_child_nodes(parsed) if isinstance(n, ast.FunctionDef)]
    assert len(top_level) == 1
    assert top_level[0].name == "inner"
