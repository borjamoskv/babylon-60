"""cortex.extensions.connectors — Enterprise legacy system connectors.

Provides CORTEX-native integrations for CRM/ERP systems (Salesforce, SAP)
and a generic REST connector for arbitrary external APIs.

All connectors route through EngineProtocol.store() — they never bypass
guards, ledger, or audit trail.
"""

from cortex.extensions.connectors.registry import ConnectorRegistry

__all__ = ["ConnectorRegistry"]
