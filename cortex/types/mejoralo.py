# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "MejoraloScanRequest",
    "DimensionResultModel",
    "MejoraloScanResponse",
    "MejoraloSessionRequest",
    "MejoraloSessionResponse",
    "MejoraloShipRequest",
    "ShipSealModel",
    "MejoraloShipResponse",
]


class MejoraloScanRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str
    deep: bool = False


class DimensionResultModel(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)
    weight: str
    findings: list[str] = Field(default_factory=list)


class MejoraloScanResponse(BaseModel):
    project: str
    score: int
    stack: str
    dimensions: list[DimensionResultModel]
    dead_code: bool
    total_files: int = 0
    total_loc: int = 0
    fact_id: int | None = None


class MejoraloSessionRequest(BaseModel):
    project: str = Field(..., max_length=100)
    score_before: int = Field(..., ge=0, le=100)
    score_after: int = Field(..., ge=0, le=100)
    actions: list[str] = Field(default_factory=list)


class MejoraloSessionResponse(BaseModel):
    fact_id: int
    project: str
    delta: int
    status: str = "recorded"


class MejoraloShipRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str


class ShipSealModel(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class MejoraloShipResponse(BaseModel):
    project: str
    ready: bool
    seals: list[ShipSealModel]
    passed: int
    total: int = 7
