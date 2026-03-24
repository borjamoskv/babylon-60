import asyncio
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

    async def scan_global(self, max_results: int = 20) -> list[BountyLead]:
        """
        Scans all of GitHub for Python open issues with the 'bounty' label.
        """
        logger.info("[BOUNTY] Scanning GitHub globally for open Python bounties...")
        query = "is:issue is:open label:bounty language:python"
        return await self._fetch_from_github(query, limit=max_results)

    async def scan_algora(self, limit: int = 20) -> list[BountyLead]:
        """
        Scans algora.io for open bounties (Ω₃.3).
        """
        logger.info("[BOUNTY] Scanning algora.io for open bounties...")
        url = "https://algora.io/bounties"
        leads = []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

                # Pattern: [Company #Issue $Amount Title](URL)
                # Example: [Archestra #3378 $500 Agent schedule triggers](https://github.com/...)
                # Example: [Twenty (YC S23) $2,500 IMAP](https://algora.io/...)
                pattern = r"\[(.*?)(?:\s+#(\d+))?\s+\$([\d,]+(?:\.\d{2})?)\s+(.*?)\]\((.*?)\)"
                matches = re.finditer(pattern, html)

                for m in matches:
                    if len(leads) >= limit:
                        break
                    company, issue_num, amount_str, title, link = m.groups()
                    amount = float(amount_str.replace(",", ""))

                    leads.append(BountyLead(
                        number=int(issue_num) if issue_num else 0,
                        title=title.strip(),
                        url=link,
                        reward_usd=amount,
                        difficulty="medium", # Default for Algora
                        score=7.0,
                        repo=company.strip()
                    ))
        except Exception as e:
            logger.error("[BOUNTY] Failed to fetch from Algora: %s", e)

        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty",
                action="scan_algora",
                detail={"leads_found": len(leads)}
            )
        return leads

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

        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": limit
        }

        leads = []
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
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
                    repo=repo_name
                )
            )

        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty",
                action="scan",
                detail={"query": query, "leads_found": len(leads)}
            )

        return leads

    def rank_leads(self, leads: list[BountyLead]) -> list[BountyLead]:
        """Rank leads by reward and filter by exergy threshold (Ω₂)."""
        filtered = []
        for L in leads:
            # Algora-Jules Exergy Filter: No bounties < $100 unless difficulty allows it
            if L.reward_usd < 100.0 and L.difficulty != "low":
                continue

            # Thermodynamic Evaluation: Expected_Value = (Reward - Cloud_Cost) * Confidence
            cloud_cost = 5.0 if L.difficulty == "high" else (2.0 if L.difficulty == "medium" else 0.5)
            confidence = min(L.score / 10.0, 0.95)
            expected_value = (L.reward_usd - cloud_cost) * confidence

            # Filter based on genuine Expected Value Exergy
            if expected_value >= self.reward_threshold:
                filtered.append(L)

        # Log discards if ledger is present
        if self.ledger and len(filtered) < len(leads):
            discard_count = len(leads) - len(filtered)
            asyncio.create_task(self.ledger.record_transaction(
                project="bounty",
                action="lead_discard",
                detail={"count": discard_count, "reason": "negative_net_exergy_or_threshold"}
            ))

        return sorted(filtered, key=lambda x: x.reward_usd, reverse=True)

    def generate_claim_prompt(self, lead: BountyLead) -> str:
        """Constructs a prompt for the specialist to claim and solve the bounty."""
        return (
            f"Solve bounty {lead.repo}#{lead.number}: {lead.title}. "
            f"Reward: ${lead.reward_usd}. "
            f"Requirements: Deliver a high-quality PR following project standards."
        )
