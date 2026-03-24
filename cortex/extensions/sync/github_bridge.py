"""GitHub → CORTEX Bridge — Synchronize Issues/PRs as CORTEX facts.

Open issues/PRs are stored as `bridge` facts.
Closed issues crystallize into `decision` facts (bridge deprecated, decision created).
Dedup via SHA256 of `{repo}/{number}` stored in `meta.github_key`.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from cortex.memory.temporal import now_iso

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

__all__ = ["GitHubCortexBridge", "SyncResult"]

logger = logging.getLogger("cortex.extensions.sync.github")

_GH_API = "https://api.github.com"
_PROJECT = "github-sync"
_SOURCE = "bridge:github"


@dataclass
class SyncResult:
    """Aggregate result of a GitHub → CORTEX sync run."""

    repos_scanned: int = 0
    issues_synced: int = 0
    prs_synced: int = 0
    crystallized: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _github_key(repo: str, number: int) -> str:
    """Deterministic dedup key: SHA256(`owner/repo#number`)."""
    raw = f"{repo}#{number}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class GitHubCortexBridge:
    """Bidirectional bridge between GitHub Issues/PRs and CORTEX facts.

    Parameters
    ----------
    engine : CortexEngine
        An initialised CORTEX engine instance.
    token : str
        GitHub Personal Access Token with `repo` scope.
    owner : str
        GitHub user/org to scan (default: ``borjamoskv``).
    """

    def __init__(
        self,
        engine: CortexEngine,
        token: str,
        owner: str = "borjamoskv",
    ) -> None:
        self._engine = engine
        self._owner = owner
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    # ─── Public API ──────────────────────────────────────────────────

    async def sync_all(self, repo_filter: str | None = None) -> SyncResult:
        """Discover repos and sync all issues/PRs into CORTEX.

        Parameters
        ----------
        repo_filter : str | None
            If set, only sync this single repo (name, not full path).
        """
        result = SyncResult()

        try:
            repos = await self.discover_repos(repo_filter)
        except httpx.HTTPStatusError as exc:
            result.errors.append(f"GitHub API error: {exc.response.status_code}")
            return result

        # Pre-load existing github_keys for O(1) dedup
        existing = await self._load_existing_keys()

        for repo_name in repos:
            result.repos_scanned += 1
            try:
                await self._sync_repo(repo_name, existing, result)
            except httpx.HTTPError as exc:
                msg = f"Failed to sync {repo_name}: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

        return result

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get_repo_stats(self, repo: str) -> dict[str, Any]:
        """Fetch repository statistics (stars, forks, watchers)."""
        resp = await self._client.get(f"{_GH_API}/repos/{repo}")
        resp.raise_for_status()
        data = resp.json()
        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "watchers": data.get("subscribers_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "updated_at": data.get("updated_at", ""),
        }

    async def get_issue_comments(self, repo: str, number: int) -> list[dict[str, Any]]:
        """Fetch comments for a specific issue or PR."""
        resp = await self._client.get(f"{_GH_API}/repos/{repo}/issues/{number}/comments")
        resp.raise_for_status()
        return resp.json()

    async def post_bounty_invoice(self, repo: str, number: int, amount: int) -> dict[str, Any]:
        """Post a payment invoice to a PR using the Algora Invoice Bridge."""
        try:
            from cortex.extensions.algora.invoice_injector import AlgoraInvoiceBridge
        except ImportError:
            logger.error("AlgoraInvoiceBridge not found.")
            raise

        injector = AlgoraInvoiceBridge()
        comment_body = injector.compose_invoice_comment(amount)

        resp = await self._client.post(
            f"{_GH_API}/repos/{repo}/issues/{number}/comments",
            json={"body": comment_body}
        )
        resp.raise_for_status()
        logger.info("💰 Injected bounty invoice of $%d into %s#%d", amount, repo, number)
        return resp.json()

    # ─── Repo Discovery ──────────────────────────────────────────────

    async def discover_repos(self, repo_filter: str | None = None) -> list[str]:
        """List public repos for the owner. Returns full names (owner/repo)."""
        if repo_filter:
            if "/" in repo_filter:
                return [repo_filter]
            return [f"{self._owner}/{repo_filter}"]

        repos: list[str] = []
        page = 1
        while True:
            resp = await self._client.get(
                f"{_GH_API}/users/{self._owner}/repos",
                params={"per_page": 100, "page": page, "type": "owner"},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            repos.extend(r["full_name"] for r in batch if not r.get("fork"))
            page += 1
        return repos

    # ─── Per-Repo Sync ───────────────────────────────────────────────

    async def _sync_repo(
        self,
        repo: str,
        existing: dict[str, int],
        result: SyncResult,
    ) -> None:
        """Fetch issues/PRs for a single repo and reconcile with CORTEX."""
        page = 1
        while True:
            resp = await self._client.get(
                f"{_GH_API}/repos/{repo}/issues",
                params={
                    "state": "all",
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break

            for item in items:
                await self._process_item(item, repo, existing, result)

            page += 1

    async def _process_item(
        self,
        item: dict[str, Any],
        repo: str,
        existing: dict[str, int],
        result: SyncResult,
        include_comments: bool = True,
    ) -> None:
        """Process a single issue/PR item."""
        number: int = item["number"]
        key = _github_key(repo, number)
        is_pr = "pull_request" in item
        state: str = item["state"]  # "open" or "closed"

        fact_id = None
        if key in existing:
            # Already in CORTEX — check for crystallization
            if state == "closed":
                fact_id = await self._crystallize_decision(item, repo, existing[key])
                result.crystallized += 1
            else:
                fact_id = existing[key]
                result.skipped += 1
        else:
            # New item — only store open ones as bridges
            if state == "open":
                fact_id = await self._store_bridge(item, repo, key, is_pr)
                if is_pr:
                    result.prs_synced += 1
                else:
                    result.issues_synced += 1
            # Closed items without a previous bridge are historical — skip
            else:
                result.skipped += 1

        # Sync comments if a fact exists/was created
        if include_comments and fact_id:
            await self._sync_comments(repo, number, fact_id)

    # ─── Store / Crystallize ─────────────────────────────────────────

    async def _store_bridge(
        self,
        item: dict[str, Any],
        repo: str,
        key: str,
        is_pr: bool,
    ) -> int:
        """Store an open issue/PR as a bridge fact."""
        labels = [lb["name"] for lb in item.get("labels", [])]
        title = item["title"]
        body = (item.get("body") or "")[:500]

        content = (
            f"[GitHub {'PR' if is_pr else 'Issue'}] {repo}#{item['number']}: "
            f"{title}. {body}".strip()
        )

        meta = {
            "github_key": key,
            "github_url": item["html_url"],
            "github_number": item["number"],
            "github_repo": repo,
            "github_state": item["state"],
            "github_type": "pr" if is_pr else "issue",
            "github_labels": labels,
            "github_updated_at": item.get("updated_at", ""),
            "synced_at": now_iso(),
        }

        fact_id = await self._engine.store(
            project=_PROJECT,
            content=content,
            fact_type="bridge",
            tags=["github", "pr" if is_pr else "issue", repo.split("/")[-1]],
            confidence="C4",
            source=_SOURCE,
            meta=meta,
        )
        logger.info("🌉 Stored bridge #%d: %s#%d", fact_id, repo, item["number"])
        return fact_id

    async def _crystallize_decision(
        self,
        item: dict[str, Any],
        repo: str,
        existing_fact_id: int,
    ) -> int:
        """Crystallize a closed issue: deprecate bridge → store decision."""
        title = item["title"]
        closed_at = item.get("closed_at", now_iso())

        # Deprecate the bridge fact
        await self._engine.deprecate(
            existing_fact_id,
            reason=f"crystallized:closed:{repo}#{item['number']}",
        )

        # Store as decision
        content = f"[GitHub Resolved] {repo}#{item['number']}: {title}. Closed at {closed_at}."
        meta = {
            "github_key": _github_key(repo, item["number"]),
            "github_url": item["html_url"],
            "github_number": item["number"],
            "github_repo": repo,
            "github_state": "closed",
            "github_type": "pr" if "pull_request" in item else "issue",
            "previous_bridge_id": existing_fact_id,
            "closed_at": closed_at,
            "crystallized_at": now_iso(),
        }

        fact_id = await self._engine.store(
            project=_PROJECT,
            content=content,
            fact_type="decision",
            tags=["github", "crystallized", repo.split("/")[-1]],
            confidence="C5",
            source=_SOURCE,
            meta=meta,
        )
        logger.info(
            "💎 Crystallized decision #%d from bridge #%d: %s#%d",
            fact_id,
            existing_fact_id,
            repo,
            item["number"],
        )
        return fact_id

    async def _sync_comments(self, repo: str, number: int, parent_id: int) -> None:
        """Fetch and store comments for an issue/PR."""
        try:
            comments = await self.get_issue_comments(repo, number)
            for comment in comments:
                # Use a combined key for comments: repo#issue#comment_id
                c_key = f"{repo}#{number}#{comment['id']}"
                c_hash = hashlib.sha256(c_key.encode()).hexdigest()[:16]

                # Check if comment already exists as a fact (light check)
                # For now, we just store it if it's new in the last sync
                # Ideally we'd have a comment index too
                await self._store_comment(comment, repo, number, parent_id, c_hash)
        except Exception as e:
            logger.debug("Failed to sync comments for %s#%d: %s", repo, number, e)

    async def _store_comment(
        self,
        comment: dict[str, Any],
        repo: str,
        number: int,
        parent_id: int,
        key: str,
    ) -> int:
        """Store a GitHub comment as a bridge fact."""
        user = comment.get("user", {}).get("login", "unknown")
        body = (comment.get("body") or "")[:500]

        content = f"[GitHub Comment] {repo}#{number} by @{user}: {body}".strip()

        meta = {
            "github_comment_id": comment["id"],
            "github_user": user,
            "github_url": comment["html_url"],
            "parent_fact_id": parent_id,
            "github_key": key,
            "synced_at": now_iso(),
        }

        fact_id = await self._engine.store(
            project=_PROJECT,
            content=content,
            fact_type="bridge",
            tags=["github", "comment", repo.split("/")[-1]],
            confidence="C4",
            source=_SOURCE,
            meta=meta,
        )
        return fact_id

    # ─── Dedup Index ─────────────────────────────────────────────────

    async def _load_existing_keys(self) -> dict[str, int]:
        """Load all github_key → fact_id mappings from active bridge facts.

        Returns a dict for O(1) dedup during sync.
        """
        index: dict[str, int] = {}
        try:
            conn = await self._engine.get_conn()
            cursor = await conn.execute(
                "SELECT id, metadata FROM facts "
                "WHERE fact_type = 'bridge' AND is_tombstoned = 0 "
                "AND source = ?",
                (_SOURCE,),
            )
            rows = await cursor.fetchall()

            from cortex.crypto import get_default_encrypter

            enc = get_default_encrypter()

            for row in rows:
                fact_id = row[0]
                try:
                    meta_dict = enc.decrypt_json(row[1], tenant_id="default")
                    if isinstance(meta_dict, dict) and "github_key" in meta_dict:
                        index[meta_dict["github_key"]] = fact_id
                except (ValueError, TypeError, OSError):
                    continue  # Skip corrupted or non-GitHub entries
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load existing GitHub keys: %s", exc)
            raise

        logger.debug("Loaded %d existing GitHub bridge keys", len(index))
        return index
