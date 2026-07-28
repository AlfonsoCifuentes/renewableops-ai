from __future__ import annotations

from fastapi.testclient import TestClient
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
