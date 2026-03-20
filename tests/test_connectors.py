"""tests/test_connectors.py — Unit tests for CORTEX enterprise connectors.

Tests use mocked HTTP sessions and a mock EngineProtocol — no real
external system connections are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cortex.extensions.connectors.base import ConnectorConfig, IngestResult
from cortex.extensions.connectors.generic_rest.connector import GenericRESTConnector
from cortex.extensions.connectors.registry import (
    ConnectorRegistry,
    build_connector,
)
from cortex.extensions.connectors.salesforce.connector import SalesforceConnector
from cortex.extensions.connectors.sap.connector import SAPS4HanaConnector

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    engine.store = AsyncMock(return_value=999)
    return engine


def _salesforce_config(**extra_kwargs) -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="sf-test",
        system="salesforce",
        base_url="https://myorg.salesforce.com",
        keyring_service="cortex.salesforce.test",
        project="crm",
        tenant_id="default",
        max_records_per_cycle=100,
        extra=extra_kwargs or {},
    )


def _sap_config(**extra_kwargs) -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="sap-test",
        system="sap_s4hana",
        base_url="https://my-sap-system.example.com",
        keyring_service="cortex.sap.test",
        project="erp",
        tenant_id="default",
        max_records_per_cycle=100,
        extra=extra_kwargs or {},
    )


def _generic_config(**extra_kwargs) -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="rest-test",
        system="generic_rest",
        base_url="https://api.example.com",
        keyring_service="cortex.rest.test",
        project="external",
        tenant_id="default",
        max_records_per_cycle=50,
        extra=extra_kwargs,
    )


# ── ConnectorConfig ───────────────────────────────────────────────────────────

class TestConnectorConfig:
    def test_defaults(self):
        cfg = _salesforce_config()
        assert cfg.tenant_id == "default"
        assert cfg.poll_interval_seconds == 300
        assert cfg.max_records_per_cycle == 100

    def test_extra_passthrough(self):
        cfg = _salesforce_config(sandbox=True)
        assert cfg.extra["sandbox"] is True


# ── IngestResult ──────────────────────────────────────────────────────────────

class TestIngestResult:
    def test_success_when_no_errors(self):
        r = IngestResult("c1", "sf", 10, 8, 2)
        assert r.success is True

    def test_fails_when_errors_present(self):
        r = IngestResult("c1", "sf", 10, 5, 5, errors=["boom"])
        assert r.success is False

    def test_str_representation(self):
        r = IngestResult("c1", "sf", 10, 10, 0)
        assert "stored=10" in str(r)


# ── Registry ─────────────────────────────────────────────────────────────────

class TestConnectorRegistry:
    def test_registered_systems(self):
        # SalesforceConnector, SAPS4HanaConnector, GenericRESTConnector
        # auto-register on import — verify they are present
        from cortex.extensions.connectors.registry import list_connectors
        avail = list_connectors()
        assert "salesforce" in avail
        assert "sap_s4hana" in avail
        assert "generic_rest" in avail

    def test_build_unknown_raises(self, mock_engine):
        cfg = ConnectorConfig(
            connector_id="x", system="nonexistent_crm",
            base_url="http://x.com",
        )
        with pytest.raises(KeyError, match="nonexistent_crm"):
            build_connector(cfg, mock_engine)

    def test_registry_get_or_create(self, mock_engine):
        registry = ConnectorRegistry(mock_engine)
        cfg = _salesforce_config()
        c1 = registry.get_or_create(cfg)
        c2 = registry.get_or_create(cfg)
        assert c1 is c2  # same instance returned

    def test_registry_list_active(self, mock_engine):
        registry = ConnectorRegistry(mock_engine)
        cfg = _salesforce_config()
        registry.get_or_create(cfg)
        assert "sf-test" in registry.list_active()


# ── BaseConnector.ingest() circuit breaker ────────────────────────────────────

class TestBaseConnectorIngest:
    @pytest.mark.asyncio
    async def test_circuit_breaker_caps_records(self, mock_engine):
        """Records beyond max_records_per_cycle must be discarded."""
        cfg = _salesforce_config()
        cfg = ConnectorConfig(
            connector_id="sf-cap",
            system="salesforce",
            base_url="https://myorg.salesforce.com",
            keyring_service="cortex.salesforce.test",
            project="crm",
            max_records_per_cycle=3,  # small cap
        )
        connector = SalesforceConnector(cfg, mock_engine)

        # Patch pull() to return more records than cap
        big_pull = [
            {"Id": str(i), "Name": f"Acct{i}", "_object_type": "Account"}
            for i in range(10)
        ]
        connector.pull = AsyncMock(return_value=big_pull)

        result = await connector.ingest()
        assert result.records_fetched == 10
        # Only 3 were processed (cap applied)
        assert result.records_stored <= 3

    @pytest.mark.asyncio
    async def test_pull_failure_returns_error_result(self, mock_engine):
        """pull() exception → IngestResult with error, no crash."""
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        connector.pull = AsyncMock(side_effect=RuntimeError("network down"))

        result = await connector.ingest()
        assert result.records_fetched == 0
        assert result.records_stored == 0
        assert len(result.errors) == 1
        assert "pull() failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_transform_none_skips_record(self, mock_engine):
        """transform() returning None → record skipped."""
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        connector.pull = AsyncMock(return_value=[{"Id": "x", "_object_type": "Account"}])
        connector.transform = AsyncMock(return_value=None)

        result = await connector.ingest()
        assert result.records_skipped == 1
        assert result.records_stored == 0
        mock_engine.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_engine_store_failure_isolated(self, mock_engine):
        """engine.store() failure → record skipped, other records continue."""
        cfg = _salesforce_config()
        connector = SalesforceConnector(cfg, mock_engine)

        records = [
            {"Id": "001", "Name": "Good", "_object_type": "Account"},
            {"Id": "002", "Name": "Bad", "_object_type": "Account"},
        ]
        connector.pull = AsyncMock(return_value=records)
        mock_engine.store = AsyncMock(side_effect=[None, RuntimeError("db full")])

        result = await connector.ingest()
        assert result.records_stored == 1
        assert result.records_skipped == 1


# ── SalesforceConnector.transform() ──────────────────────────────────────────

class TestSalesforceTransform:
    @pytest.mark.asyncio
    async def test_account_transform(self, mock_engine):
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        record = {
            "_object_type": "Account",
            "Id": "001ABC",
            "Name": "Acme Corp",
            "Industry": "Technology",
            "Type": "Customer",
            "AnnualRevenue": 5000000,
            "NumberOfEmployees": 250,
            "BillingCountry": "US",
            "Website": "acme.com",
            "Description": "Leading tech firm",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert payload["fact_type"] == "world-model"
        assert "salesforce:account" in payload["tags"]
        assert "sf_id:001ABC" in payload["tags"]
        assert "Acme Corp" in payload["content"]
        assert payload["confidence"] == "C3"

    @pytest.mark.asyncio
    async def test_opportunity_transform(self, mock_engine):
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        record = {
            "_object_type": "Opportunity",
            "Id": "006XYZ",
            "Name": "Big Deal Q2",
            "StageName": "Proposal/Price Quote",
            "Amount": 120000,
            "CloseDate": "2026-06-30",
            "Probability": 65,
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert payload["fact_type"] == "knowledge"
        assert "stage:proposal/price_quote" in payload["tags"]
        assert "120000" in payload["content"]

    @pytest.mark.asyncio
    async def test_case_transform(self, mock_engine):
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        record = {
            "_object_type": "Case",
            "Id": "500ZZZ",
            "CaseNumber": "00001234",
            "Subject": "Login page broken",
            "Status": "New",
            "Priority": "High",
            "Description": "Cannot login since yesterday",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert payload["fact_type"] == "issue"
        assert "priority:high" in payload["tags"]
        assert "00001234" in payload["content"]

    @pytest.mark.asyncio
    async def test_lead_transform(self, mock_engine):
        connector = SalesforceConnector(_salesforce_config(), mock_engine)
        record = {
            "_object_type": "Lead",
            "Id": "00QLLL",
            "FirstName": "María",
            "LastName": "García",
            "Company": "ACME",
            "Title": "CTO",
            "Status": "Working",
            "LeadSource": "Web",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert "María García" in payload["content"]


# ── SAPS4HanaConnector.transform() ───────────────────────────────────────────

class TestSAPTransform:
    @pytest.mark.asyncio
    async def test_business_partner_transform(self, mock_engine):
        connector = SAPS4HanaConnector(_sap_config(), mock_engine)
        record = {
            "_label": "business_partner",
            "_fact_type": "world-model",
            "_service": "API_BUSINESS_PARTNER",
            "_entity_set": "A_BusinessPartner",
            "BusinessPartner": "BP-00042",
            "BusinessPartnerName": "Volkswagen AG",
            "BusinessPartnerType": "1",
            "Industry": "Automotive",
            "Country": "DE",
            "CityName": "Wolfsburg",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert payload["fact_type"] == "world-model"
        assert "sap:business_partner" in payload["tags"]
        assert "Volkswagen AG" in payload["content"]
        assert payload["meta"]["sap_pk"] == "BP-00042"

    @pytest.mark.asyncio
    async def test_maintenance_notification_transform(self, mock_engine):
        connector = SAPS4HanaConnector(_sap_config(), mock_engine)
        record = {
            "_label": "maintenance_notification",
            "_fact_type": "issue",
            "_service": "API_MAINTNOTIFICATION",
            "_entity_set": "MaintenanceNotification",
            "MaintenanceNotification": "MN-000123",
            "NotificationType": "M1",
            "ShortText": "Pump failure",
            "FunctionalLocation": "PLANT-01",
            "Equipment": "EQ-007",
            "NotificationUserStatus": "OSNO",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert payload["fact_type"] == "issue"
        assert "Pump failure" in payload["content"]
        assert "status:osno" in payload["tags"]

    @pytest.mark.asyncio
    async def test_empty_record_returns_none(self, mock_engine):
        connector = SAPS4HanaConnector(_sap_config(), mock_engine)
        record = {"_label": "product", "_fact_type": "knowledge"}
        payload = await connector.transform(record)
        assert payload is None


# ── GenericRESTConnector.transform() ─────────────────────────────────────────

class TestGenericRESTTransform:
    @pytest.mark.asyncio
    async def test_transform_with_template(self, mock_engine):
        cfg = _generic_config(
            auth_type="none",
            endpoints=[{
                "path": "/users",
                "label": "users",
                "fact_type": "knowledge",
                "content_template": "${name} | ${email} | ${role}",
                "tags": ["source:myapp"],
            }]
        )
        connector = GenericRESTConnector(cfg, mock_engine)
        record = {
            "_label": "users",
            "_fact_type": "knowledge",
            "_endpoint_path": "/users",
            "id": "u42",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "role": "Engineer",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert "Ada Lovelace" in payload["content"]
        assert "ada@example.com" in payload["content"]
        assert "source:myapp" in payload["tags"]
        assert "rest:users" in payload["tags"]
        assert payload["meta"]["record_id"] == "u42"

    @pytest.mark.asyncio
    async def test_transform_fallback_no_template(self, mock_engine):
        cfg = _generic_config(auth_type="none", endpoints=[])
        connector = GenericRESTConnector(cfg, mock_engine)
        record = {
            "_label": "events",
            "_fact_type": "knowledge",
            "_endpoint_path": "/events",
            "id": 9,
            "title": "Q1 Review",
            "date": "2026-04-01",
        }
        payload = await connector.transform(record)
        assert payload is not None
        assert "Q1 Review" in payload["content"]

    @pytest.mark.asyncio
    async def test_transform_empty_record_returns_none(self, mock_engine):
        cfg = _generic_config(auth_type="none", endpoints=[])
        connector = GenericRESTConnector(cfg, mock_engine)
        record = {"_label": "empty", "_fact_type": "knowledge", "_endpoint_path": "/x"}
        payload = await connector.transform(record)
        assert payload is None
