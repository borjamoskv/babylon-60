"""Typed configuration contract for DORA evidence-pack inputs."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class DeploymentMode(str, Enum):
    """Supported deployment modes for a CORTEX DORA evidence pack."""

    SELF_MANAGED = "self-managed"
    MANAGED_PRIVATE = "managed-private"
    HOSTED = "hosted"


class EvidenceStatus(str, Enum):
    """Allowed evidence maturity states for controls and claims."""

    IMPLEMENTED = "implemented"
    CONFIG_DEPENDENT = "config-dependent"
    CUSTOMER_RESPONSIBILITY = "customer-responsibility"
    CONTRACT_DEPENDENT = "contract-dependent"
    ROADMAP = "roadmap"
    NOT_APPLICABLE = "not-applicable"


class Materiality(str, Enum):
    """Materiality levels for ICT subprocessors and dependencies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationSeverity(str, Enum):
    """Severity for DORA configuration validation issues."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class ValidationIssue(BaseModel):
    """Actionable validation issue returned by the DORA validator."""

    severity: ValidationSeverity
    code: str
    message: str
    path: str
    affected_document: str | None = None


class PackConfig(BaseModel):
    """Top-level pack metadata."""

    deployment_id: str
    deployment_mode: DeploymentMode
    customer_name: str | None = None
    validity_days: int = Field(default=90, ge=1, le=365)


class ServiceConfig(BaseModel):
    """Service metadata used in generated evidence."""

    legal_provider_name: str
    product_version: str
    service_description: str | None = None
    modules_enabled: list[str] = Field(default_factory=list)
    independent_assurance_available: bool = False


class LocationEntry(BaseModel):
    """A country/owner tuple for location declarations."""

    category: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=2)
    owner: str
    description: str | None = None

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        """Normalize ISO 3166-1 alpha-2 country values."""

        return value.upper()


class SupportAccess(BaseModel):
    """Remote support access configuration."""

    enabled: bool = False
    countries: list[str] = Field(default_factory=list)
    authorization_required: bool = True
    logging_enabled: bool = True
    revocation_supported: bool = True

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, values: list[str]) -> list[str]:
        """Normalize support countries to uppercase values."""

        return [value.upper() for value in values]


class ExternalModelProvider(BaseModel):
    """External AI/model provider details when enabled."""

    name: str
    service: str
    data_sent: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    retention: str | None = None
    opt_out_available: bool = False

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, values: list[str]) -> list[str]:
        """Normalize model provider countries to uppercase values."""

        return [value.upper() for value in values]


class DataConfig(BaseModel):
    """Data handling and external processing configuration."""

    telemetry_enabled: bool = False
    external_models_enabled: bool = False
    personal_data_possible: bool = False
    confidential_data_possible: bool = False
    key_custody: str = "customer"
    encryption_at_rest: str | None = None
    encryption_in_transit: str | None = None
    external_model_providers: list[ExternalModelProvider] = Field(default_factory=list)


class Subprocessor(BaseModel):
    """ICT subprocessor declaration."""

    name: str
    service: str
    data_categories: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    materiality: Materiality = Materiality.LOW
    customer_opt_out: str = "unknown"
    applies_to: list[DeploymentMode] = Field(default_factory=list)

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, values: list[str]) -> list[str]:
        """Normalize subprocessor countries to uppercase values."""

        return [value.upper() for value in values]


class ContinuityConfig(BaseModel):
    """Continuity, restore, and exit planning configuration."""

    rto: str
    rpo: str
    backup_responsibility: str
    restore_responsibility: str
    restore_test_available: bool = False
    exit_plan_available: bool = True
    key_loss_procedure_available: bool = False


class Claim(BaseModel):
    """Evidence claim rendered into the DORA evidence pack."""

    id: str
    text: str
    status: EvidenceStatus
    owner: str
    evidence_source: list[str] = Field(default_factory=list)
    verification_method: str | None = None
    limitation: str | None = None


class DoraConfig(BaseModel):
    """Validated source of truth for DORA evidence generation."""

    pack: PackConfig
    service: ServiceConfig
    data: DataConfig
    continuity: ContinuityConfig
    support_access: SupportAccess = Field(default_factory=SupportAccess)
    locations: list[LocationEntry] = Field(default_factory=list)
    subprocessors: list[Subprocessor] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


def read_yaml_mapping(path: Path) -> dict[str, object]:
    """Read a YAML mapping from disk and reject non-mapping roots."""

    import yaml

    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}
    if not isinstance(parsed, dict):
        raise TypeError(f"DORA config must be a YAML mapping: {path}")
    return parsed
