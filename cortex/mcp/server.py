"""MCP Server Implementation.

Core logic for the CORTEX MCP Trust Server.
Provides memory, search, and EU AI Act compliance tools.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from cortex.engine import CortexEngine
from cortex.extensions.immune.filters.base import Verdict
from cortex.extensions.immune.membrane import ImmuneMembrane
from cortex.ledger import SovereignLedger
from cortex.mcp.core_tools import (
    _register_embed_status_tool,
    _register_embed_tool,
    _register_handoff_tool,
    _register_shannon_report_tool,
    _register_trace_chain_tool,
    _register_trace_episode_tool,
)
from cortex.mcp.genesis_tools import register_genesis_tools
from cortex.mcp.guard import MCPGuard
from cortex.mcp.health_tools import register_health_tools
from cortex.mcp.mega_tools import register_mega_tools
from cortex.mcp.scraper_tools import register_scraper_tools
from cortex.mcp.trust_tools import register_trust_tools
from cortex.mcp.utils import AsyncConnectionPool, MCPMetrics, MCPServerConfig, SimpleAsyncCache

__all__ = [
    "MCP_PROFILE_TOOL_NAMES",
    "VALID_MCP_TOOL_PROFILES",
    "create_mcp_server",
    "get_profile_tool_names",
    "run_server",
]

logger = logging.getLogger("cortex.mcp.server")

_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP as _FastMCP

    _MCP_AVAILABLE = True
    FastMCP = _FastMCP
except ImportError:
    FastMCP = None  # type: ignore
    logger.debug("MCP SDK not installed. Install with: pip install 'cortex-persist[mcp]'")

VALID_MCP_TOOL_PROFILES = ("core", "trust", "ops", "media", "research")

MCP_PROFILE_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    "core": (
        "cortex_store",
        "cortex_search",
        "cortex_status",
        "cortex_ledger_verify",
        "cortex_trace_episode",
        "cortex_trace_chain",
        "cortex_shannon_report",
        "cortex_handoff",
        "cortex_embed",
        "cortex_embed_status",
    ),
    "trust": (
        "cortex_audit_trail",
        "cortex_verify_fact",
        "cortex_compliance_report",
        "cortex_decision_lineage",
        "cortex_health_check",
        "cortex_health_report",
    ),
    "ops": (
        "cortex_reality_weaver",
        "cortex_entropy_cracker",
        "cortex_temporal_nexus",
        "cortex_genesis_create",
        "cortex_genesis_preview",
        "cortex_genesis_templates",
        "cortex_genesis_specs",
        "cortex_scrape",
        "cortex_scrape_batch",
        "cortex_scrape_map",
    ),
    "media": (
        "music_create_album",
        "music_generate_track",
        "music_evaluate_gri",
        "suno_generate_headless",
    ),
    "research": ("cortex_hilbert_omega",),
}


def _normalize_tool_profile(tool_profile: str) -> str:
    profile = (tool_profile or "core").strip().lower()
    if profile not in VALID_MCP_TOOL_PROFILES:
        valid = ", ".join(VALID_MCP_TOOL_PROFILES)
        raise ValueError(f"Unknown MCP tool profile '{tool_profile}'. Expected one of: {valid}")
    return profile


def get_profile_tool_names(tool_profile: str) -> tuple[str, ...]:
    """Return the deterministic tool-name snapshot for a profile."""
    return MCP_PROFILE_TOOL_NAMES[_normalize_tool_profile(tool_profile)]


# ─── Server Context ──────────────────────────────────────────────────


class _MCPContext:
    """Encapsulates the shared state for an MCP server instance.

    Replaces the old ``_state`` dict anti-pattern with a proper class
    that owns its lifecycle.
    """

    __slots__ = ("cfg", "metrics", "executor", "pool", "search_cache", "_initialized", "membrane")

    def __init__(self, cfg: MCPServerConfig) -> None:
        self.cfg = cfg
        self.metrics = MCPMetrics()
        self.executor = ThreadPoolExecutor(max_workers=cfg.max_workers)
        self.pool = AsyncConnectionPool(cfg.db_path, max_connections=cfg.max_workers)
        self.search_cache = SimpleAsyncCache(maxsize=cfg.query_cache_size)
        self.membrane = ImmuneMembrane()
        self._initialized = False

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.pool.initialize()
            self._initialized = True


# ─── Tool Registrators ───────────────────────────────────────────────


def _register_store_tool(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_store`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_store(
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
        parent_decision_id: int = 0,
    ) -> str:
        """Store a fact in CORTEX memory.

        Args:
            parent_decision_id: Causal link to parent fact (0 = auto-resolve).
        """
        await ctx.ensure_ready()

        try:
            parsed_tags = json.loads(tags) if tags else []
        except (json.JSONDecodeError, TypeError):
            parsed_tags = []

        try:
            MCPGuard.validate_store(project, content, fact_type, parsed_tags)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected store: %s", e)
            return f"❌ Rejected by Guard: {e}"

        # Immune Membrane Interception (Ω₃ Byzantine Default)
        intent_payload = f"Store Fact [{fact_type}]: {content}"
        context_payload = {
            "project": project,
            "tags": parsed_tags,
            "source": source,
        }
        triage = await ctx.membrane.intercept(
            intent_payload,
            context_payload,
        )

        if triage.verdict != Verdict.PASS:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "Immune Membrane rejected store: %s",
                triage.risks_assumed,
            )
            return f"❌ Rejected by Immune System ({triage.verdict.value}): {triage.risks_assumed}"

        # Normalize parent_decision_id: 0 means None (auto-resolve)
        parent_id = parent_decision_id if parent_decision_id > 0 else None

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            fact_id = await engine.store(
                project,
                content,
                fact_type,
                parsed_tags,
                "stated",
                source or None,
                parent_decision_id=parent_id,
            )

        ctx.metrics.record_request()
        ctx.search_cache.clear()
        return f"✓ Stored fact #{fact_id} in project '{project}'"


def _register_search_tool(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_search`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_search(
        query: str,
        project: str = "",
        top_k: int = 5,
    ) -> str:
        """Search CORTEX memory using semantic + text hybrid search."""
        await ctx.ensure_ready()

        try:
            MCPGuard.validate_search(query)
        except ValueError as e:
            ctx.metrics.record_error()
            logger.warning("MCP Guard rejected search: %s", e)
            return f"❌ Rejected by Guard: {e}"

        # 1. Immune Membrane Interception (Ω₃)
        context = {
            "source": "mcp_search",
            "project": project or "global",
            "is_external_source": True,  # MCP calls are effectively external
            "complexity_added": 1.0,  # Minimal entropy added by a read
            "complexity_removed": 0.0,
            "query_length": len(query),
        }

        # For search, we might want to flag highly adversarial-looking queries
        # even before the DB is hit.
        triage = await ctx.membrane.intercept(query, context)

        if triage.verdict == Verdict.BLOCK:
            ctx.metrics.record_error(is_immune_rejection=True)
            logger.warning(
                "MCP Immune System rejected search: %s\nRisks: %s", query, triage.risks_assumed
            )
            return f"❌ Rejected by Immune System (Ω₃): {', '.join(triage.risks_assumed)}"
        elif triage.verdict == Verdict.HOLD:
            # We can allow HOLD for search, but log it
            logger.info("Search passed with HOLD warnings: %s", triage.risks_assumed)

        cache_key = f"{query}:{project}:{top_k}"
        cached_result = ctx.search_cache.get(cache_key)
        if cached_result:
            ctx.metrics.record_request(cached=True)
            return cached_result

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn

            results = await engine.search(
                query,
                project or None,  # type: ignore[reportArgumentType]
                min(max(top_k, 1), 20),  # type: ignore[reportArgumentType]
            )

        if not results:
            ctx.search_cache.set(cache_key, "No results found.")
            return "No results found."

        ctx.metrics.record_request()
        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(
                f"[#{r.fact_id}] (score: {r.score:.3f}) [{r.project}/{r.fact_type}]\n{r.content}\n"  # type: ignore[reportAttributeAccessIssue]
            )

        output = "\n".join(lines)
        ctx.search_cache.set(cache_key, output)
        return output


def _register_status_tool(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_status`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_status() -> str:
        """Get CORTEX system status and metrics."""
        await ctx.ensure_ready()

        async with ctx.pool.acquire() as conn:
            engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
            engine._conn = conn
            stats = await engine.stats()

        m_summary = ctx.metrics.get_summary()
        return (
            f"CORTEX Status (Optimized v2):\n"
            f"  Facts: {stats.get('total_facts', 0)} total, "
            f"{stats.get('active_facts', 0)} active\n"
            f"  Projects: {stats.get('project_count', 0)}\n"
            f"  Fact Types: {json.dumps(stats.get('types', {}))}\n"
            f"  DB Size: {stats.get('db_size_mb', 0):.1f} MB\n"
            f"  MCP Metrics: {json.dumps(m_summary, indent=2)}"
        )


def _register_ledger_tool(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the ``cortex_ledger_verify`` tool on *mcp*."""

    @mcp.tool()
    async def cortex_ledger_verify() -> str:
        """Perform a full integrity check on the CORTEX ledger."""
        await ctx.ensure_ready()

        # SovereignLedger expects a pool, not a single connection
        ledger = SovereignLedger(ctx.pool)  # type: ignore[reportArgumentType]
        verification = await ledger.audit_integrity()

        if verification["valid"]:
            return (
                f"✅ Ledger Integrity: OK\n"
                f"Transactions verified: {verification['tx_checked']}\n"
                f"Roots checked: {verification['roots_checked']}"
            )
        return (
            f"❌ Ledger Integrity: VIOLATION\n"
            f"Violations: {json.dumps(verification['violations'], indent=2)}"
        )


