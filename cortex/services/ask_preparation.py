from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AskPreparation:
    """Prepared RAG payload shared by sync and streaming ask endpoints."""

    results: list[Any]
    prompt: str
    system: str


class AskSearchEngine(Protocol):
    """Minimal search surface needed by the ask preparation workflow."""

    async def search(
        self,
        query: str,
        tenant_id: str = "default",
        top_k: int = 5,
        project: str | None = None,
        **kwargs: Any,
    ) -> list[Any]: ...


def build_facts_context(results: list[Any]) -> str:
    """Render retrieved facts into the grounded context block expected by the LLM."""

    if not results:
        return "(No facts found matching the query.)"

    return "\n\n".join(
        f"[Fact #{result.fact_id}] (project: {result.project}, score: {result.score:.3f})\n"
        f"{result.content}"
        for result in results
    )


def build_ask_prompt(*, context: str, query: str) -> str:
    """Build the canonical grounded prompt for ask routes."""

    return (
        "## Retrieved Facts from CORTEX Memory\n\n"
        f"{context}\n\n"
        "## Question\n\n"
        f"{query}\n\n"
        "## Instructions\n\n"
        "Answer the question above using ONLY the facts provided. "
        "Cite [Fact #ID] when referencing specific facts."
    )


async def prepare_ask_request(
    *,
    engine: AskSearchEngine,
    query: str,
    tenant_id: str,
    top_k: int,
    project: str | None,
    system_prompt: str | None,
    default_system_prompt: str,
) -> AskPreparation:
    """Resolve search results plus the shared prompt state for ask endpoints."""

    results = await engine.search(
        query=query,
        top_k=top_k,
        project=project,
        tenant_id=tenant_id,
    )
    context = build_facts_context(results)
    system = system_prompt or default_system_prompt
    prompt = build_ask_prompt(context=context, query=query)
    return AskPreparation(results=results, prompt=prompt, system=system)
