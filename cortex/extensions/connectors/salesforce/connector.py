"""salesforce/connector.py — SalesforceConnector (BaseConnector)

Pulls CRM objects from Salesforce and ingests them as CORTEX facts.

Default ingested objects:
  - Account      → world-model facts (companies)
  - Opportunity  → knowledge facts (deals pipeline)
  - Case         → issue facts (support tickets)
  - Lead         → knowledge facts (inbound leads)

Each object maps to a fact_type and tag set. The SOQL queries and object
selection are configurable via ConnectorConfig.extra:

    extra = {
        "objects": ["Account", "Opportunity"],
        "account_soql": "SELECT Id, Name, Industry, AnnualRevenue FROM Account",
        "opportunity_soql": "SELECT Id, Name, StageName, Amount, CloseDate FROM Opportunity",
    }
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.connectors.base import BaseConnector, ConnectorConfig
from cortex.extensions.connectors.registry import register_connector
from cortex.extensions.connectors.salesforce.client import SalesforceClient
from cortex.extensions.interfaces.engine import EngineProtocol

logger = logging.getLogger(__name__)

# Default SOQL per object
_DEFAULT_SOQL: dict[str, str] = {
    "Account": (
        "SELECT Id, Name, Industry, Type, AnnualRevenue, NumberOfEmployees, "
        "BillingCountry, Website, Description, LastModifiedDate "
        "FROM Account ORDER BY LastModifiedDate DESC NULLS LAST LIMIT 200"
    ),
    "Opportunity": (
        "SELECT Id, Name, StageName, Amount, CloseDate, Probability, "
        "AccountId, Description, LastModifiedDate "
        "FROM Opportunity ORDER BY LastModifiedDate DESC NULLS LAST LIMIT 200"
    ),
    "Case": (
        "SELECT Id, CaseNumber, Subject, Status, Priority, Description, "
        "AccountId, LastModifiedDate "
        "FROM Case ORDER BY LastModifiedDate DESC NULLS LAST LIMIT 200"
    ),
    "Lead": (
        "SELECT Id, FirstName, LastName, Company, Title, Email, "
        "Status, LeadSource, Description, LastModifiedDate "
        "FROM Lead ORDER BY LastModifiedDate DESC NULLS LAST LIMIT 200"
    ),
}

# fact_type mapping per Salesforce object
_FACT_TYPE_MAP: dict[str, str] = {
    "Account": "world-model",
    "Opportunity": "knowledge",
    "Case": "issue",
    "Lead": "knowledge",
}


class SalesforceConnector(BaseConnector):
    """CORTEX connector for Salesforce CRM.

    Reads CRM objects via SOQL, transforms them into CORTEX facts,
    and stores them through EngineProtocol (guards + ledger always active).
    """

    def __init__(self, config: ConnectorConfig, engine: EngineProtocol) -> None:
        super().__init__(config, engine)
        self._client = SalesforceClient(config)
        self._active_objects: list[str] = config.extra.get(
            "objects", list(_DEFAULT_SOQL.keys())
        )
        self._raw_records: list[dict[str, Any]] = []

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._client.authenticate()

    async def disconnect(self) -> None:
        await self._client.close()

    # ── Pull ─────────────────────────────────────────────────────────────────

    async def pull(self) -> list[dict[str, Any]]:
        """Fetch all configured Salesforce objects via SOQL.

        Returns flat list of records — each with a '_object_type' meta key.
        """
        all_records: list[dict[str, Any]] = []

        for obj in self._active_objects:
            soql_key = f"{obj.lower()}_soql"
            soql = self.config.extra.get(soql_key, _DEFAULT_SOQL.get(obj, ""))
            if not soql:
                logger.warning("[SalesforceConnector] No SOQL for object '%s' — skipping", obj)
                continue

            try:
                records = await self._client.query(soql)
                for r in records:
                    r["_object_type"] = obj
                all_records.extend(records)
                logger.info(
                    "[SalesforceConnector] pulled %d %s records", len(records), obj
                )
            except Exception as exc:
                logger.error(
                    "[SalesforceConnector] SOQL failed for %s: %s", obj, exc
                )
                # Isolated failure — continue with other objects
                continue

        return all_records

    # ── Transform ────────────────────────────────────────────────────────────

    async def transform(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Map a Salesforce record to a CORTEX fact payload."""
        obj_type = record.get("_object_type", "Unknown")
        rec_id = record.get("Id", "unknown")

        # Build human-readable content string
        content = self._build_content(obj_type, record)
        if not content:
            return None

        tags = [
            f"salesforce:{obj_type.lower()}",
            f"sf_id:{rec_id}",
            "crm:salesforce",
            "connector:auto",
        ]

        # Add domain-specific tags
        if obj_type == "Opportunity":
            stage = record.get("StageName", "")
            if stage:
                tags.append(f"stage:{stage.lower().replace(' ', '_')}")

        if obj_type == "Case":
            priority = record.get("Priority", "")
            if priority:
                tags.append(f"priority:{priority.lower()}")

        return {
            "content": content,
            "fact_type": _FACT_TYPE_MAP.get(obj_type, "knowledge"),
            "tags": tags,
            "confidence": "C3",  # External CRM data: verified at source but not by CORTEX
            "source": f"salesforce://{obj_type}/{rec_id}",
            "meta": {
                "sf_id": rec_id,
                "sf_object": obj_type,
                "last_modified": record.get("LastModifiedDate"),
                "connector": self.config.connector_id,
            },
        }

    # ── Content builders (per object) ────────────────────────────────────────

    def _build_content(self, obj_type: str, r: dict[str, Any]) -> str:
        if obj_type == "Account":
            return (
                f"Salesforce Account: {r.get('Name', 'N/A')} | "
                f"Industry: {r.get('Industry', 'N/A')} | "
                f"Type: {r.get('Type', 'N/A')} | "
                f"Employees: {r.get('NumberOfEmployees', 'N/A')} | "
                f"Revenue: {r.get('AnnualRevenue', 'N/A')} | "
                f"Country: {r.get('BillingCountry', 'N/A')} | "
                f"Web: {r.get('Website', 'N/A')} | "
                f"Desc: {(r.get('Description') or '')[:300]}"
            )
        if obj_type == "Opportunity":
            return (
                f"Salesforce Opportunity: {r.get('Name', 'N/A')} | "
                f"Stage: {r.get('StageName', 'N/A')} | "
                f"Amount: {r.get('Amount', 'N/A')} | "
                f"Close: {r.get('CloseDate', 'N/A')} | "
                f"Probability: {r.get('Probability', 'N/A')}% | "
                f"Desc: {(r.get('Description') or '')[:300]}"
            )
        if obj_type == "Case":
            return (
                f"Salesforce Case #{r.get('CaseNumber', 'N/A')}: {r.get('Subject', 'N/A')} | "
                f"Status: {r.get('Status', 'N/A')} | "
                f"Priority: {r.get('Priority', 'N/A')} | "
                f"Desc: {(r.get('Description') or '')[:300]}"
            )
        if obj_type == "Lead":
            name = f"{r.get('FirstName', '')} {r.get('LastName', '')}".strip()
            return (
                f"Salesforce Lead: {name} @ {r.get('Company', 'N/A')} | "
                f"Title: {r.get('Title', 'N/A')} | "
                f"Status: {r.get('Status', 'N/A')} | "
                f"Source: {r.get('LeadSource', 'N/A')} | "
                f"Desc: {(r.get('Description') or '')[:300]}"
            )
        # Generic fallback for custom objects
        return f"Salesforce {obj_type} [{r.get('Id', 'N/A')}]: {str(r)[:500]}"


# Auto-register on import
register_connector("salesforce", SalesforceConnector)
