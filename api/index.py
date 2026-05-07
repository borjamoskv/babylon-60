"""Serverless FastAPI entrypoint for the CORTEX SaaS checkout API.

This serverless surface is intentionally small: it exposes health endpoints and
creates hosted billing sessions without loading the full local-first CORTEX
engine inside the function runtime.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

__all__ = [
    "CheckoutRequest",
    "ProofMarkRequest",
    "app",
]

logger = logging.getLogger("uvicorn.error")

DEFAULT_PUBLIC_ORIGIN = "https://cortexpersist.com"
DEFAULT_ALLOWED_ORIGINS = (
    "https://cortexpersist.com",
    "https://www.cortexpersist.com",
    "https://cortexpersist.dev",
    "https://cortexpersist.org",
)
PROOF_MARK_KEY = "cortex:proof-marks:v1"
PROOF_MARK_SEQUENCE_KEY = "cortex:proof-marks:sequence:v1"
PROOF_MARK_RATE_PREFIX = "cortex:proof-marks:rate:v1"
PROOF_MARK_LIMIT = 192
PROOF_MARK_RATE_LIMIT = 120
PROOF_MARK_HUES = ("#d7ff5f", "#6ba6ff", "#38d39f", "#ffb45c")
MEDIA_MARK_KEY = "media:curation:marks:v1"
MEDIA_MARK_SEQUENCE_KEY = "media:curation:marks:sequence:v1"
MEDIA_MARK_RATE_PREFIX = "media:curation:marks:rate:v1"
MEDIA_MARK_LIMIT = 260
MEDIA_MARK_RATE_LIMIT = 180
MEDIA_MARK_HUES = ("#d6b25e", "#1db954", "#ff3b30", "#88d9ff", "#f2efe9")
ALLOWED_PROOF_MARK_SECTIONS = {
    "hero",
    "compliance",
    "workflow",
    "evidence",
    "crypto-nft-evidence",
    "use-cases",
    "features",
    "api-surface",
    "agent-control",
    "research",
    "crypto-tax",
    "fiscal-checklist",
    "use-cases-live",
    "reference-agent",
    "compare",
    "faq",
    "deployment",
    "pricing",
    "start",
    "page",
}
ALLOWED_MEDIA_MARK_SECTIONS = {"top", "playlist", "archivo", "criterio", "page"}


class CheckoutRequest(BaseModel):
    """Browser payload for hosted billing checkout session creation."""

    plan: Literal["pro", "team"] = "pro"
    customer_email: str | None = Field(default=None, max_length=320)
    success_url: str | None = Field(default=None, max_length=2048)
    cancel_url: str | None = Field(default=None, max_length=2048)
    ui_mode: Literal["hosted", "embedded"] = "hosted"


class ProofMarkRequest(BaseModel):
    """Anonymous browser payload for collective proof marks.

    Coordinates are already coarse page ratios in the client, and are quantized
    again server-side before storage. The API intentionally accepts no identity
    fields such as IP, email, user agent, or visitor ID.
    """

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    section: str = Field(default="page", min_length=1, max_length=64)


app = FastAPI(
    title="CORTEX SaaS API",
    description="Server-side checkout API for CORTEX hosted plans.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)


def _csv_env(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def _allowed_origins() -> tuple[str, ...]:
    configured = _csv_env("CORTEX_CHECKOUT_ALLOWED_ORIGINS") or _csv_env(
        "CORTEX_ALLOWED_ORIGINS"
    )
    if configured:
        return tuple(configured)
    return DEFAULT_ALLOWED_ORIGINS


def _public_origin() -> str:
    origin = os.environ.get("CORTEX_PUBLIC_ORIGIN", DEFAULT_PUBLIC_ORIGIN).strip().rstrip("/")
    if not origin:
        return DEFAULT_PUBLIC_ORIGIN
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.netloc:
        return DEFAULT_PUBLIC_ORIGIN
    return f"{parsed.scheme}://{parsed.netloc}"


def _origin_for(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _safe_return_url(candidate: str | None, fallback_path: str) -> str:
    fallback = _public_origin() + fallback_path
    if not candidate:
        return fallback
    origin = _origin_for(candidate)
    if origin and origin in _allowed_origins():
        return candidate
    return fallback


def _price_table() -> dict[str, str]:
    raw = os.environ.get("STRIPE_PRICE_TABLE", "")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="Billing price table is invalid") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=503, detail="Billing price table is invalid")
    return {str(key): str(price_id) for key, price_id in value.items() if price_id}


def _create_billing_checkout(session_kwargs: dict[str, Any]) -> dict[str, Any]:
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise HTTPException(status_code=503, detail="Billing checkout is not configured")

    try:
        import stripe
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Billing SDK is not installed") from exc

    stripe.api_key = secret_key
    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.StripeError as exc:  # type: ignore[attr-defined]
        logger.warning("Billing checkout creation failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="Billing checkout is unavailable") from exc

    return {
        "client_secret": getattr(session, "client_secret", None),
        "session_id": session.id,
        "url": session.url,
    }


def _redis_rest_config() -> tuple[str, str] | None:
    url = (
        os.environ.get("UPSTASH_REDIS_REST_URL")
        or os.environ.get("KV_REST_API_URL")
        or ""
    ).strip().rstrip("/")
    token = (
        os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        or os.environ.get("KV_REST_API_TOKEN")
        or ""
    ).strip()
    if not url or not token:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return url, token


async def _redis_command(command: list[Any]) -> Any:
    config = _redis_rest_config()
    if not config:
        raise HTTPException(status_code=503, detail="Proof mark storage is not configured")

    url, token = config
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=command,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Proof mark storage command failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Proof mark storage is unavailable") from exc

    if isinstance(payload, dict) and payload.get("error"):
        logger.warning("Proof mark storage returned an error")
        raise HTTPException(status_code=503, detail="Proof mark storage is unavailable")
    return payload.get("result") if isinstance(payload, dict) else payload


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _proof_mark_rate_limit() -> int:
    raw = os.environ.get("CORTEX_PROOF_MARKS_PER_MINUTE", "").strip()
    if not raw:
        return PROOF_MARK_RATE_LIMIT
    return max(1, min(_coerce_int(raw, PROOF_MARK_RATE_LIMIT), 600))


def _media_mark_rate_limit() -> int:
    raw = os.environ.get("MEDIA_MARKS_PER_MINUTE", "").strip()
    if not raw:
        return MEDIA_MARK_RATE_LIMIT
    return max(1, min(_coerce_int(raw, MEDIA_MARK_RATE_LIMIT), 900))


async def _enforce_rate_limit(prefix: str, limit: int, detail: str) -> None:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = f"{prefix}:{minute}"
    count = _coerce_int(await _redis_command(["INCR", key]))
    if count == 1:
        await _redis_command(["EXPIRE", key, 90])
    if count > limit:
        raise HTTPException(status_code=429, detail=detail)


async def _enforce_global_proof_mark_rate_limit() -> None:
    await _enforce_rate_limit(
        PROOF_MARK_RATE_PREFIX,
        _proof_mark_rate_limit(),
        "Proof mark rate limit exceeded",
    )


async def _enforce_media_mark_rate_limit() -> None:
    await _enforce_rate_limit(
        MEDIA_MARK_RATE_PREFIX,
        _media_mark_rate_limit(),
        "Media mark rate limit exceeded",
    )


def _coarse_ratio(value: float, steps: int) -> float:
    return round(value * steps) / steps


def _clean_section(section: str) -> str:
    normalized = section.strip().lower()
    if normalized in ALLOWED_PROOF_MARK_SECTIONS:
        return normalized
    return "page"


def _clean_media_section(section: str) -> str:
    normalized = section.strip().lower()
    if normalized in ALLOWED_MEDIA_MARK_SECTIONS:
        return normalized
    return "page"


def _current_hour() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(minute=0, second=0, microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _proof_mark_hash(
    sequence: int,
    section: str,
    x: float,
    y: float,
    timestamp: str,
    *,
    namespace: str = "cortex",
) -> str:
    material = f"{namespace}|{sequence}|{section}|{x:.4f}|{y:.4f}|{timestamp}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _proof_mark_from_body(body: ProofMarkRequest, sequence: int) -> dict[str, Any]:
    section = _clean_section(body.section)
    x = _coarse_ratio(body.x, 48)
    y = _coarse_ratio(body.y, 160)
    timestamp = _current_hour()
    proof_hash = _proof_mark_hash(sequence, section, x, y, timestamp)
    return {
        "x": x,
        "y": y,
        "section": section,
        "t": timestamp,
        "hue": PROOF_MARK_HUES[sequence % len(PROOF_MARK_HUES)],
        "hash": proof_hash,
    }


def _media_mark_from_body(body: ProofMarkRequest, sequence: int) -> dict[str, Any]:
    section = _clean_media_section(body.section)
    x = _coarse_ratio(body.x, 56)
    y = _coarse_ratio(body.y, 180)
    timestamp = _current_hour()
    proof_hash = _proof_mark_hash(
        sequence,
        section,
        x,
        y,
        timestamp,
        namespace="media-curation",
    )
    return {
        "x": x,
        "y": y,
        "section": section,
        "t": timestamp,
        "hue": MEDIA_MARK_HUES[sequence % len(MEDIA_MARK_HUES)],
        "hash": proof_hash,
    }


def _decode_proof_mark(
    value: Any,
    default_hue: str = PROOF_MARK_HUES[0],
) -> dict[str, Any] | None:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if not isinstance(value, str):
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    if not {"x", "y", "section", "t", "hash"}.issubset(decoded):
        return None
    return {
        "x": decoded["x"],
        "y": decoded["y"],
        "section": decoded["section"],
        "t": decoded["t"],
        "hue": decoded.get("hue", default_hue),
        "hash": decoded["hash"],
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_allowed_origins()),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/")
@app.get("/health")
@app.get("/v1/health")
async def health() -> dict[str, str]:
    """Return a minimal health response for serverless and edge probes."""

    return {"service": "cortex-saas-api", "status": "ok"}


@app.get("/v1/proof-marks")
async def list_proof_marks(limit: int = Query(default=96, ge=1, le=PROOF_MARK_LIMIT)) -> dict[str, Any]:
    """Return recent anonymous proof marks.

    The endpoint reads only public mark payloads. It does not inspect or return
    request identity.
    """

    raw_marks = await _redis_command(["LRANGE", PROOF_MARK_KEY, 0, limit - 1])
    if not isinstance(raw_marks, list):
        raw_marks = []
    marks = [_decode_proof_mark(item) for item in raw_marks]
    return {"marks": [mark for mark in reversed(marks) if mark is not None]}


@app.post("/v1/proof-marks")
async def create_proof_mark(body: ProofMarkRequest) -> dict[str, Any]:
    """Persist an anonymous collective proof mark with no identity fields."""

    await _enforce_global_proof_mark_rate_limit()
    sequence = _coerce_int(await _redis_command(["INCR", PROOF_MARK_SEQUENCE_KEY]), 1)
    mark = _proof_mark_from_body(body, sequence)
    encoded = json.dumps(mark, separators=(",", ":"), sort_keys=True)
    await _redis_command(["LPUSH", PROOF_MARK_KEY, encoded])
    await _redis_command(["LTRIM", PROOF_MARK_KEY, 0, PROOF_MARK_LIMIT - 1])
    return mark


@app.get("/v1/media/marks")
async def list_media_marks(
    limit: int = Query(default=120, ge=1, le=MEDIA_MARK_LIMIT),
) -> dict[str, Any]:
    """Return recent anonymous media curation marks."""

    raw_marks = await _redis_command(["LRANGE", MEDIA_MARK_KEY, 0, limit - 1])
    if not isinstance(raw_marks, list):
        raw_marks = []
    marks = [_decode_proof_mark(item, MEDIA_MARK_HUES[0]) for item in raw_marks]
    return {"marks": [mark for mark in reversed(marks) if mark is not None]}


@app.post("/v1/media/marks")
async def create_media_mark(body: ProofMarkRequest) -> dict[str, Any]:
    """Persist an anonymous media curation mark with no identity fields."""

    await _enforce_media_mark_rate_limit()
    sequence = _coerce_int(await _redis_command(["INCR", MEDIA_MARK_SEQUENCE_KEY]), 1)
    mark = _media_mark_from_body(body, sequence)
    encoded = json.dumps(mark, separators=(",", ":"), sort_keys=True)
    await _redis_command(["LPUSH", MEDIA_MARK_KEY, encoded])
    await _redis_command(["LTRIM", MEDIA_MARK_KEY, 0, MEDIA_MARK_LIMIT - 1])
    return mark


@app.post("/v1/billing/checkout")
async def create_checkout_session(body: CheckoutRequest) -> dict[str, Any]:
    """Create a hosted billing checkout session for a supported plan."""

    price_id = _price_table().get(body.plan)
    if not price_id:
        raise HTTPException(status_code=503, detail="Billing plan is not configured")

    session_kwargs: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "metadata": {"plan": body.plan},
    }

    success_url = _safe_return_url(body.success_url, "/success/")
    if body.ui_mode == "embedded":
        session_kwargs["ui_mode"] = "embedded"
        session_kwargs["return_url"] = success_url
    else:
        session_kwargs["success_url"] = success_url
        session_kwargs["cancel_url"] = _safe_return_url(body.cancel_url, "/cancel/")

    if body.customer_email:
        session_kwargs["customer_email"] = body.customer_email

    return _create_billing_checkout(session_kwargs)
