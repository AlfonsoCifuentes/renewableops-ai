"""Official-source HTTP clients with provenance, retries and bounded fallbacks."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


@dataclass(frozen=True)
class SourcePayload:
    source_id: str
    requested_url: str
    extracted_at: str
    status_code: int
    checksum_sha256: str
    payload: dict[str, Any]


class SourceError(RuntimeError):
    """Raised when an official source cannot provide a valid bounded response."""


def _payload(source_id: str, response: httpx.Response) -> SourcePayload:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise SourceError(f"{source_id} returned HTTP {response.status_code}") from error
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError) as error:
        raise SourceError(f"{source_id} returned non-JSON content") from error
    if not isinstance(body, dict):
        body = {"records": body}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return SourcePayload(
        source_id=source_id,
        requested_url=str(response.request.url).split("?")[0],
        extracted_at=datetime.now(UTC).isoformat(),
        status_code=response.status_code,
        checksum_sha256=hashlib.sha256(encoded).hexdigest(),
        payload=body,
    )


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, SourceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.4, max=4),
    reraise=True,
)
def fetch_redata(
    *,
    start: str = "2026-07-20T00:00",
    end: str = "2026-07-21T23:59",
    client: httpx.Client | None = None,
) -> SourcePayload:
    """Fetch a small national generation structure window from REData."""

    owns_client = client is None
    active_client = client or httpx.Client(timeout=20, headers={"User-Agent": "RenewableOpsAI/1.0"})
    try:
        response = active_client.get(
            "https://apidatos.ree.es/es/datos/generacion/estructura-generacion",
            params={
                "start_date": start,
                "end_date": end,
                "time_trunc": "hour",
                "geo_trunc": "electric_system",
                "geo_limit": "peninsular",
            },
        )
        return _payload("ree_redata", response)
    finally:
        if owns_client:
            active_client.close()


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, SourceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.4, max=4),
    reraise=True,
)
def fetch_pvgis(
    *,
    latitude: float = 39.39,
    longitude: float = -3.21,
    client: httpx.Client | None = None,
) -> SourcePayload:
    """Fetch PVGIS monthly radiation for one representative portfolio location."""

    owns_client = client is None
    active_client = client or httpx.Client(timeout=25, headers={"User-Agent": "RenewableOpsAI/1.0"})
    try:
        response = active_client.get(
            "https://re.jrc.ec.europa.eu/api/v5_3/MRcalc",
            params={
                "lat": latitude,
                "lon": longitude,
                "horirrad": 1,
                "optrad": 1,
                "selectrad": 1,
                "outputformat": "json",
            },
        )
        return _payload("pvgis", response)
    finally:
        if owns_client:
            active_client.close()


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, SourceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.4, max=4),
    reraise=True,
)
def fetch_aemet(
    *,
    station_id: str = "3195",
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> SourcePayload:
    """Fetch AEMET daily observations through its documented two-step API.

    AEMET returns a short-lived ``datos`` URL in the first response. Neither
    the API key nor temporary query parameters are retained in provenance or
    surfaced through error messages.
    """

    token = api_key or os.getenv("AEMET_API_KEY")
    if not token:
        raise SourceError("aemet requires AEMET_API_KEY")
    owns_client = client is None
    active_client = client or httpx.Client(timeout=25, headers={"User-Agent": "RenewableOpsAI/1.0"})
    try:
        discovery = active_client.get(
            (
                "https://opendata.aemet.es/opendata/api/valores/"
                f"climatologicos/diarios/datos/fechaini/2026-07-20T00:00:00UTC/"
                f"fechafin/2026-07-21T23:59:59UTC/estacion/{station_id}"
            ),
            params={"api_key": token},
        )
        first = _payload("aemet_discovery", discovery)
        data_url = first.payload.get("datos")
        if not isinstance(data_url, str) or not data_url.startswith("https://"):
            raise SourceError("aemet discovery response omitted a valid datos URL")
        observations = active_client.get(data_url)
        return _payload("aemet", observations)
    finally:
        if owns_client:
            active_client.close()
