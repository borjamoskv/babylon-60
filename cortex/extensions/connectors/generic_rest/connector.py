"""generic_rest/connector.py — GenericRESTConnector

CORTEX connector for any JSON REST API configurable via ConnectorConfig.extra.
No SDK dependencies — pure aiohttp + keyring.

Config (ConnectorConfig.extra):
    {
        "auth_type": "bearer" | "basic" | "api_key" | "none",
        "endpoints": [
            {
                "path": "/api/v1/accounts",
                "method": "GET",
                "params": {"limit": "100"},
                "headers": {"X-Custom": "value"},
                "data_key": "results",           # JSON path to records list
                "next_page_key": "next",         # key for next page URL/cursor
                "next_page_param": "page",       # query param to increment
                "label": "accounts",
                "fact_type": "knowledge",
                "content_template": "{name} | {email} | {status}",
                "tags": ["source:myapp"],
            }
        ]
    }

Credentials via keyring:
    service = config.keyring_service
    username = "api_key"     (for api_key auth)
    username = "username"    (for basic auth)
    username = "password"    (for basic auth)
    username = "token"       (for bearer auth)
"""

from __future__ import annotations

import base64
import logging
import string
from typing import Any

import aiohttp
import keyring

from cortex.extensions.connectors.base import BaseConnector, ConnectorConfig
from cortex.extensions.connectors.registry import register_connector
from cortex.extensions.interfaces.engine import EngineProtocol

logger = logging.getLogger(__name__)


