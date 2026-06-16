# [C5-REAL] Exergy-Maximized
"""MCP tools for CORTEX NotebookLM integration.

Registers NotebookLM tools on a FastMCP server so AI agents
can manage the Ouroboros memory loop autonomously.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.mcp.notebooklm")


def _register_notebooklm_digest(mcp: Any, ctx: Any) -> None:
    @mcp.tool()
    async def notebooklm_digest(
        output: str = "cortex_notebooklm_digest.md",
        project: str | None = None,
    ) -> dict:
        """Generate Master Digest for NotebookLM with Shadow Key anchors.

        Extracts all active CORTEX facts, applies the Shadow Key protocol
        (∆_CTX/∇_CTX anchors), and writes a cleartext Markdown digest.

        Args:
            output: Output file path (default: cortex_notebooklm_digest.md).
            project: Optional project filter. If None, exports all projects.

        Returns:
            dict with keys: file, facts_count, word_count, status.
        """
        from cortex.services.notebooklm import NotebookLMService

        db_path = getattr(ctx, "db_path", "")
        svc = NotebookLMService(str(db_path))
        content = await svc.generate_digest(project=project)

        Path(output).write_text(content, encoding="utf-8")
        word_count = len(content.split())
        facts_count = content.count("∆_CTX:")

        return {
            "file": output,
            "facts_count": facts_count,
            "word_count": word_count,
            "status": "safe" if word_count < 500_000 else "OVER_LIMIT",
        }

def _register_notebooklm_fragment(mcp: Any, ctx: Any) -> None:
    @mcp.tool()
    async def notebooklm_fragment(
        output_dir: str = "notebooklm_domains",
    ) -> dict:
        """Fragment CORTEX facts into semantic domain files.

        Classifies facts by domain taxonomy (7 domains) and writes
        one timestamped Markdown file per domain.

        Args:
            output_dir: Output directory for domain fragment files.

        Returns:
            dict mapping domain name to fact count.
        """
        from cortex.services.notebooklm import NotebookLMService

        db_path = getattr(ctx, "db_path", "")
        svc = NotebookLMService(str(db_path))
        counts = await svc.fragment_by_domain(Path(output_dir))

        return {"domains": counts, "total_facts": sum(counts.values())}

def _detect_cloud_target(drive_path: str | None) -> tuple[Path | None, str]:
    from cortex.services.notebooklm import CLOUD_PROVIDERS
    if drive_path:
        return Path(drive_path), "Custom"
    for provider, paths in CLOUD_PROVIDERS.items():
        for p in paths:
            if p.parent.exists():
                return p, provider
    return None, "Custom"

def _perform_sync(target: Path, mode: str) -> tuple[list[str], int]:
    import os
    import shutil
    import time
    from datetime import datetime, timezone

    from cortex.services.notebooklm import DIGEST_FILE, DOMAINS_DIR
    
    target.mkdir(parents=True, exist_ok=True)
    ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y-%m-%d")
    synced: list[str] = []

    if mode in ("digest", "both") and DIGEST_FILE.exists():
        dest = target / f"cortex-master-{ts}.md"
        shutil.copy2(DIGEST_FILE, dest)
        synced.append(str(dest))

    if mode in ("domains", "both") and DOMAINS_DIR.exists():
        for f in DOMAINS_DIR.glob("*.md"):
            dest = target / f.name
            shutil.copy2(f, dest)
            synced.append(str(dest))

    cutoff = time.monotonic() - (7 * 86400)
    cleaned = 0
    synced_names = {Path(s).name for s in synced}
    for f in target.glob("*.md"):
        if os.path.getmtime(f) < cutoff and f.name not in synced_names:
            f.unlink()
            cleaned += 1
            
    return synced, cleaned

def _notebooklm_sync_impl(drive_path: str | None, mode: str) -> dict:
    target, provider_name = _detect_cloud_target(drive_path)
    if not target:
        return {"error": "No cloud sync provider detected. Specify drive_path."}
    synced, cleaned = _perform_sync(target, mode)
    return {
        "provider": provider_name,
        "destination": str(target),
        "files_synced": len(synced),
        "files_cleaned": cleaned,
    }

def _register_notebooklm_sync(mcp: Any, ctx: Any) -> None:
    @mcp.tool()
    async def notebooklm_sync(
        drive_path: str | None = None,
        mode: str = "both",
    ) -> dict:
        """Sync exported files to cloud storage for NotebookLM pickup.

        Auto-detects Google Drive, OneDrive, or iCloud. Copies digest
        and/or domain fragments. Cleans stale files older than 7 days.

        Args:
            drive_path: Optional explicit cloud folder path. Auto-detected if None.
            mode: What to sync - 'digest', 'domains', or 'both'.

        Returns:
            dict with keys: provider, destination, files_synced, files_cleaned.
        """
        return _notebooklm_sync_impl(drive_path, mode)

def _get_notebooklm_digest_status() -> dict:
    import os
    import time
    from datetime import datetime, timezone

    from cortex.services.notebooklm import DIGEST_FILE
    if DIGEST_FILE.exists():
        mtime = os.path.getmtime(DIGEST_FILE)
        age_h = (time.monotonic() - mtime) / 3600
        return {
            "exists": True,
            "size_bytes": os.path.getsize(DIGEST_FILE),
            "updated": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            "age_hours": round(age_h, 1),
        }
    return {"exists": False}

def _get_notebooklm_domains_status() -> dict:
    import os

    from cortex.services.notebooklm import DOMAINS_DIR
    if DOMAINS_DIR.exists():
        files = list(DOMAINS_DIR.glob("*.md"))
        return {
            "exists": True,
            "file_count": len(files),
            "total_bytes": sum(os.path.getsize(f) for f in files),
        }
    return {"exists": False}

def _notebooklm_status_impl() -> dict:
    target, provider_name = _detect_cloud_target(None)
    cloud_info = {"provider": provider_name, "path": str(target) if target else None}
    
    digest_status = _get_notebooklm_digest_status()
    domains_status = _get_notebooklm_domains_status()
    
    staleness = "no_digest"
    if digest_status.get("exists"):
        age = digest_status["age_hours"]
        if age > 48:
            staleness = "critical"
        elif age > 24:
            staleness = "warning"
        else:
            staleness = "fresh"
            
    return {
        "digest": digest_status,
        "domains": domains_status,
        "cloud": cloud_info,
        "staleness": staleness
    }

def _register_notebooklm_status(mcp: Any, ctx: Any) -> None:
    @mcp.tool()
    async def notebooklm_status() -> dict:
        """Check NotebookLM sync status - staleness, file inventory, cloud detection.

        No arguments required. Reports digest freshness, domain fragment count,
        cloud sync provider availability, and staleness warnings.

        Returns:
            dict with keys: digest, domains, cloud, staleness.
        """
        return _notebooklm_status_impl()

def register_notebooklm_tools(mcp: Any, ctx: Any) -> None:
    """Register NotebookLM tools on the MCP server.

    Args:
        mcp: FastMCP server instance.
        ctx: MCPContext with engine reference.
    """
    _register_notebooklm_digest(mcp, ctx)
    _register_notebooklm_fragment(mcp, ctx)
    _register_notebooklm_sync(mcp, ctx)
    _register_notebooklm_status(mcp, ctx)
    
    logger.debug("Registered NotebookLM MCP tools")
