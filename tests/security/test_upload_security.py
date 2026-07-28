from __future__ import annotations

from fastapi.testclient import TestClient
from renewableops_api.main import RATE_LIMIT_REQUESTS, RATE_WINDOWS, app

client = TestClient(app)


def test_api_applies_a_bounded_local_rate_limit() -> None:
    RATE_WINDOWS.clear()
    try:
        for _ in range(RATE_LIMIT_REQUESTS):
            assert client.get("/api/v1/overview").status_code == 200
        response = client.get("/api/v1/overview")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
    finally:
        RATE_WINDOWS.clear()


def test_rejects_untrusted_upload_type() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("payload.svg", b"<svg onload=alert(1)>", "image/svg+xml")},
    )
    assert response.status_code == 415


def test_rejects_corrupted_image() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("fake.png", b"not-a-png", "image/png")},
    )
    assert response.status_code == 422
