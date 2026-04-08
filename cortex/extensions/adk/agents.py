"""CORTEX ADK Agents — Sovereign AI Agent Definitions.

Defines multi-agent architecture using Google ADK:
- cortex_memory_agent: Root agent for memory operations
- cortex_analyst_agent: Cross-source analysis sub-agent
- cortex_guardian_agent: Ledger integrity and security sub-agent

Requires: pip install google-adk
"""

from __future__ import annotations

import logging
import os
import re
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any, Optional

__all__ = [
    "create_google_one_agent",
    "create_cortex_swarm",
    "create_analyst_agent",
    "create_domain_agent",
    "create_guardian_agent",
    "create_memory_agent",
    "is_adk_available",
    "resolve_domain_agents",
]

logger = logging.getLogger("cortex.extensions.adk.agents")

_ADK_INSTALL_MSG = "Google ADK not installed. Install with: pip install google-adk"

if TYPE_CHECKING:
    from google.adk.agents.llm_agent import Agent
else:
    Agent = Any  # type: ignore[misc,assignment]

_ADK_AVAILABLE = find_spec("google.adk") is not None


def _require_agent_class() -> type[Agent]:
    """Import the ADK agent lazily to avoid import-time warnings/side effects."""
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)

    try:
        from google.adk.agents.llm_agent import (
            Agent as adk_agent,  # pyright: ignore[reportMissingImports]
        )
    except ImportError as exc:
        logger.debug(_ADK_INSTALL_MSG)
        raise ImportError(_ADK_INSTALL_MSG) from exc

    return adk_agent


def is_adk_available() -> bool:
    """Check if Google ADK is installed."""
    return _ADK_AVAILABLE


# ─── Agent Definitions ────────────────────────────────────────────────

_DEFAULT_MODEL = os.environ.get("CORTEX_ADK_MODEL", "gemini-2.0-flash")

_DEFAULT_DOMAIN_FAMILIES = [
    "facts",
    "ledger",
    "ingestion",
    "search",
    "routing",
    "consensus",
    "policy",
    "security",
    "compliance",
    "observability",
    "telemetry",
    "daemon",
    "sync",
    "api",
    "cli",
    "gateway",
    "docs",
    "testing",
    "deployment",
    "storage",
    "memory",
    "engine",
    "runtime",
]

_DEFAULT_DOMAIN_ROLES = [
    "orchestrator",
    "ingestor",
    "retriever",
    "writer",
    "auditor",
    "guardian",
    "planner",
    "worker",
    "cache",
    "watcher",
]


def _build_default_domain_agents() -> list[str]:
    """Synthesize the default 230-agent specialist pack.

    The default swarm is generated from repository-relevant families and a
    fixed set of operational roles so the size is easy to reason about and the
    order remains deterministic.
    """
    return [
        f"{family}_{role}"
        for family in _DEFAULT_DOMAIN_FAMILIES
        for role in _DEFAULT_DOMAIN_ROLES
    ]


_DEFAULT_DOMAIN_AGENTS = _build_default_domain_agents()


