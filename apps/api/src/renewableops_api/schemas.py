"""Versioned public API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScenarioRequest(BaseModel):
    scenario: Literal[
        "soiling",
        "inverter_loss",
        "wind_vibration",
        "source_outage",
        "model_drift",
    ]
    asset_id: str = Field(min_length=3, max_length=64)
    severity: int = Field(default=60, ge=1, le=100)
    duration_hours: int = Field(default=12, ge=1, le=168)
    seed: int = Field(default=20260728, ge=1, le=2_147_483_647)

    @field_validator("asset_id")
    @classmethod
    def safe_asset_id(cls, value: str) -> str:
        if not all(character.isalnum() or character in "-_" for character in value):
            raise ValueError("asset_id contains unsupported characters")
        return value


class ScenarioResponse(BaseModel):
    run_id: str
    status: Literal["completed"]
    detected_by: str
    detection_seconds: int
    estimated_mwh_at_risk: float
    action: str
    audit_event_id: str
    reverted: bool = True


class ForecastRequest(BaseModel):
    technology: Literal["solar", "wind"]
    installed_capacity_mw: float = Field(gt=0, le=500)
    hour_sin: float = Field(ge=-1, le=1)
    hour_cos: float = Field(ge=-1, le=1)
    day_sin: float = Field(ge=-1, le=1)
    day_cos: float = Field(ge=-1, le=1)
    irradiance_wm2: float = Field(ge=0, le=1400)
    temperature_c: float = Field(ge=-50, le=65)
    cloud_cover_fraction: float = Field(ge=0, le=1)
    wind_speed_ms: float = Field(ge=0, le=70)
    availability: float = Field(ge=0, le=1)
    lag_1h_mw: float | None = Field(default=None, ge=0)
    lag_24h_mw: float = Field(ge=0)
    lag_168h_mw: float | None = Field(default=None, ge=0)
    rolling_24h_mw: float = Field(ge=0)


class ForecastResponse(BaseModel):
    technology: str
    model: str
    p10_mw: float
    p50_mw: float
    p90_mw: float
    model_version: str = "1.0.0"
    decision_support_only: bool = True


class BatteryDispatchRequest(BaseModel):
    prices_eur_mwh: list[float] = Field(min_length=1, max_length=168)
    capacity_mwh: float = Field(gt=0, le=1000)
    max_power_mw: float = Field(gt=0, le=500)
    initial_soc_fraction: float = Field(default=0.5, gt=0, le=1)
    reserve_fraction: float = Field(default=0.1, ge=0, lt=1)
    roundtrip_efficiency: float = Field(default=0.90, gt=0, le=1)


class BatteryDispatchResponse(BaseModel):
    schedule: list[dict[str, float | int]]
    estimated_margin_eur: float
    method: str = "transparent_quantile_heuristic"
    decision_support_only: bool = True


class InspectionReviewRequest(BaseModel):
    action: Literal["approve", "reject", "correct"]
    reviewer: str = Field(pattern=r"^[a-z0-9_-]{3,64}$")
    corrected_label: Literal["defective", "functional"] | None = None
    reason: str = Field(default="", max_length=500)
