"""sap/connector.py — SAPS4HanaConnector (BaseConnector)

Pulls ERP data from SAP S/4HANA via OData and ingests as CORTEX facts.

Default ingested entity sets (from standard SAP APIs):
  - API_BUSINESS_PARTNER / A_BusinessPartner  → world-model (master data)
  - API_PURCHASEORDER_PROCESS_SRV / A_PurchaseOrder → knowledge (procurement)
  - API_MAINTNOTIFICATION / MaintenanceNotification  → issue (maintenance WOs)
  - API_PRODUCT_SRV / A_Product                     → knowledge (product catalog)

Configure via ConnectorConfig.extra:
    extra = {
        "entity_sets": [
            {
                "service": "API_BUSINESS_PARTNER",
                "entity_set": "A_BusinessPartner",
                "params": {"$top": "100", "$select": "BusinessPartner,BusinessPartnerName"},
                "label": "business_partner"
            }
        ]
    }
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.connectors.base import BaseConnector, ConnectorConfig
from cortex.extensions.connectors.registry import register_connector
from cortex.extensions.connectors.sap.client import SAPS4HanaClient
from cortex.extensions.interfaces.engine import EngineProtocol

logger = logging.getLogger(__name__)

# Default entity set configurations
_DEFAULT_ENTITY_SETS: list[dict[str, Any]] = [
    {
        "service": "API_BUSINESS_PARTNER",
        "entity_set": "A_BusinessPartner",
        "params": {
            "$top": "100",
            "$select": (
                "BusinessPartner,BusinessPartnerName,BusinessPartnerType,"
                "Industry,SearchTerm1,Country,CityName,IsNaturalPerson"
            ),
        },
        "label": "business_partner",
        "fact_type": "world-model",
    },
    {
        "service": "API_PURCHASEORDER_PROCESS_SRV",
        "entity_set": "A_PurchaseOrder",
        "params": {
            "$top": "100",
            "$select": (
                "PurchaseOrder,PurchaseOrderType,CompanyCode,Supplier,"
                "PurchasingOrganization,DocumentCurrency,NetPaymentDays,"
                "CreationDate,PurchaseOrderDate"
            ),
        },
        "label": "purchase_order",
        "fact_type": "knowledge",
    },
    {
        "service": "API_MAINTNOTIFICATION",
        "entity_set": "MaintenanceNotification",
        "params": {
            "$top": "100",
            "$select": (
                "MaintenanceNotification,NotificationType,ShortText,"
                "MaintNotifLongTextForEdit,FunctionalLocation,Equipment,"
                "MaintNotifNotifDate,NotificationUserStatus"
            ),
        },
        "label": "maintenance_notification",
        "fact_type": "issue",
    },
    {
        "service": "API_PRODUCT_SRV",
        "entity_set": "A_Product",
        "params": {
            "$top": "100",
            "$select": (
                "Product,ProductType,BaseUnit,ProductGroup,GrossWeight,"
                "WeightUnit,Division,CreationDate,IsMarkedForDeletion"
            ),
        },
        "label": "product",
        "fact_type": "knowledge",
    },
]


class SAPS4HanaConnector(BaseConnector):
    """CORTEX connector for SAP S/4HANA via OData REST API.

    Reads ERP entity sets, transforms them into CORTEX facts,
    and stores through EngineProtocol (guards + ledger always active).
    """

    def __init__(self, config: ConnectorConfig, engine: EngineProtocol) -> None:
        super().__init__(config, engine)
        self._client = SAPS4HanaClient(config)
        self._entity_sets: list[dict[str, Any]] = config.extra.get(
            "entity_sets", _DEFAULT_ENTITY_SETS
        )
        self._raw_records: list[dict[str, Any]] = []

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._client.authenticate()

    async def disconnect(self) -> None:
        await self._client.close()

    # ── Pull ─────────────────────────────────────────────────────────────────

    async def pull(self) -> list[dict[str, Any]]:
        """Fetch all configured SAP OData entity sets.

        Returns flat list with '_label' and '_fact_type' meta keys injected.
        """
        all_records: list[dict[str, Any]] = []

        for es_config in self._entity_sets:
            service = es_config.get("service", "")
            entity_set = es_config.get("entity_set", "")
            params = es_config.get("params", {})
            label = es_config.get("label", entity_set.lower())
            fact_type = es_config.get("fact_type", "knowledge")

            if not service or not entity_set:
                logger.warning("[SAPS4HanaConnector] skipping incomplete entity_set config: %s", es_config)
                continue

            try:
                records = await self._client.get_entity_set(service, entity_set, params)
                for r in records:
                    r["_label"] = label
                    r["_fact_type"] = fact_type
                    r["_service"] = service
                    r["_entity_set"] = entity_set
                all_records.extend(records)
                logger.info(
                    "[SAPS4HanaConnector] pulled %d %s records from %s",
                    len(records), entity_set, service,
                )
            except Exception as exc:
                # Isolated entity set failure — log and continue
                logger.error(
                    "[SAPS4HanaConnector] failed to pull %s/%s: %s",
                    service, entity_set, exc,
                )
                continue

        return all_records

    # ── Transform ────────────────────────────────────────────────────────────

    async def transform(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Map a SAP OData entity to a CORTEX fact payload."""
        label = record.get("_label", "sap_entity")
        fact_type = record.get("_fact_type", "knowledge")
        service = record.get("_service", "")
        entity_set = record.get("_entity_set", "")

        # Strip meta keys before building content
        clean = {k: v for k, v in record.items() if not k.startswith("_")}
        if not clean:
            return None

        content = self._build_content(label, clean)
        if not content:
            return None

        # Primary key extraction (SAP uses PascalCase IDs)
        pk = (
            clean.get("BusinessPartner")
            or clean.get("PurchaseOrder")
            or clean.get("MaintenanceNotification")
            or clean.get("Product")
            or "unknown"
        )

        tags = [
            f"sap:{label}",
            f"sap_service:{service.lower()[:30]}",
            "erp:sap_s4hana",
            "connector:auto",
        ]

        # Domain-specific tags
        if label == "maintenance_notification":
            status = clean.get("NotificationUserStatus", "")
            if status:
                tags.append(f"status:{status.lower()[:20]}")

        return {
            "content": content,
            "fact_type": fact_type,
            "tags": tags,
            "confidence": "C3",
            "source": f"sap://{service}/{entity_set}/{pk}",
            "meta": {
                "sap_pk": pk,
                "sap_service": service,
                "sap_entity_set": entity_set,
                "label": label,
                "connector": self.config.connector_id,
            },
        }

    # ── Content builders ─────────────────────────────────────────────────────

    def _build_content(self, label: str, r: dict[str, Any]) -> str:
        if label == "business_partner":
            return (
                f"SAP Business Partner: {r.get('BusinessPartnerName', 'N/A')} "
                f"[{r.get('BusinessPartner', 'N/A')}] | "
                f"Type: {r.get('BusinessPartnerType', 'N/A')} | "
                f"Industry: {r.get('Industry', 'N/A')} | "
                f"Country: {r.get('Country', 'N/A')} | "
                f"City: {r.get('CityName', 'N/A')}"
            )
        if label == "purchase_order":
            return (
                f"SAP Purchase Order: {r.get('PurchaseOrder', 'N/A')} | "
                f"Type: {r.get('PurchaseOrderType', 'N/A')} | "
                f"Supplier: {r.get('Supplier', 'N/A')} | "
                f"Company: {r.get('CompanyCode', 'N/A')} | "
                f"Currency: {r.get('DocumentCurrency', 'N/A')} | "
                f"Date: {r.get('PurchaseOrderDate', 'N/A')}"
            )
        if label == "maintenance_notification":
            return (
                f"SAP Maintenance Notification: {r.get('MaintenanceNotification', 'N/A')} | "
                f"Type: {r.get('NotificationType', 'N/A')} | "
                f"Short Text: {r.get('ShortText', 'N/A')} | "
                f"Location: {r.get('FunctionalLocation', 'N/A')} | "
                f"Equipment: {r.get('Equipment', 'N/A')} | "
                f"Status: {r.get('NotificationUserStatus', 'N/A')} | "
                f"Detail: {(r.get('MaintNotifLongTextForEdit') or '')[:300]}"
            )
        if label == "product":
            return (
                f"SAP Product: {r.get('Product', 'N/A')} | "
                f"Type: {r.get('ProductType', 'N/A')} | "
                f"Group: {r.get('ProductGroup', 'N/A')} | "
                f"Base Unit: {r.get('BaseUnit', 'N/A')} | "
                f"Division: {r.get('Division', 'N/A')} | "
                f"Deleted: {r.get('IsMarkedForDeletion', False)}"
            )
        # Generic fallback for custom entity sets
        pairs = " | ".join(f"{k}: {v}" for k, v in list(r.items())[:10])
        return f"SAP {label}: {pairs}"


# Auto-register on import
register_connector("sap_s4hana", SAPS4HanaConnector)
