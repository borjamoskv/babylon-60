# CORTEX-TAINT: cazarecompensas-agent:ab12cd34:1742878308
import logging
import os
import re
from dataclasses import dataclass

import httpx

from cortex.ledger.sovereign_ledger import SovereignLedger

logger = logging.getLogger("cortex.services.bounty_service")


@dataclass
class BountyLead:
    number: int
    title: str
    url: str
    reward_usd: float
    difficulty: str
    score: float
    repo: str


class BountyService:
    """
    Service for identifying and prioritizing high-exergy bounties.
    """

    def __init__(self, ledger: SovereignLedger | None = None, reward_threshold: float = 200.0):
        self.ledger = ledger
        self.reward_threshold = reward_threshold

    async def scan_repository(self, owner: str, repo: str) -> list[BountyLead]:
        """
        Scans a repository for open issues with the 'bounty' label.
        Refactored to integrate live GitHub Search API.
        """
        logger.info("[BOUNTY] Scanning %s/%s for work opportunities...", owner, repo)
        query = f"repo:{owner}/{repo} is:issue is:open label:bounty"
        return await self._fetch_from_github(query)

    async def scan_global(
        self,
        max_results: int = 20,
        languages: list[str] | None = None,
    ) -> list[BountyLead]:
        """
        Scans all of GitHub for open issues with the 'bounty' label.
        Optionally filter by language(s). Defaults to all languages.
        """
        lang_filter = ""
        if languages:
            lang_filter = " ".join(f"language:{lang}" for lang in languages)
        query = f"is:issue is:open label:bounty {lang_filter}".strip()
        logger.info("[BOUNTY] Scanning GitHub globally: %s", query)
        return await self._fetch_from_github(query, limit=max_results)

    async def scan_algora(self, limit: int = 20) -> list[BountyLead]:
        """
        Scans Algora for open bounties via GitHub label search.
        Delegates to SovereignBountyScanner.AlgoraScanner (Ω₃).
        """
        logger.info("[BOUNTY] Scanning Algora via GitHub label search...")
        from cortex.swarm.bounty_scanner import AlgoraScanner

        scanner = AlgoraScanner()
        opportunities = await scanner.scan(min_usd=0.0, limit=limit)
        leads = [
            BountyLead(
                number=0,
                title=opp.title,
                url=opp.url,
                reward_usd=opp.reward_usd,
                difficulty=self._complexity_to_difficulty(opp.complexity),
                score=opp.confidence * 10,
                repo=opp.repo,
            )
            for opp in opportunities
        ]
        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty",
                action="scan_algora",
                detail={"leads_found": len(leads)},
            )
        return leads

    async def scan_all(self, min_usd: float = 100.0) -> list[BountyLead]:
        """
        Unified scan across Algora + Polar + GitHub + Immunefi.
        Delegates to SovereignBountyScanner and converts to BountyLead.
        """
        from cortex.swarm.bounty_scanner import SovereignBountyScanner

        scanner = SovereignBountyScanner()
        opportunities = await scanner.scan_all(min_usd=min_usd)
        leads = [
            BountyLead(
                number=0,
                title=opp.title,
                url=opp.url,
                reward_usd=opp.reward_usd,
                difficulty=self._complexity_to_difficulty(opp.complexity),
                score=opp.confidence * 10,
                repo=opp.repo,
            )
            for opp in opportunities
        ]
        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty",
                action="scan_all",
                detail={"leads_found": len(leads), "min_usd": min_usd},
            )
        return leads

    @staticmethod
    def _complexity_to_difficulty(complexity: int) -> str:
        if complexity <= 3:
            return "low"
        if complexity <= 6:
            return "medium"
        return "high"

    async def validate_lead_semantics(self, lead: BountyLead) -> bool:
        """
        Performs semantic verification of the bounty (Ω₁).
        Designed to be used by the agent to confirm data with Perplexity or similar.
        """
        # In the base service, we just confirm that the reward is above zero.
        # The logic is intended to be called by the Agent using MCP tools.
        return lead.reward_usd > 0

    async def _fetch_from_github(self, query: str, limit: int = 15) -> list[BountyLead]:
        url = "https://api.github.com/search/issues"
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        params = {"q": query, "sort": "updated", "order": "desc", "per_page": limit}

        leads = []
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error("[BOUNTY] Failed to fetch from GitHub API: %s", e)
            return []

        for item in data.get("items", []):
            title = item.get("title", "")
            body = item.get("body", "") or ""
            html_url = item.get("html_url", "")
            number = item.get("number", 0)

            repo_match = re.search(r"github\.com/([^/]+/[^/]+)/issues", html_url, re.IGNORECASE)
            repo_name = repo_match.group(1) if repo_match else "unknown/repo"

            # Parse reward from text like "💎 $500 bounty" or "$50"
            reward_match = re.search(r"\$(\d+(?:\.\d{1,2})?)", title + " " + body)
            reward_usd = float(reward_match.group(1)) if reward_match else 0.0

            if reward_usd <= 0:
                continue

            labels = [lbl.get("name", "").lower() for lbl in item.get("labels", [])]
            difficulty = "high"
            score = 8.0
            if "good first issue" in labels or "easy" in labels or "beginner" in labels:
                difficulty = "low"
                score = 2.0
            elif "medium" in labels:
                difficulty = "medium"
                score = 5.0

            leads.append(
                BountyLead(
                    number=number,
                    title=title,
                    url=html_url,
                    reward_usd=reward_usd,
                    difficulty=difficulty,
                    score=score,
                    repo=repo_name,
                )
            )

        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty", action="scan", detail={"query": query, "leads_found": len(leads)}
            )

        return leads

    async def rank_leads(self, leads: list[BountyLead]) -> list[BountyLead]:
        """Rank leads by thermodynamic Exergy/Entropy ratio (Ω₂)."""
        from decimal import Decimal

        filtered = []
        for L in leads:
            diff_weight = {"low": 2, "medium": 5, "high": 8, "critical": 10}.get(L.difficulty, 5)
            context_lines = 100 if diff_weight <= 2 else (300 if diff_weight <= 5 else 500)

            exergy = Decimal(str(L.reward_usd))
            entropy_base = Decimal(diff_weight) * 50 + Decimal(context_lines) * Decimal("0.1")

            ghost_penalty = (
                Decimal(context_lines) * Decimal("0.5")
                if diff_weight >= 5 and exergy < Decimal("200")
                else Decimal("0")
            )

            meta_penalty = (
                Decimal(diff_weight) ** 2 * Decimal("4") if diff_weight >= 8 else Decimal("0")
            )

            entropy = max(entropy_base + ghost_penalty + meta_penalty, Decimal("1"))
            ratio = float(exergy / entropy)

            min_ratio = max(3.0, self.reward_threshold / 100.0)

            L.score = ratio

            if ratio >= min_ratio:
                filtered.append(L)

        if self.ledger and len(filtered) < len(leads):
            discard_count = len(leads) - len(filtered)
            await self.ledger.record_transaction(
                project="bounty",
                action="lead_discard",
                detail={"count": discard_count, "reason": "negative_net_exergy_or_threshold"},
            )

        return sorted(filtered, key=lambda x: x.reward_usd, reverse=True)

    def generate_claim_prompt(self, lead: BountyLead) -> str:
        """Constructs a prompt for the specialist to claim and solve the bounty."""
        return (
            f"Solve bounty {lead.repo}#{lead.number}: {lead.title}. "
            f"Reward: ${lead.reward_usd}. "
            f"Requirements: Deliver a high-quality PR following project standards."
        )
