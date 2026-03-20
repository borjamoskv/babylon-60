"""salesforce/client.py — Salesforce REST API client (OAuth 2.0 + SOQL).

Auth flow: OAuth 2.0 Username-Password (Connected App).
Credentials: read from OS keyring — never from env or config files.

keyring layout:
    service = config.keyring_service  (e.g. "cortex.salesforce.production")
    username = "client_id"       → Connected App client_id
    username = "client_secret"   → Connected App client_secret
    username = "sf_username"     → Salesforce user login
    username = "sf_password"     → Salesforce user password + security_token

Usage:
    client = SalesforceClient(config)
    await client.authenticate()
    records = await client.query("SELECT Id, Name FROM Account LIMIT 100")
    await client.close()
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import keyring

from cortex.extensions.connectors.base import ConnectorConfig

logger = logging.getLogger(__name__)

_LOGIN_URL = "https://login.salesforce.com/services/oauth2/token"
_TEST_LOGIN_URL = "https://test.salesforce.com/services/oauth2/token"


class SalesforceAuthError(RuntimeError):
    """Raised when Salesforce OAuth authentication fails."""


class SalesforceClient:
    """Async Salesforce REST + SOQL client.

    All credentials are loaded from keyring at authenticate() — never stored
    in plaintext. The access_token is ephemeral and discarded on close().
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._instance_url: str | None = None
        self._api_version: str = config.extra.get("api_version", "v60.0")
        self._sandbox: bool = config.extra.get("sandbox", False)

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def authenticate(self) -> None:
        """OAuth 2.0 Username-Password flow using credentials from keyring."""
        svc = self.config.keyring_service
        client_id = keyring.get_password(svc, "client_id") or ""
        client_secret = keyring.get_password(svc, "client_secret") or ""
        sf_username = keyring.get_password(svc, "sf_username") or ""
        sf_password = keyring.get_password(svc, "sf_password") or ""  # includes security token

        if not all([client_id, client_secret, sf_username, sf_password]):
            raise SalesforceAuthError(
                f"Missing Salesforce credentials in keyring service '{svc}'. "
                "Required keys: client_id, client_secret, sf_username, sf_password."
            )

        login_url = _TEST_LOGIN_URL if self._sandbox else _LOGIN_URL

        self._session = aiohttp.ClientSession()
        try:
            async with self._session.post(
                login_url,
                data={
                    "grant_type": "password",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "username": sf_username,
                    "password": sf_password,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise SalesforceAuthError(
                        f"Salesforce auth failed [{resp.status}]: {body}"
                    )
                data = await resp.json()

        except SalesforceAuthError:
            raise
        except Exception as exc:
            raise SalesforceAuthError(f"Auth request error: {exc}") from exc

        self._access_token = data.get("access_token")
        self._instance_url = data.get("instance_url")

        if not self._access_token or not self._instance_url:
            raise SalesforceAuthError("Auth response missing access_token or instance_url")

        logger.info(
            "[SalesforceClient] authenticated → instance=%s api=%s",
            self._instance_url, self._api_version,
        )

    # ── SOQL Query ───────────────────────────────────────────────────────────

    async def query(self, soql: str) -> list[dict[str, Any]]:
        """Execute a SOQL query, auto-paginating through nextRecordsUrl."""
        if not self._session or not self._access_token or not self._instance_url:
            raise RuntimeError("Not authenticated — call authenticate() first")

        url = f"{self._instance_url}/services/data/{self._api_version}/query"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        params = {"q": soql}

        all_records: list[dict[str, Any]] = []

        while True:
            async with self._session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 401:
                    raise SalesforceAuthError("Access token expired — re-authenticate")
                resp.raise_for_status()
                data = await resp.json()

            all_records.extend(data.get("records", []))

            if data.get("done", True):
                break
            # Paginate
            next_url = data.get("nextRecordsUrl", "")
            url = f"{self._instance_url}{next_url}"
            params = {}  # nextRecordsUrl already has the query embedded

        logger.debug(
            "[SalesforceClient] query returned %d records", len(all_records)
        )
        return all_records

    # ── REST describe ─────────────────────────────────────────────────────────

    async def describe_object(self, sobject: str) -> dict[str, Any]:
        """Describe a Salesforce object (fields, relationships)."""
        if not self._session or not self._access_token or not self._instance_url:
            raise RuntimeError("Not authenticated")

        url = (
            f"{self._instance_url}/services/data/{self._api_version}"
            f"/sobjects/{sobject}/describe"
        )
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with self._session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Discard access token and close HTTP session."""
        self._access_token = None
        self._instance_url = None
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        logger.debug("[SalesforceClient] session closed")
