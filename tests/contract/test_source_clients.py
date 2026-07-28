from __future__ import annotations

import httpx
import pytest
from renewableops.sources import SourceError, fetch_aemet, fetch_pvgis, fetch_redata


def _client(payload: dict[str, object]) -> httpx.Client:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload, request=request)
    )
    return httpx.Client(transport=transport)


def test_redata_records_provenance_without_query_secrets() -> None:
    with _client({"data": [{"type": "Generación"}]}) as client:
        result = fetch_redata(client=client)
    assert result.source_id == "ree_redata"
    assert "?" not in result.requested_url
    assert len(result.checksum_sha256) == 64


def test_pvgis_records_provenance() -> None:
    with _client({"outputs": {"monthly": []}}) as client:
        result = fetch_pvgis(client=client)
    assert result.source_id == "pvgis"
    assert result.status_code == 200


def test_aemet_follows_data_url_without_persisting_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "opendata/api/valores" in str(request.url):
            assert request.url.params["api_key"] == "test-secret"
            return httpx.Response(
                200,
                json={"estado": 200, "datos": "https://datos.aemet.test/observations?token=short"},
                request=request,
            )
        return httpx.Response(
            200,
            json=[{"indicativo": "3195", "fecha": "2026-07-20", "tmed": "27,4"}],
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch_aemet(api_key="test-secret", client=client)
    assert result.source_id == "aemet"
    assert result.payload["records"][0]["indicativo"] == "3195"
    assert "?" not in result.requested_url
    assert "test-secret" not in result.requested_url


def test_aemet_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AEMET_API_KEY", raising=False)
    with pytest.raises(SourceError, match="AEMET_API_KEY"):
        fetch_aemet(api_key="")
