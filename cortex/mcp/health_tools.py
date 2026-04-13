"""MCP tools for CORTEX Health Index.

Registers health monitoring tools on a FastMCP server so AI agents
can query system health autonomously.
"""

from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.mcp.health")


def _resolve_db_path(ctx: Any) -> str:
    """Normalize the configured MCP DB path before health collection."""
    cfg = getattr(ctx, "cfg", None)
    raw_path = getattr(cfg, "db_path", None)
    if raw_path is None:
        raw_path = getattr(ctx, "db_path", "")
    if isinstance(raw_path, PathLike):
        raw_path = str(raw_path)
    if not raw_path:
        return ""
    return str(Path(str(raw_path)).expanduser())


def register_health_tools(mcp: Any, ctx: Any) -> None:
    """Register health tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """

    @mcp.tool()
    async def cortex_health_check() -> dict:
        """Quick CORTEX health check — returns score, grade, and healthy boolean.

        No arguments required. Checks DB, ledger, and entropy.
        Returns: {"healthy": bool, "score": float, "grade": str}
        """
        from cortex.extensions.health import classify_component_status, collect_health_score
        from cortex.extensions.health.scorer import HealthScorer

        db_path = _resolve_db_path(ctx)
        hs = collect_health_score(db_path)

        return {
            "healthy": hs.score >= 40.0,
            "score": round(hs.score, 2),
            "grade": hs.grade.letter,
            "summary": HealthScorer.summarize(hs),
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "weight": m.weight,
                    "status": classify_component_status(m),
                }
                for m in hs.metrics
            ],
        }

    @mcp.tool()
    async def cortex_health_report() -> dict:
        """Full CORTEX health report with score, recommendations, and warnings.

        No arguments required.
        Returns: {"score": {...}, "recommendations": [...], "warnings": [...]}
        """
        from cortex.extensions.health import build_health_report

        db_path = _resolve_db_path(ctx)
        report = build_health_report(db_path)
        return report.to_dict()

    logger.debug("Registered health MCP tools")
