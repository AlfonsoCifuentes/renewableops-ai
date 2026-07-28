from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from renewableops_api.main import app

client = TestClient(app)


@pytest.mark.slow
def test_liveness_p95_is_bounded_on_local_test_client() -> None:
    durations: list[float] = []
    for _ in range(25):
        started = time.perf_counter()
        response = client.get("/health/live")
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 < 0.25
