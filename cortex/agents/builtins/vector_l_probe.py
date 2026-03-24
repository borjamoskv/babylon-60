"""Vector L — Signal Probes.

Async scrapers that extract PYME bottleneck signals from public sources.
Each probe returns a list of ProspectSignal objects scored 0.0-1.0.
Zero external auth required for baseline operation.

Sources:
    - LinkedInProbe: job listing volume for ops/admin/data-entry roles
    - GlassdoorProbe: review keyword density (manual, repetitive, no automation)
    - GitHubOrgProbe: engineer count heuristic via GitHub REST API
    - IndeedProbe: job listing volume for non-technical roles
    - TwitterProbe: operational complaints via Nitter (no API key)
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

logger = logging.getLogger("cortex.agents.vector_l.probe")


# ── Domain types ─────────────────────────────────────────────────────────────


@dataclass
class ProspectSignal:
    """A single bottleneck signal for a company from one source."""

    company: str
    domain: str | None
    source: str
    raw_score: float  # 0.0–1.0
    evidence: str
    metadata: dict = field(default_factory=dict)


# ── HTTP helper (lazy import) ─────────────────────────────────────────────────


async def _fetch(url: str, headers: dict | None = None, timeout: float = 10.0) -> str:
    """Async HTTP GET. Returns response text or '' on failure."""
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        logger.error("httpx not installed. Run: pip install httpx")
        return ""

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        **(headers or {}),
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers=_headers)
            resp.raise_for_status()
            return resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch failed url=%s reason=%s", url, exc)
        return ""


# ── Bottleneck keywords ───────────────────────────────────────────────────────

_OPS_KEYWORDS = re.compile(
    r"\b(data[\s-]?entry|administrative|operations?\s+manager|back[\s-]?office"
    r"|manual\s+process|spreadsheet|bookkeeping|accounting\s+clerk"
    r"|office\s+manager|support\s+coordinator|logistics\s+coordinator)\b",
    re.IGNORECASE,
)

_REVIEW_KEYWORDS = re.compile(
    r"\b(manual|repetitive|no\s+automation|outdated\s+tools|paper[\s-]?based"
    r"|inefficient\s+process|still\s+using\s+excel|no\s+software"
    r"|everything\s+is\s+manual|too\s+much\s+admin)\b",
    re.IGNORECASE,
)


# ── Probe base ────────────────────────────────────────────────────────────────


class BaseProbe:
    """Abstract bottleneck signal probe."""

    source: str = "base"
    weight: float = 0.10

    async def scan(self, query: str, limit: int = 20) -> list[ProspectSignal]:  # noqa: ARG002
        raise NotImplementedError


# ── LinkedIn Probe ────────────────────────────────────────────────────────────


class LinkedInProbe(BaseProbe):
    """Parse LinkedIn public job search for ops-heavy companies.

    Strategy: search LinkedIn jobs for bottleneck-related titles,
    group by company, score by density of ops roles.
    Note: uses public search (no auth). Rate-limited to avoid blocks.
    """

    source = "linkedin"
    weight = 0.35

    _SEARCH_URL = (
        "https://www.linkedin.com/jobs/search/"
        "?keywords={query}&f_TPR=r86400&sortBy=DD&start={start}"
    )

    async def scan(self, query: str = "data entry OR office manager", limit: int = 50) -> list[ProspectSignal]:
        signals: dict[str, list[str]] = {}
        encoded = quote_plus(query)
        for start in range(0, min(limit, 100), 25):
            url = self._SEARCH_URL.format(query=encoded, start=start)
            html = await _fetch(url)
            if not html:
                break

            # Parse company names + job titles from LinkedIn job cards
            companies = re.findall(
                r'"companyName"\s*:\s*"([^"]{3,80})"', html
            ) or re.findall(
                r'class="job-search-card__subtitle[^"]*"[^>]*>\s*<a[^>]*>([^<]{3,60})</a>',
                html,
            )
            titles = re.findall(r'"jobTitle"\s*:\s*"([^"]{3,100})"', html)

            for i, company in enumerate(companies[:25]):
                title = titles[i] if i < len(titles) else ""
                if _OPS_KEYWORDS.search(title) or _OPS_KEYWORDS.search(company):
                    signals.setdefault(company, []).append(title)

            await asyncio.sleep(2.0)  # rate limit

        results = []
        for company, titles in signals.items():
            density = min(len(titles) / 5.0, 1.0)
            results.append(
                ProspectSignal(
                    company=company,
                    domain=None,
                    source=self.source,
                    raw_score=round(density, 3),
                    evidence=f"{len(titles)} ops/admin roles: {', '.join(titles[:3])}",
                )
            )
        return results


# ── Glassdoor Probe ───────────────────────────────────────────────────────────


class GlassdoorProbe(BaseProbe):
    """Parse Glassdoor public reviews for manual-process indicators."""

    source = "glassdoor"
    weight = 0.25

    _SEARCH_URL = "https://www.glassdoor.com/Reviews/company-reviews.htm?suggestCount=0&suggestChosen=false&clickSource=searchBtn&typedKeyword={query}&sc.keyword={query}&locT=&locId=&jobType="

    async def scan(self, query: str = "small company", limit: int = 20) -> list[ProspectSignal]:
        signals = []
        encoded = quote_plus(query)
        url = self._SEARCH_URL.format(query=encoded)
        html = await _fetch(url)
        if not html:
            return []

        # Extract company names and review snippets
        company_blocks = re.findall(
            r'"employerName"\s*:\s*"([^"]{2,80})".*?"pros"\s*:\s*"([^"]{0,500})".*?"cons"\s*:\s*"([^"]{0,500})"',
            html,
            re.DOTALL,
        )

        for company, pros, cons in company_blocks[:limit]:
            combined = pros + " " + cons
            matches = _REVIEW_KEYWORDS.findall(combined)
            if matches:
                score = min(len(matches) / 4.0, 1.0)
                signals.append(
                    ProspectSignal(
                        company=company,
                        domain=None,
                        source=self.source,
                        raw_score=round(score, 3),
                        evidence=f"Review keywords: {', '.join(set(m.strip() for m in matches[:4]))}",
                    )
                )

        return signals


# ── GitHub Org Probe ──────────────────────────────────────────────────────────


class GitHubOrgProbe(BaseProbe):
    """Check company GitHub org — low engineer presence = ops-heavy company.

    A company with a GitHub org but few repos/engineers is likely
    run by non-technical leadership = high CORTEX agent receptivity.
    """

    source = "github_org"
    weight = 0.20

    _ORG_URL = "https://api.github.com/orgs/{org}"
    _MEMBERS_URL = "https://api.github.com/orgs/{org}/members?per_page=10"

    async def scan_org(self, org_name: str) -> ProspectSignal | None:
        import os

        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        org_text = await _fetch(self._ORG_URL.format(org=org_name), headers=headers)
        if not org_text:
            return None

        try:
            import json

            data = json.loads(org_text)
            public_repos = data.get("public_repos", 0)
            company = data.get("name") or org_name

            # Low repo count → tech-light company
            score = max(0.0, 1.0 - (public_repos / 20.0))
            if score < 0.3:
                return None

            return ProspectSignal(
                company=company,
                domain=data.get("blog"),
                source=self.source,
                raw_score=round(score, 3),
                evidence=f"GitHub org {org_name}: {public_repos} repos (low tech footprint)",
                metadata={"org": org_name, "repos": public_repos},
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("GitHubOrgProbe parse error org=%s: %s", org_name, exc)
            return None

    async def scan(self, query: str = "", limit: int = 20) -> list[ProspectSignal]:
        # query is treated as comma-separated org list or a search term
        if "," in query:
            orgs = [o.strip() for o in query.split(",") if o.strip()]
        else:
            orgs = [query.strip()] if query.strip() else []

        tasks = [self.scan_org(org) for org in orgs[:limit]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, ProspectSignal)]


# ── Indeed Probe ──────────────────────────────────────────────────────────────


class IndeedProbe(BaseProbe):
    """Parse Indeed public job listings for non-technical role density."""

    source = "indeed"
    weight = 0.15

    _SEARCH_URL = "https://www.indeed.com/jobs?q={query}&sort=date&limit=25&fromage=3"

    async def scan(self, query: str = "office manager OR data entry", limit: int = 30) -> list[ProspectSignal]:
        encoded = quote_plus(query)
        url = self._SEARCH_URL.format(query=encoded)
        html = await _fetch(url)
        if not html:
            return []

        signals: dict[str, list[str]] = {}
        # Extract company names from Indeed result cards
        companies = re.findall(
            r'data-testid="company-name"[^>]*>([^<]{2,80})</span', html
        ) or re.findall(
            r'class="companyName"[^>]*>(?:<a[^>]*>)?([^<]{2,80})(?:</a>)?</span>',
            html,
        )
        titles = re.findall(
            r'class="jobTitle[^"]*"[^>]*>\s*<span[^>]*>([^<]{3,100})</span',
            html,
        )

        for i, company in enumerate(companies[:limit]):
            title = titles[i] if i < len(titles) else ""
            if _OPS_KEYWORDS.search(title):
                signals.setdefault(company.strip(), []).append(title)

        return [
            ProspectSignal(
                company=c,
                domain=None,
                source=self.source,
                raw_score=round(min(len(t) / 3.0, 1.0), 3),
                evidence=f"{len(t)} non-tech roles: {', '.join(t[:2])}",
            )
            for c, t in signals.items()
        ]


# ── Bottleneck Scorer ─────────────────────────────────────────────────────────


PROBE_WEIGHTS: dict[str, float] = {
    "linkedin": 0.35,
    "glassdoor": 0.25,
    "github_org": 0.20,
    "indeed": 0.15,
    "twitter": 0.05,
}


def score_company(signals: list[ProspectSignal], employee_count: int = 50) -> float:
    """Aggregate multi-source signals into a single exergy gap score.

    Returns float 0.0–1.0. Threshold for pitch: > 0.55.
    company_size_factor amplifies score for larger SMEs (more budget).

    Args:
        signals: all ProspectSignal objects for a single company
        employee_count: approximate employee count (default 50)

    Returns:
        exergy_gap: 0.0–1.0 composite score
    """
    import math

    if not signals:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0
    for sig in signals:
        w = PROBE_WEIGHTS.get(sig.source, 0.10)
        weighted_sum += sig.raw_score * w
        total_weight += w

    base_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Size amplifier: log10(50)=1.7 → factor≈0.57; log10(200)=2.3 → factor≈0.77
    count = max(10, min(employee_count, 10_000))
    size_factor = math.log10(count) / 3.0

    exergy_gap = round(base_score * (1.0 + size_factor), 4)
    return min(exergy_gap, 1.0)


def tier_from_score(exergy_gap: float) -> int:
    """Map exergy gap to monthly price tier in USD."""
    if exergy_gap >= 0.85:
        return 2000
    if exergy_gap >= 0.70:
        return 1000
    if exergy_gap >= 0.55:
        return 500
    return 0  # below threshold — do not pitch


# ── Public registry ───────────────────────────────────────────────────────────

ALL_PROBES: list[type[BaseProbe]] = [
    LinkedInProbe,
    GlassdoorProbe,
    GitHubOrgProbe,
    IndeedProbe,
]
