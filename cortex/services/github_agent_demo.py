"""Shared one-shot harness for running the GitHubAgent against the current repository."""

from __future__ import annotations

from typing import Any

from cortex.services.github_agent_session import GitHubAgentSession

__all__ = ["build_github_agent_payload", "run_github_agent_demo"]


def build_github_agent_payload(
    *,
    op: str,
    remote: str = "origin",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a TASK_REQUEST payload for the GitHubAgent, dropping null values."""
    payload: dict[str, Any] = {
        "op": op,
        "remote": remote,
    }
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, bool) and not value:
            continue
        payload[key] = value
    return payload


async def run_github_agent_demo(
    payload: dict[str, Any],
    *,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Run GitHubAgent once and return its reply payload."""
    async with GitHubAgentSession(caller_id="demo-caller") as session:
        return await session.request(payload, timeout=timeout)
