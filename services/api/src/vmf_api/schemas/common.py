from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    database: Literal["ok", "unavailable"]
    timestamp: datetime


class AuditInfo(BaseModel):
    decision_id: int
    actor: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