class GenericRESTConnector(BaseConnector):
    """CORTEX connector for arbitrary JSON REST APIs.

    Declare endpoints in ConnectorConfig.extra['endpoints'].
    Auth credentials are read from keyring at connect() time.
    Supports: Bearer token, Basic auth, API key header, and no-auth.
    """

    def __init__(self, config: ConnectorConfig, engine: EngineProtocol) -> None:
        super().__init__(config, engine)
        self._session: aiohttp.ClientSession | None = None
        self._auth_headers: dict[str, str] = {}
        self._endpoints: list[dict[str, Any]] = config.extra.get("endpoints", [])
        self._auth_type: str = config.extra.get("auth_type", "bearer")

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Build auth headers from keyring credentials."""
        svc = self.config.keyring_service
        auth_type = self._auth_type

        if auth_type == "bearer":
            token = keyring.get_password(svc, "token") or ""
            if not token:
                logger.warning("[GenericRESTConnector] No bearer token in keyring('%s', 'token')", svc)
            self._auth_headers = {"Authorization": f"Bearer {token}"}

        elif auth_type == "basic":
            username = keyring.get_password(svc, "username") or ""
            password = keyring.get_password(svc, "password") or ""
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            self._auth_headers = {"Authorization": f"Basic {encoded}"}

        elif auth_type == "api_key":
            api_key = keyring.get_password(svc, "api_key") or ""
            key_header = self.config.extra.get("api_key_header", "X-API-Key")
            self._auth_headers = {key_header: api_key}

        elif auth_type == "none":
            self._auth_headers = {}

        else:
            logger.warning("[GenericRESTConnector] Unknown auth_type '%s' — using no-auth", auth_type)
            self._auth_headers = {}

        self._session = aiohttp.ClientSession(
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        logger.info(
            "[GenericRESTConnector] connected → base=%s auth=%s endpoints=%d",
            self.config.base_url, auth_type, len(self._endpoints),
        )

    async def disconnect(self) -> None:
        """Discard auth headers and close session."""
        self._auth_headers = {}
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        logger.debug("[GenericRESTConnector] session closed")

    # ── Pull ─────────────────────────────────────────────────────────────────

    async def pull(self) -> list[dict[str, Any]]:
        """Fetch all configured endpoints."""
        if not self._session:
            raise RuntimeError("Not connected — call connect() first")

        all_records: list[dict[str, Any]] = []

        for ep in self._endpoints:
            try:
                records = await self._pull_endpoint(ep)
                all_records.extend(records)
            except Exception as exc:
                logger.error(
                    "[GenericRESTConnector] endpoint '%s' failed: %s",
                    ep.get("path", "?"), exc,
                )
                continue

        return all_records

    async def _pull_endpoint(self, ep: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch a single endpoint configuration with optional pagination."""
        path = ep.get("path", "")
        method = ep.get("method", "GET").upper()
        params = dict(ep.get("params", {}))
        extra_headers = ep.get("headers", {})
        data_key = ep.get("data_key", "")
        next_page_key = ep.get("next_page_key", "")
        next_page_param = ep.get("next_page_param", "")
        label = ep.get("label", path.strip("/").replace("/", "_") or "generic")
        fact_type = ep.get("fact_type", "knowledge")

        url = f"{self.config.base_url.rstrip('/')}{path}"
        headers = {**self._auth_headers, **extra_headers}
        all_records: list[dict[str, Any]] = []
        page = 1

        while True:
            async with self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            # Extract records from response
            if data_key:
                records = data.get(data_key, [])
                if not isinstance(records, list):
                    records = [records]
            elif isinstance(data, list):
                records = data
            else:
                records = [data]

            for r in records:
                if isinstance(r, dict):
                    r["_label"] = label
                    r["_fact_type"] = fact_type
                    r["_endpoint_path"] = path
            all_records.extend([r for r in records if isinstance(r, dict)])

            # Pagination
            if next_page_key and isinstance(data, dict):
                next_val = data.get(next_page_key)
                if not next_val:
                    break
                if next_page_param:
                    page += 1
                    params[next_page_param] = str(page)
                else:
                    # next_val is a full URL
                    url = str(next_val)
                    params = {}
            else:
                break

        logger.info(
            "[GenericRESTConnector] %s → %d records", path, len(all_records)
        )
        return all_records

    # ── Transform ────────────────────────────────────────────────────────────

    async def transform(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Map a generic REST record to a CORTEX fact payload."""
        label = record.get("_label", "generic")
        fact_type = record.get("_fact_type", "knowledge")
        path = record.get("_endpoint_path", "/")

        # Find endpoint config for this label (for content_template and tags)
        ep_config = next(
            (e for e in self._endpoints if e.get("label") == label), {}
        )

        clean = {k: v for k, v in record.items() if not k.startswith("_")}
        if not clean:
            return None

        content = self._render_content(ep_config, label, clean)
        if not content:
            return None

        # ID detection: look for common PK field names
        pk = (
            clean.get("id")
            or clean.get("Id")
            or clean.get("ID")
            or clean.get("uuid")
            or clean.get("key")
            or "unknown"
        )

        tags = [
            f"rest:{label}",
            f"endpoint:{path.strip('/').replace('/', '_')[:30]}",
            "connector:generic_rest",
            "connector:auto",
        ]
        # Merge endpoint-level tags
        tags.extend(ep_config.get("tags", []))

        return {
            "content": content,
            "fact_type": fact_type,
            "tags": tags,
            "confidence": "C3",
            "source": f"{self.config.base_url.rstrip('/')}{path}/{pk}",
            "meta": {
                "record_id": str(pk),
                "label": label,
                "endpoint": path,
                "connector": self.config.connector_id,
            },
        }

    def _render_content(
        self,
        ep_config: dict[str, Any],
        label: str,
        record: dict[str, Any],
    ) -> str:
        template: str = ep_config.get("content_template", "")
        if template:
            try:
                # Safe string.Template substitution — won't raise on missing keys
                return string.Template(template).safe_substitute(record)
            except Exception:
                pass

        # Fallback: top 10 fields as "key: value" pairs
        pairs = " | ".join(
            f"{k}: {v}"
            for k, v in list(record.items())[:10]
            if v is not None
        )
        return f"{label}: {pairs}" if pairs else ""


# Auto-register on import
register_connector("generic_rest", GenericRESTConnector)