def _register_core_profile(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register the baseline coding profile."""
    _register_store_tool(mcp, ctx)
    _register_search_tool(mcp, ctx)
    _register_status_tool(mcp, ctx)
    _register_ledger_tool(mcp, ctx)
    _register_trace_episode_tool(mcp, ctx)
    _register_trace_chain_tool(mcp, ctx)
    _register_shannon_report_tool(mcp, ctx)
    _register_handoff_tool(mcp, ctx)
    _register_embed_tool(mcp, ctx)
    _register_embed_status_tool(mcp, ctx)


def _register_trust_profile(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register trust and health tools."""
    register_trust_tools(mcp, ctx)
    register_health_tools(mcp, ctx)


def _register_ops_profile(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register operations and generation tools."""
    register_mega_tools(mcp, ctx)
    register_genesis_tools(mcp, ctx)
    register_scraper_tools(mcp)


def _register_media_profile(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register media-generation tools."""
    from cortex.mcp.music_tools import register_music_tools
    from cortex.mcp.suno_tools import register_suno_tools

    register_music_tools(mcp)
    register_suno_tools(mcp, ctx)


def _register_research_profile(mcp: FastMCP, ctx: _MCPContext) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register research-oriented theorem tooling."""
    from cortex.mcp.hilbert_tools import register_hilbert_tools

    register_hilbert_tools(mcp, ctx)


_PROFILE_REGISTRARS = {
    "core": _register_core_profile,
    "trust": _register_trust_profile,
    "ops": _register_ops_profile,
    "media": _register_media_profile,
    "research": _register_research_profile,
}


# ─── Factory ─────────────────────────────────────────────────────────


def create_mcp_server(config: MCPServerConfig | None = None) -> FastMCP:  # type: ignore[reportInvalidTypeForm]
    """Create and configure an optimized CORTEX MCP server instance.

    Each tool is registered via a dedicated helper, keeping this
    function focused on orchestration (cognitive complexity ≤ 5).
    """
    if not _MCP_AVAILABLE:
        raise ImportError("MCP SDK not installed. Install with: pip install 'cortex-persist[mcp]'")

    cfg = config or MCPServerConfig()
    mcp = FastMCP(  # type: ignore[reportOptionalCall]
        "CORTEX Trust Engine",
        host=cfg.host,
        port=cfg.port,
    )
    ctx = _MCPContext(cfg)
    tool_profile = _normalize_tool_profile(cfg.tool_profile)
    logger.info(
        "Creating CORTEX MCP server with tool profile '%s' (%d tools)",
        tool_profile,
        len(get_profile_tool_names(tool_profile)),
    )
    _PROFILE_REGISTRARS[tool_profile](mcp, ctx)

    return mcp


# ─── Global Server Instance ──────────────────────────────────────────

# Default configuration
_default_config = MCPServerConfig()
mcp = create_mcp_server(_default_config)


def run_server(config: MCPServerConfig | None = None) -> None:
    """Start the CORTEX MCP server."""
    global mcp
    if config:
        mcp = create_mcp_server(config)

    cfg = config or _default_config

    if cfg.transport == "sse":
        logger.info("Starting CORTEX MCP server v2 (SSE) on %s:%d", cfg.host, cfg.port)
        mcp.run(transport="sse")
    else:
        logger.info("Starting CORTEX MCP server v2 (stdio)")
        mcp.run()
