"""sap/client.py — SAP S/4HANA OData v4 REST client.

Auth: Basic auth or OAuth 2.0 (client_credentials).
Credentials: read from OS keyring at authenticate() — never in plaintext.

keyring layout:
    service = config.keyring_service  (e.g. "cortex.sap.production")
    username = "sap_username"     → SAP user / client_id
    username = "sap_password"     → SAP password / client_secret
    username = "token_url"        → OAuth token endpoint (if using OAuth)

S/4HANA OData v4 base path: /sap/opu/odata4/sap/
S/4HANA OData v2 base path: /sap/opu/odata/sap/

This client targets OData v4 by default (recommended for S/4HANA 2021+).
Set extra.odata_version = "v2" for older systems.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp
import keyring

from cortex.extensions.connectors.base import ConnectorConfig

logger = logging.getLogger(__name__)


class SAPAuthError(RuntimeError):
    """Raised when SAP authentication fails."""


class SAPS4HanaClient:
    """Async SAP S/4HANA OData REST client.

    Supports:
    - Basic auth (development / on-premise with user/pass)
    - OAuth 2.0 client_credentials (recommended for production)

    Credentials are loaded from keyring at authenticate().
    The session is closed and tokens discarded at close().
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._auth_headers: dict[str, str] = {}
        self._odata_version: str = config.extra.get("odata_version", "v4")
        self._csrf_token: str | None = None  # Required for SAP write operations

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def authenticate(self) -> None:
        """Authenticate using credentials from keyring.

        Attempts OAuth 2.0 client_credentials first (if token_url is set),
        falls back to Basic auth.
        """
        svc = self.config.keyring_service
        username = keyring.get_password(svc, "sap_username") or ""
        password = keyring.get_password(svc, "sap_password") or ""
        token_url = keyring.get_password(svc, "token_url") or ""

        if not username:
            raise SAPAuthError(
                f"Missing SAP credentials in keyring service '{svc}'. "
                "Required keys: sap_username, sap_password (and optionally token_url)."
            )

        self._session = aiohttp.ClientSession()

        if token_url:
            await self._oauth_client_credentials(username, password, token_url)
        else:
            await self._basic_auth(username, password)

        logger.info(
            "[SAPS4HanaClient] authenticated → base=%s odata=%s",
            self.config.base_url, self._odata_version,
        )

    async def _oauth_client_credentials(
        self, client_id: str, client_secret: str, token_url: str
    ) -> None:
        """OAuth 2.0 client_credentials flow."""
        if not self._session:
            raise RuntimeError("Session not initialized")

        async with self._session.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise SAPAuthError(f"SAP OAuth failed [{resp.status}]: {body}")
            data = await resp.json()

        access_token = data.get("access_token")
        if not access_token:
            raise SAPAuthError("SAP OAuth response missing access_token")

        self._auth_headers = {"Authorization": f"Bearer {access_token}"}

    async def _basic_auth(self, username: str, password: str) -> None:
        """HTTP Basic auth — on-premise or development systems only."""
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._auth_headers = {"Authorization": f"Basic {encoded}"}

    # ── OData query ───────────────────────────────────────────────────────────

    async def get_entity_set(
        self,
        service: str,
        entity_set: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read an OData entity set (collection), auto-paging with @odata.nextLink.

        Args:
            service:    OData service name (e.g. "API_BUSINESS_PARTNER")
            entity_set: Entity set name (e.g. "A_BusinessPartner")
            params:     OData query options ($filter, $select, $top, etc.)

        Returns list of entity dicts.
        """
        if not self._session:
            raise RuntimeError("Not authenticated — call authenticate() first")

        if self._odata_version == "v4":
            base_path = f"/sap/opu/odata4/sap/{service}/srvd/sap/{service}/0001"
        else:
            base_path = f"/sap/opu/odata/sap/{service}"

        url = f"{self.config.base_url.rstrip('/')}{base_path}/{entity_set}"
        headers = {
            **self._auth_headers,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        all_entities: list[dict[str, Any]] = []
        query_params = dict(params or {})
        if "$format" not in query_params:
            query_params["$format"] = "json"

        while True:
            async with self._session.get(
                url,
                headers=headers,
                params=query_params,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 401:
                    raise SAPAuthError("SAP token expired — re-authenticate")
                resp.raise_for_status()
                data = await resp.json()

            # OData v4: value[] + @odata.nextLink
            # OData v2: d.results[]
            if self._odata_version == "v4":
                entities = data.get("value", [])
                next_link = data.get("@odata.nextLink")
            else:
                d = data.get("d", {})
                entities = d.get("results", [])
                next_link = d.get("__next")

            all_entities.extend(entities)

            if not next_link:
                break
            # Paginate: nextLink is a full URL
            url = next_link
            query_params = {}

        logger.debug(
            "[SAPS4HanaClient] %s/%s → %d entities", service, entity_set, len(all_entities)
        )
        return all_entities

    # ── CSRF token (required for SAP write operations) ────────────────────────

    async def fetch_csrf_token(self, path: str) -> str:
        """Fetch SAP X-CSRF-Token via HEAD request (required before POST/PATCH/DELETE)."""
        if not self._session:
            raise RuntimeError("Not authenticated")

        async with self._session.head(
            f"{self.config.base_url.rstrip('/')}{path}",
            headers={**self._auth_headers, "X-CSRF-Token": "Fetch"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            token = resp.headers.get("X-CSRF-Token", "")
            if not token:
                logger.warning("[SAPS4HanaClient] CSRF token not returned by SAP system")
            self._csrf_token = token
            return token

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Discard auth headers and close HTTP session."""
        self._auth_headers = {}
        self._csrf_token = None
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        logger.debug("[SAPS4HanaClient] session closed")
