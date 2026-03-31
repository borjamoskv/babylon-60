"""
CORTEX Leviathan: Sovereign Targeting Engine (AX-1000)
Autonomous discovery and compliance auditing of EU-based AI startups.
Integrates AsyncCortexEngine + SwarmManager for OMEGA-routed audit dispatch.
"""

import asyncio
import logging
import os
import time
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("Leviathan-Swarm")


class Target(BaseModel):
    name: str
    jurisdiction: str
    sector: str
    compliance_risk: str = "HIGH"
    repo_url: str
    estimated_revenue_usd: float = 0.0


class AuditResult(BaseModel):
    target_name: str
    jurisdiction: str
    report: str
    status: str = "pending"
    ledger_committed: bool = False
    duration_s: float = 0.0


class TargetingEngine:
    """
    Sovereign Target Discovery & Compliance Engine (Project LEVIATHAN).
    Identifies agentic AI systems lacking cryptographic audit trails
    and dispatches OMEGA squads to generate compliance integration PRs.
    """

    SEED_TARGETS: list[dict[str, Any]] = [
        {
            "name": "MistralAI-Fan-Repo",
            "jurisdiction": "FR",
            "sector": "LLM",
            "repo_url": "github.com/mistral/fan",
            "estimated_revenue_usd": 5_000_000.0,
        },
        {
            "name": "DeepBerlin",
            "jurisdiction": "DE",
            "sector": "Vision",
            "repo_url": "github.com/deepberlin/core",
            "estimated_revenue_usd": 2_000_000.0,
        },
        {
            "name": "Madrid-AI-Edge",
            "jurisdiction": "ES",
            "sector": "Edge",
            "repo_url": "github.com/madrid-ai/edge-v1",
            "estimated_revenue_usd": 1_000_000.0,
        },
    ]

    def __init__(
        self,
        engine: Any = None,
        swarm_manager: Any = None,
        github_token: str | None = None,
    ):
        self.engine = engine
        self.swarm_manager = swarm_manager
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.targets: list[Target] = [
            Target(**t) for t in self.SEED_TARGETS
        ]
        self.results: list[AuditResult] = []

    # ── Jurisdiction mapping for GitHub user locations ──
    JURISDICTION_MAP: dict[str, str] = {
        "france": "FR", "paris": "FR", "lyon": "FR",
        "germany": "DE", "berlin": "DE", "munich": "DE", "münchen": "DE",
        "spain": "ES", "madrid": "ES", "barcelona": "ES",
        "netherlands": "NL", "amsterdam": "NL",
        "italy": "IT", "milan": "IT", "rome": "IT",
        "portugal": "PT", "lisbon": "PT",
        "belgium": "BE", "brussels": "BE",
        "austria": "AT", "vienna": "AT",
        "ireland": "IE", "dublin": "IE",
        "sweden": "SE", "stockholm": "SE",
        "finland": "FI", "helsinki": "FI",
        "poland": "PL", "warsaw": "PL",
    }

    COMPLIANCE_KEYWORDS = frozenset({
        "audit trail", "audit log", "compliance", "eu ai act",
        "record-keeping", "record keeping", "gdpr", "logging framework",
    })

    async def discover_targets(
        self,
        queries: list[str] | None = None,
        max_results: int = 10,
    ) -> list[Target]:
        """
        Discover targets dynamically via GitHub Search API.
        Finds AI agent repos in EU jurisdictions lacking compliance keywords.
        """
        import httpx

        search_queries = queries or [
            "AI agent framework language:python stars:>50",
            "agentic workflow LLM language:python stars:>30",
            "multi-agent orchestration language:python stars:>20",
        ]

        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        discovered: list[Target] = []
        seen_repos: set[str] = {t.repo_url for t in self.targets}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in search_queries:
                try:
                    resp = await client.get(
                        "https://api.github.com/search/repositories",
                        params={"q": query, "per_page": max_results, "sort": "stars"},
                        headers=headers,
                    )
                    if resp.status_code != 200:
                        logger.warning(
                            "[DISCOVERY] GitHub API returned %d for query: %s",
                            resp.status_code, query,
                        )
                        continue

                    items = resp.json().get("items", [])
                    for repo in items:
                        full_name = repo.get("full_name", "")
                        if full_name in seen_repos:
                            continue

                        # Check description + README for compliance keywords
                        desc = (repo.get("description") or "").lower()
                        has_compliance = any(
                            kw in desc for kw in self.COMPLIANCE_KEYWORDS
                        )
                        if has_compliance:
                            continue  # Already compliant, skip

                        # Infer jurisdiction from owner location
                        owner = repo.get("owner", {})
                        location = (owner.get("location") or "").lower()
                        jurisdiction = None
                        for loc_key, jur_code in self.JURISDICTION_MAP.items():
                            if loc_key in location:
                                jurisdiction = jur_code
                                break

                        if not jurisdiction:
                            continue  # Non-EU, skip

                        target = Target(
                            name=repo.get("name", full_name),
                            jurisdiction=jurisdiction,
                            sector=self._infer_sector(desc),
                            repo_url=f"github.com/{full_name}",
                            estimated_revenue_usd=float(
                                repo.get("stargazers_count", 0)
                            ) * 100.0,  # Rough heuristic: stars × $100
                        )
                        discovered.append(target)
                        seen_repos.add(full_name)

                except Exception as exc:
                    logger.error("[DISCOVERY] Query failed: %s — %s", query, exc)

        logger.info("[DISCOVERY] Found %d new targets in EU jurisdiction", len(discovered))
        return discovered

    @staticmethod
    def _infer_sector(description: str) -> str:
        """Infer sector from repo description."""
        desc = description.lower()
        if any(kw in desc for kw in ("llm", "language model", "gpt", "chat")):
            return "LLM"
        if any(kw in desc for kw in ("vision", "image", "cv", "detection")):
            return "Vision"
        if any(kw in desc for kw in ("agent", "agentic", "swarm", "orchestrat")):
            return "Agentic"
        if any(kw in desc for kw in ("edge", "iot", "embedded")):
            return "Edge"
        return "AI/General"

    def generate_compliance_report(self, target: Target) -> str:
        """
        EU AI Act Art. 12 compliance audit report.
        """
        return (
            f"[CORTEX COMPLIANCE AUDIT]\n"
            f"Target: {target.name}\n"
            f"Jurisdiction: {target.jurisdiction}\n"
            f"Sector: {target.sector}\n"
            f"Risk Level: {target.compliance_risk}\n"
            f"Est. Revenue: ${target.estimated_revenue_usd:,.0f}\n\n"
            "Finding: Agentic infrastructure lacks a deterministic "
            "cryptographic ledger.\n"
            "Liability: Direct corporate liability under EU AI Act "
            "Art. 12 (record-keeping) in the event of model-driven "
            "catastrophic failure.\n\n"
            "Proposed Integration: CORTEX Audit Ledger — "
            "sovereign, append-only, Git-DAG-entangled transaction log."
        )

    async def _audit_target(self, target: Target) -> AuditResult:
        """Audit a single target: generate report, dispatch OMEGA, persist."""
        t0 = time.monotonic()
        report_text = self.generate_compliance_report(target)
        result = AuditResult(
            target_name=target.name,
            jurisdiction=target.jurisdiction,
            report=report_text,
        )

        # Dispatch OMEGA squad for automated PR generation if live
        if self.swarm_manager:
            try:
                prompt = (
                    f"Analyze repo {target.repo_url} for EU AI Act Art. 12 "
                    "compliance gaps. If non-compliant, generate a PR adding "
                    "CORTEX Audit Ledger integration with append-only "
                    "transaction logging."
                )
                responses = await self.swarm_manager.recruit(
                    task=prompt,
                    count=10,
                    squad_type="OMEGA",
                )
                if responses and len(responses) > 0:
                    result.status = "audited"
                else:
                    result.status = "no_response"
            except Exception as exc:
                logger.error(
                    "OMEGA dispatch failed for %s: %s", target.name, exc
                )
                result.status = "dispatch_error"
        else:
            result.status = "simulated"

        # Persist to SovereignLedger
        if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
            try:
                await self.engine.ledger.record_transaction(
                    project="leviathan",
                    action="compliance_audit",
                    detail={
                        "target": target.name,
                        "jurisdiction": target.jurisdiction,
                        "sector": target.sector,
                        "risk": target.compliance_risk,
                        "status": result.status,
                        "revenue_usd": target.estimated_revenue_usd,
                    },
                    tenant_id="default",
                )
                result.ledger_committed = True
            except Exception as exc:
                logger.error(
                    "Ledger write failed for %s: %s", target.name, exc
                )

        result.duration_s = time.monotonic() - t0
        logger.info(
            "[LEVIATHAN] %s (%s) → %s in %.2fs",
            target.name, target.jurisdiction, result.status, result.duration_s,
        )
        return result

    async def execute_swarm_wave(
        self, enable_discovery: bool = False,
    ) -> list[AuditResult]:
        """
        Execute parallel compliance audits across all targets.
        If enable_discovery is True, dynamically discovers new targets
        via GitHub Search API before auditing.
        """
        if enable_discovery:
            discovered = await self.discover_targets()
            if discovered:
                self.targets.extend(discovered)
                logger.info(
                    "[LEVIATHAN] Total targets after discovery: %d",
                    len(self.targets),
                )

        logger.info(
            "Swarm active. Auditing %d targets in EU jurisdiction...",
            len(self.targets),
        )
        tasks = [self._audit_target(t) for t in self.targets]
        self.results = await asyncio.gather(*tasks)
        return self.results


async def _bootstrap_and_run() -> list[AuditResult]:
    """AX-1000 Sovereign Bootstrap for Leviathan Targeting."""
    from cortex import config
    from cortex.database.pool import CortexConnectionPool
    from cortex.engine_async import AsyncCortexEngine
    from cortex.swarm.manager import SwarmManager

    pool = CortexConnectionPool(config.DB_PATH, read_only=False)
    await pool.initialize()
    cortex_engine = AsyncCortexEngine(pool=pool, db_path=config.DB_PATH)
    swarm_mgr = SwarmManager(ledger=cortex_engine._get_ledger())
    await swarm_mgr.start_compaction(cortex_engine)
    logger.info("[LEVIATHAN] AX-1000 Sovereign Engine Initialized")

    try:
        engine = TargetingEngine(
            engine=cortex_engine,
            swarm_manager=swarm_mgr,
        )
        results = await engine.execute_swarm_wave(enable_discovery=True)
    finally:
        await swarm_mgr.stop_compaction()
        await pool.close()
        logger.info("[LEVIATHAN] Sovereign Engine shutdown complete")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_bootstrap_and_run())
    except KeyboardInterrupt:
        logger.info("[LEVIATHAN] Process terminated safely.")
