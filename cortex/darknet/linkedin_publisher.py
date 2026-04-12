"""LinkedIn Publisher — Sovereign Posts API Integration.

Flow: markdown -> preview -> human approval -> POST /rest/posts
Auth: OAuth 2.0 (3-legged, w_member_social or w_organization_social)
API:  LinkedIn Community Management API v2 (2026)

Confidence: C5-REAL — verified against official LinkedIn docs 2026-04-07
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger("cortex.darknet.linkedin")

# ── Constants ──────────────────────────────────────────────────────────────────
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
POSTS_URL = "https://api.linkedin.com/rest/posts"
IMAGES_URL = "https://api.linkedin.com/rest/images"
ORGANIZATIONS_URL = "https://api.linkedin.com/rest/organizations"
ORGANIZATION_AUTHORIZATIONS_URL = "https://api.linkedin.com/rest/organizationAuthorizations"
PERSON_URL = "https://api.linkedin.com/v2/userinfo"
DEFAULT_LINKEDIN_API_VERSION = "202510"

LINKEDIN_POSTS_SCOPE = "w_member_social"
LINKEDIN_ORG_SCOPE = "w_organization_social"


@dataclass
class LinkedInConfig:
    """OAuth credentials loaded from environment."""

    client_id: str
    client_secret: str
    redirect_uri: str
    access_token: str = ""
    token_expiry: float = 0.0
    api_version: str = DEFAULT_LINKEDIN_API_VERSION
    member_urn: str = ""
    organization_urn: str = ""
    actor_urn: str = ""

    @classmethod
    def from_env(cls) -> LinkedInConfig:
        """Load config from environment variables. Raises if required vars missing."""
        required = {
            "LINKEDIN_CLIENT_ID": "client_id",
            "LINKEDIN_CLIENT_SECRET": "client_secret",
            "LINKEDIN_REDIRECT_URI": "redirect_uri",
        }
        kwargs: dict = {}
        missing = []
        for env_var, field_name in required.items():
            val = os.environ.get(env_var, "")
            if not val:
                missing.append(env_var)
            kwargs[field_name] = val

        if missing:
            raise OSError(
                f"Missing LinkedIn env vars: {', '.join(missing)}\n"
                "Set them in .env or export before running."
            )

        kwargs["access_token"] = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
        kwargs["token_expiry"] = float(os.environ.get("LINKEDIN_TOKEN_EXPIRY", "0"))
        kwargs["api_version"] = os.environ.get(
            "LINKEDIN_API_VERSION",
            DEFAULT_LINKEDIN_API_VERSION,
        )
        kwargs["member_urn"] = os.environ.get("LINKEDIN_MEMBER_URN", "")
        kwargs["organization_urn"] = normalize_organization_urn(
            os.environ.get("LINKEDIN_ORGANIZATION_URN", "")
        )
        kwargs["actor_urn"] = os.environ.get("LINKEDIN_ACTOR_URN", "")

        if not kwargs["member_urn"] and kwargs["actor_urn"].startswith("urn:li:person:"):
            kwargs["member_urn"] = kwargs["actor_urn"]
        if not kwargs["organization_urn"] and kwargs["actor_urn"].startswith(
            "urn:li:organization:"
        ):
            kwargs["organization_urn"] = kwargs["actor_urn"]
        return cls(**kwargs)

    def is_token_valid(self) -> bool:
        """Token is valid if present and not within 60s of expiry."""
        return bool(self.access_token) and time.time() < (self.token_expiry - 60)

    def resolved_actor_urn(self, prefer_organization: bool = False) -> str:
        """Resolve the effective author URN for publishing."""
        if prefer_organization and self.organization_urn:
            return self.organization_urn
        if self.organization_urn:
            return self.organization_urn
        if self.member_urn:
            return self.member_urn
        return self.actor_urn


def _linkedin_headers(
    *,
    access_token: str,
    api_version: str,
    include_json: bool = False,
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": api_version,
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def normalize_organization_urn(value: str | None) -> str:
    """Normalize organization identifiers into `urn:li:organization:{id}` form."""
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.isdigit():
        return f"urn:li:organization:{raw}"
    if raw.startswith("urn:li:organizationBrand:"):
        return raw.replace("urn:li:organizationBrand:", "urn:li:organization:", 1)
    return raw


@dataclass
class ArticlePost:
    """Structured post payload for a linked-article share."""

    title: str
    description: str
    article_url: str
    commentary: str  # The text body of the LinkedIn post
    thumbnail_url: str = ""  # Optional: pre-uploaded image URN or external URL
    source_file: str = ""
    git_sha: str = ""

    def content_hash(self, actor_urn: str = "") -> str:
        """Deterministic dedup key scoped by actor + article + source revision."""
        raw = f"{actor_urn}:{self.article_url}:{self.git_sha}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def build_payload(self, actor_urn: str) -> dict:
        """Build the LinkedIn /rest/posts payload."""
        payload: dict = {
            "author": actor_urn,
            "commentary": self.commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": self.article_url,
                    "title": self.title,
                    "description": self.description,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        # Attach thumbnail if provided (must be a LinkedIn image URN)
        if self.thumbnail_url.startswith("urn:li:image:"):
            payload["content"]["article"]["thumbnail"] = self.thumbnail_url

        return payload


# ── OAuth Helpers ──────────────────────────────────────────────────────────────


def build_auth_url(config: LinkedInConfig, scope: str = LINKEDIN_POSTS_SCOPE) -> tuple[str, str]:
    """Build the browser authorization URL for the member to visit."""
    state = hashlib.sha256(os.urandom(16)).hexdigest()[:12]
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "state": state,
        "scope": scope,
    }
    return f"{AUTH_URL}?{urlencode(params)}", state


def exchange_code_for_token(
    config: LinkedInConfig,
    code: str,
) -> tuple[str, float]:
    """Exchange authorization code for access_token. Returns (token, expiry_epoch)."""
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expiry = time.time() + int(data.get("expires_in", 5184000))
    return token, expiry


def fetch_member_urn(access_token: str, api_version: str) -> str:
    """Fetch the authenticated member's URN via /v2/userinfo."""
    resp = httpx.get(
        PERSON_URL,
        headers=_linkedin_headers(access_token=access_token, api_version=api_version),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    # userinfo returns 'sub' as the member ID
    sub = data.get("sub", "")
    return f"urn:li:person:{sub}"


def fetch_actor_urn(access_token: str) -> str:
    """Backward-compatible alias for the member URN lookup."""
    return fetch_member_urn(access_token, DEFAULT_LINKEDIN_API_VERSION)


def _extract_organization_urn(payload: object) -> str:
    if isinstance(payload, dict):
        candidate_fields = (
            payload.get("$URN"),
            payload.get("organization"),
            payload.get("organizationTarget"),
            payload.get("urn"),
            payload.get("entityUrn"),
        )
        for candidate in candidate_fields:
            normalized = normalize_organization_urn(str(candidate or ""))
            if normalized.startswith("urn:li:organization:"):
                return normalized

        org_id = payload.get("id")
        normalized_id = normalize_organization_urn(str(org_id or ""))
        if normalized_id.startswith("urn:li:organization:"):
            return normalized_id

        for value in payload.values():
            found = _extract_organization_urn(value)
            if found:
                return found

    if isinstance(payload, list):
        for item in payload:
            found = _extract_organization_urn(item)
            if found:
                return found

    return ""


def resolve_organization_urn(
    access_token: str,
    api_version: str,
    *,
    organization_urn: str = "",
    organization_id: str = "",
    organization_vanity: str = "",
) -> str:
    """Resolve an organization identifier into a canonical URN."""
    if organization_urn:
        return normalize_organization_urn(organization_urn)
    if organization_id:
        return normalize_organization_urn(organization_id)
    if not organization_vanity:
        return ""

    resp = httpx.get(
        ORGANIZATIONS_URL,
        params={"q": "vanityName", "vanityName": organization_vanity},
        headers=_linkedin_headers(access_token=access_token, api_version=api_version),
        timeout=15,
    )
    resp.raise_for_status()
    resolved = _extract_organization_urn(resp.json())
    if not resolved:
        raise RuntimeError(
            f"Could not resolve LinkedIn organization vanity '{organization_vanity}' to a URN."
        )
    return resolved


def check_organization_post_permission(
    access_token: str,
    api_version: str,
    member_urn: str,
    organization_urn: str,
) -> dict[str, object]:
    """Best-effort check for `ORGANIC_SHARE_CREATE` on an organization."""
    encoded_member = quote(member_urn, safe="")
    encoded_org = quote(organization_urn, safe="")
    url = (
        f"{ORGANIZATION_AUTHORIZATIONS_URL}/"
        f"(impersonator:{encoded_member},organization:{encoded_org},"
        "action:(organizationContentAuthorizationAction:(actionType:ORGANIC_SHARE_CREATE)))"
    )
    resp = httpx.get(
        url,
        headers=_linkedin_headers(access_token=access_token, api_version=api_version),
        timeout=15,
    )

    if resp.status_code in {401, 403}:
        return {
            "ok": None,
            "reasons": [],
            "error": (
                "Could not validate organization posting permissions via "
                f"organizationAuthorizations (HTTP {resp.status_code})."
            ),
        }

    resp.raise_for_status()
    data = resp.json()
    status = data.get("status", {})
    approved = any(key.endswith("Approved") for key in status)

    reasons: list[str] = []
    for key, value in status.items():
        if key.endswith("Denied") and isinstance(value, dict):
            denial_reasons = value.get("reasons", [])
            if isinstance(denial_reasons, list):
                reasons.extend(str(reason) for reason in denial_reasons)

    return {"ok": approved, "reasons": reasons, "error": None}


# ── Publisher ──────────────────────────────────────────────────────────────────


class LinkedInPublisher:
    """Sovereign LinkedIn post publisher. Dry-run by default."""

    def __init__(self, config: LinkedInConfig, dry_run: bool = True) -> None:
        self.config = config
        self.dry_run = dry_run

    def publish(self, post: ArticlePost) -> dict:
        """
        Publish an ArticlePost to LinkedIn.

        Returns:
            dict with keys: success, post_id, url, dry_run, error
        """
        if not self.config.is_token_valid():
            raise RuntimeError(
                "LinkedIn access token missing or expired.\nRun: cortex linkedin auth"
            )

        actor_urn = self.config.resolved_actor_urn()
        if not actor_urn:
            raise RuntimeError(
                "LinkedIn actor URN not set.\n"
                "Set LINKEDIN_MEMBER_URN for personal posts or "
                "LINKEDIN_ORGANIZATION_URN for company posts.\n"
                "Run: cortex linkedin auth"
            )

        payload = post.build_payload(actor_urn)

        if self.dry_run:
            logger.info("[DRY-RUN] Would POST to %s", POSTS_URL)
            return {
                "success": True,
                "post_id": f"DRY-{post.content_hash(actor_urn)}",
                "url": None,
                "dry_run": True,
                "payload": payload,
                "error": None,
            }

        resp = httpx.post(
            POSTS_URL,
            json=payload,
            headers=_linkedin_headers(
                access_token=self.config.access_token,
                api_version=self.config.api_version,
                include_json=True,
            ),
            timeout=30,
        )

        if resp.status_code == 201:
            post_id = resp.headers.get("x-restli-id", "")
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None
            return {
                "success": True,
                "post_id": post_id,
                "url": post_url,
                "dry_run": False,
                "error": None,
            }

        # Non-201 = error
        try:
            err_body = resp.json()
        except Exception:
            err_body = resp.text

        logger.error("LinkedIn API error %s: %s", resp.status_code, err_body)
        return {
            "success": False,
            "post_id": None,
            "url": None,
            "dry_run": False,
            "error": f"HTTP {resp.status_code}: {err_body}",
        }


# ── Markdown Parser ────────────────────────────────────────────────────────────


def parse_markdown_article(md_path: Path, article_url: str) -> ArticlePost:
    """
    Parse a markdown file into an ArticlePost.

    Frontmatter fields used: title, description
    Body: Used as-is for commentary (LinkedIn post text).
    The article_url is the deployed URL of the article (required).
    """
    text = md_path.read_text(encoding="utf-8")

    # Extract frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    frontmatter: dict = {}
    body = text
    if fm_match:
        fm_text = fm_match.group(1)
        body = text[fm_match.end() :]
        for line in fm_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                frontmatter[k.strip()] = v.strip().strip('"')

    title = frontmatter.get("title", md_path.stem.replace("-", " ").title())
    description = frontmatter.get("description", "")
    thumbnail_urn = frontmatter.get("linkedin_thumbnail_urn", "") or frontmatter.get(
        "thumbnail_urn",
        "",
    )

    commentary = (
        frontmatter.get("linkedin_commentary", "") or frontmatter.get("linkedin_text", "")
    ).strip()
    if not commentary:
        # LinkedIn commentary = plain text, max ~3000 chars
        commentary = _strip_markdown_for_linkedin(body).strip()
    if len(commentary) > 2900:
        commentary = commentary[:2897] + "..."

    # Git SHA for dedup
    try:
        import subprocess

        git_sha = subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", str(md_path)],
            cwd=md_path.parent,
            text=True,
        ).strip()[:12]
    except Exception:
        git_sha = hashlib.sha256(commentary.encode()).hexdigest()[:12]

    return ArticlePost(
        title=title,
        description=description,
        article_url=article_url,
        commentary=commentary,
        thumbnail_url=thumbnail_urn,
        source_file=str(md_path),
        git_sha=git_sha,
    )


def _strip_markdown_for_linkedin(text: str) -> str:
    """Light markdown → plain text for LinkedIn commentary."""
    # Remove frontmatter if any
    text = re.sub(r"^---.*?---\s*\n", "", text, flags=re.DOTALL)
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove headers (keep text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Collapse blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
