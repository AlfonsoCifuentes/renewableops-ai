from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image
from renewableops_api.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_scenario_validates_asset_technology() -> None:
    response = client.post(
        "/api/v1/scenarios",
        json={
            "scenario": "wind_vibration",
            "asset_id": "sol-cmn-01",
            "severity": 60,
            "duration_hours": 12,
            "seed": 42,
        },
    )
    assert response.status_code == 422


def test_scenario_is_reproducible() -> None:
    payload = {
        "scenario": "soiling",
        "asset_id": "sol-ext-02",
        "severity": 62,
        "duration_hours": 12,
        "seed": 42,
    }
    first = client.post("/api/v1/scenarios", json=payload)
    second = client.post("/api/v1/scenarios", json=payload)
    assert first.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]


def test_battery_dispatch_is_bounded() -> None:
    response = client.post(
        "/api/v1/battery/dispatch",
        json={
            "prices_eur_mwh": [18, 22, 35, 78, 91, 50],
            "capacity_mwh": 10,
            "max_power_mw": 4,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["schedule"]) == 6
    assert payload["decision_support_only"] is True


def test_forecast_uses_trained_quantile_artifacts() -> None:
    response = client.post(
        "/api/v1/forecast",
        json={
            "technology": "solar",
            "installed_capacity_mw": 50,
            "hour_sin": 0.5,
            "hour_cos": 0.866,
            "day_sin": 0.2,
            "day_cos": 0.98,
            "irradiance_wm2": 620,
            "temperature_c": 27,
            "cloud_cover_fraction": 0.2,
            "wind_speed_ms": 4,
            "availability": 0.99,
            "lag_1h_mw": 30,
            "lag_24h_mw": 29,
            "lag_168h_mw": 28,
            "rolling_24h_mw": 22,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["p10_mw"] <= payload["p50_mw"] <= payload["p90_mw"] <= 50


def test_documented_cv_route_returns_reviewable_evidence() -> None:
    image = Image.linear_gradient("L").resize((96, 96)).convert("RGB")
    body = io.BytesIO()
    image.save(body, format="PNG")
    response = client.post(
        "/api/v1/cv/solar/classify",
        files={"file": ("cell.png", body.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"]
    assert payload["model_version"] == "1.0.0"
    assert payload["predicted_class"] in {"defective", "functional"}
    assert isinstance(payload["review_required"], bool)


def test_human_review_is_audited_without_automatic_retraining() -> None:
    response = client.post(
        "/api/v1/inspections/VIS-TEST-001/review",
        json={
            "action": "approve",
            "reviewer": "test-reviewer",
            "reason": "Evidence checked in API contract test.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_status"] == "approve"
    assert payload["automatic_retraining"] is False
    assert payload["audit_event_id"]
