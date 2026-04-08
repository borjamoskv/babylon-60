from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from cortex.engine.models import Fact
from cortex.extensions.policy.engine import PolicyEngine
from cortex.extensions.policy.models import PolicyConfig


def _fact(*, bridge_kind: str, source: str | None = None, project: str = "alpha") -> Fact:
    return Fact(
        id=1,
        tenant_id="default",
        project=project,
        content="alpha beta gamma",
        fact_type="bridge",
        meta={"bridge_kind": bridge_kind},
        source=source,
    )


def test_bridge_future_value_prefers_relation_over_external_and_system() -> None:
    engine = MagicMock()
    policy = PolicyEngine(engine, PolicyConfig())
    project_index = {
        "alpha": [_fact(bridge_kind="relation")],
        "beta": [_fact(bridge_kind="relation", project="beta")],
        "gamma": [_fact(bridge_kind="relation", project="gamma")],
    }
    project_names_lower = set(project_index.keys())

    relation = policy._compute_future_value(
        _fact(bridge_kind="relation"),
        project_index,
        project_names_lower,
    )
    external = policy._compute_future_value(
        _fact(bridge_kind="external", source="bridge:github"),
        project_index,
        project_names_lower,
    )
    system = policy._compute_future_value(
        _fact(bridge_kind="system", source="agent:apis-omega"),
        project_index,
        project_names_lower,
    )

    assert relation > external > system