def _slugify_domain(domain: str) -> str:
    """Normalize a user-provided domain name into an ADK-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", domain.strip().lower()).strip("_")
    if not slug:
        raise ValueError("Domain agent name cannot be empty")
    return slug


def resolve_domain_agents(domain_agents: Optional[list[str]] = None) -> list[str]:
    """Resolve specialist domain agents from explicit input or environment.

    Domains are normalized to lowercase snake_case and deduplicated while
    preserving order. If ``domain_agents`` is ``None``, the value is loaded
    from ``CORTEX_ADK_DOMAIN_AGENTS`` as a comma-separated list. When the
    environment variable is unset, a default 230-agent specialist pack is used
    so the sovereign swarm scales out without extra configuration.
    """
    raw_domains = domain_agents
    if raw_domains is None:
        env_value = os.environ.get("CORTEX_ADK_DOMAIN_AGENTS")
        if env_value is None:
            raw_domains = list(_DEFAULT_DOMAIN_AGENTS)
        else:
            raw_domains = [part.strip() for part in env_value.split(",") if part.strip()]

    resolved: list[str] = []
    seen: set[str] = set()
    for domain in raw_domains:
        slug = _slugify_domain(domain)
        if slug not in seen:
            seen.add(slug)
            resolved.append(slug)
    return resolved


def _format_domain_label(domain_slug: str) -> str:
    return domain_slug.replace("_", " ").title()


def _summarize_specialists(names: list[str]) -> str:
    if not names:
        return "no additional specialist agents"

    if len(names) <= 6:
        return ", ".join(names)

    remaining = len(names) - 6
    return ", ".join(names[:6]) + f", and {remaining} more"


def create_memory_agent(
    model: Optional[str] = None,
    extra_tools: Optional[list] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create the CORTEX Memory Agent — root agent for sovereign memory ops.

    This agent can store facts, search memory, check system status,
    and verify ledger integrity. It's the primary entry point for
    all CORTEX memory operations.

    Args:
        model: LLM model to use (default: gemini-2.0-flash).
        extra_tools: Additional tools to register alongside CORTEX tools.

    Returns:
        Configured ADK Agent instance.

    Raises:
        ImportError: If google-adk is not installed.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    from cortex.adk.tools import ALL_TOOLS

    tools = list(ALL_TOOLS)
    if extra_tools:
        tools.extend(extra_tools)

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name="cortex_memory_agent",
        description=(
            "Sovereign memory agent for CORTEX. Stores, searches, and verifies "
            "facts across projects using hybrid semantic + text search and a "
            "cryptographically chained transaction ledger."
        ),
        instruction=(
            "You are the CORTEX Memory Agent — the sovereign guardian of "
            "persistent AI memory. Your responsibilities:\n\n"
            "1. **Store facts** — Use `adk_store` to persist decisions, errors, "
            "knowledge, ghosts, and bridges across projects.\n"
            "2. **Search memory** — Use `adk_search` for hybrid semantic + text "
            "retrieval. Always specify project when possible.\n"
            "3. **Deprecate facts** — Use `adk_deprecate` to retire obsolete or "
            "incorrect facts. Always provide a reason.\n"
            "4. **Monitor health** — Use `adk_status` to check system metrics.\n"
            "5. **Verify integrity** — Use `adk_ledger_verify` to audit the "
            "immutable transaction ledger.\n\n"
            "Rules:\n"
            "- Always confirm what was stored/found with the user.\n"
            "- Use fact_type accurately (knowledge, decision, error, ghost, etc).\n"
            "- Include relevant tags for discoverability.\n"
            "- Report ledger violations immediately.\n"
            "- Respond in the same language the user writes in."
        ),
        tools=tools,
    )


def create_analyst_agent(
    model: Optional[str] = None,
    toolbox_tools: Optional[list] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create the CORTEX Analyst Agent — cross-source analysis sub-agent.

    Combines CORTEX search with optional external database tools
    (via MCP Toolbox) for cross-source intelligence analysis.

    Args:
        model: LLM model to use.
        toolbox_tools: Additional Toolbox bridge tools for external DBs.

    Returns:
        Configured ADK Agent instance.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    from cortex.adk.tools import adk_search, adk_status

    tools: list = [adk_search, adk_status]
    if toolbox_tools:
        tools.extend(toolbox_tools)

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name="cortex_analyst_agent",
        description=(
            "Cross-source analyst that combines CORTEX memory search with "
            "external database queries for comprehensive intelligence analysis."
        ),
        instruction=(
            "You are the CORTEX Analyst — a cross-source intelligence engine.\n\n"
            "Your job is to find patterns across CORTEX memory AND external "
            "databases when available. When answering queries:\n"
            "1. Search CORTEX memory first for internal context.\n"
            "2. Query external databases if Toolbox tools are available.\n"
            "3. Synthesize findings into actionable intelligence.\n"
            "4. Always cite your sources (CORTEX fact IDs, external DB tables).\n"
            "5. Flag contradictions between internal memory and external data."
        ),
        tools=tools,
    )


def create_guardian_agent(
    model: Optional[str] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create the CORTEX Guardian Agent — security and integrity sub-agent.

    Focused on ledger verification, integrity audits, and system
    health monitoring.

    Args:
        model: LLM model to use.

    Returns:
        Configured ADK Agent instance.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    from cortex.adk.tools import adk_ledger_verify, adk_status

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name="cortex_guardian_agent",
        description=(
            "Security and integrity guardian that monitors CORTEX ledger "
            "health, detects violations, and audits system state."
        ),
        instruction=(
            "You are the CORTEX Guardian — the sovereign security monitor.\n\n"
            "Your responsibilities:\n"
            "1. **Verify ledger integrity** — Run `adk_ledger_verify` to check "
            "the transaction chain for tampering.\n"
            "2. **Monitor system health** — Check `adk_status` for anomalies.\n"
            "3. **Report findings** — Always report violations with severity:\n"
            "   - 🔴 CRITICAL: Hash chain broken, data tampered\n"
            "   - 🟡 WARNING: Unusual patterns, high error rates\n"
            "   - 🟢 OK: System healthy, ledger intact\n"
            "4. **Recommend actions** — Suggest remediation for issues found."
        ),
        tools=[adk_ledger_verify, adk_status],
    )


def create_google_one_agent(
    model: Optional[str] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create the Google One Agent — cloud integration and backup sub-agent.

    Focused on Google Drive sync, NotebookLM exports, and sovereign
    cloud backups in Google One.

    Args:
        model: LLM model to use.

    Returns:
        Configured ADK Agent instance.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    from cortex.extensions.adk.goog_tools import GOOGLE_ONE_TOOLS

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name="cortex_google_one_agent",
        description=(
            "Cloud integration agent that manages Google One storage, Drive sync, "
            "and secure CORTEX memory backups."
        ),
        instruction=(
            "You are the CORTEX Google One Agent — the sovereign link to the cloud.\n\n"
            "Your responsibilities:\n"
            "1. **Monitor storage** — Run `goog_quota` to check Drive and Google One capacity.\n"
            "2. **Sync NotebookLM** — Use `goog_sync_notebooklm` to push knowledge to Drive.\n"
            "3. **Sovereign Backup** — Run `goog_backup_cortex` to secure CORTEX data.\n"
            "4. **Manage sync lag** — Report if fragments or digests are stale.\n\n"
            "Rules:\n"
            "- Always confirm sync success and report quota levels.\n"
            "- If sync fails, suggest checking the Google Drive for Desktop connection.\n"
            "- Treat backups as high-priority security events."
        ),
        tools=GOOGLE_ONE_TOOLS,
    )


def create_domain_agent(
    domain: str,
    model: Optional[str] = None,
    toolbox_tools: Optional[list] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create a specialist domain agent that can scale the swarm by topic.

    Domain agents are lightweight, configurable specialists that inherit the
    same search and health tools as the analyst agent, but with domain-specific
    instructions and a stable name derived from the supplied domain.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    from cortex.adk.tools import adk_search, adk_status

    domain_slug = _slugify_domain(domain)
    domain_label = _format_domain_label(domain_slug)

    tools: list = [adk_search, adk_status]
    if toolbox_tools:
        tools.extend(toolbox_tools)

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name=f"cortex_domain_{domain_slug}_agent",
        description=(
            f"Specialist CORTEX agent for the {domain_label} domain. "
            "Used to scale the swarm horizontally with domain-specific routing "
            "and evidence-backed responses."
        ),
        instruction=(
            f"You are the CORTEX {domain_label} Specialist.\n\n"
            "Your job is to handle requests for your domain when the root "
            "orchestrator routes them to you. Use memory search and health "
            "checks first, then apply any extra tools that match the task.\n\n"
            "Rules:\n"
            "- Stay narrowly focused on your domain.\n"
            "- Cite the evidence you used.\n"
            "- Escalate ledger, security, or cross-domain uncertainty to the "
            "root Sovereign or Guardian agents."
        ),
        tools=tools,
    )


# ─── Multi-Agent Orchestrator ─────────────────────────────────────────


def create_cortex_swarm(
    model: Optional[str] = None,
    toolbox_tools: Optional[list] = None,
    domain_agents: Optional[list[str]] = None,
    extra_sub_agents: Optional[list[Any]] = None,
) -> Agent:  # type: ignore[reportInvalidTypeForm]
    """Create the full CORTEX agent swarm — multi-agent system.

    Returns a root agent that can delegate to specialized sub-agents:
    - Memory Agent for store/search ops
    - Analyst Agent for cross-source analysis
    - Guardian Agent for security audits
    - Google One Agent for cloud integration
    - Optional domain specialists from config or explicit input
    - Default 230-specialist pack when no explicit domain list is provided

    Args:
        model: LLM model for all agents.
        toolbox_tools: External DB tools for the analyst agent.
        domain_agents: Optional list of extra specialist domain names.
        extra_sub_agents: Optional list of already constructed Agent objects.

    Returns:
        Root Agent with sub-agent delegation.
    """
    if not _ADK_AVAILABLE:
        raise ImportError(_ADK_INSTALL_MSG)
    agent_cls = _require_agent_class()

    memory = create_memory_agent(model=model)
    analyst = create_analyst_agent(model=model, toolbox_tools=toolbox_tools)
    guardian = create_guardian_agent(model=model)
    google_one = create_google_one_agent(model=model)
    resolved_domains = resolve_domain_agents(domain_agents)
    domain_specialists = [
        create_domain_agent(domain=domain, model=model, toolbox_tools=toolbox_tools)
        for domain in resolved_domains
    ]
    sub_agents: list[Any] = [memory, analyst, guardian, google_one]
    sub_agents.extend(domain_specialists)
    if extra_sub_agents:
        sub_agents.extend(agent for agent in extra_sub_agents if agent is not None)

    specialist_names = [
        getattr(agent, "name", "custom_agent")
        for agent in (*domain_specialists, *(extra_sub_agents or []))
        if agent is not None
    ]
    specialist_summary = _summarize_specialists(specialist_names)

    return agent_cls(
        model=model or _DEFAULT_MODEL,
        name="cortex_sovereign",
        description=(
            "CORTEX Sovereign — the root orchestrator that coordinates memory, "
            "analysis, security, cloud, and specialist domain agents for "
            "comprehensive AI memory management."
        ),
        instruction=(
            "You are the CORTEX Sovereign — the root orchestrator of a "
            "multi-agent system for AI memory management.\n\n"
            "You coordinate four specialized agents:\n"
            "- **cortex_memory_agent**: For storing and searching facts\n"
            "- **cortex_analyst_agent**: For cross-source analysis\n"
            "- **cortex_guardian_agent**: For security and integrity audits\n"
            "- **cortex_google_one_agent**: For storage quota, sync, and cloud backups\n"
            f"- **Configured specialists**: {specialist_summary}\n\n"
            "Route requests to the appropriate agent based on the user's intent. "
            "For complex queries, coordinate multiple agents and route to any "
            "configured specialist agents when their domain matches the request. "
            "Always report results clearly and respond in the user's language."
        ),
        sub_agents=sub_agents,
    )
