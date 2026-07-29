"""Official-source HTTP clients with provenance, retries and bounded fallbacks."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


@dataclass(frozen=True)
class SourcePayload:
    source_id: str
    requested_url: str
    extracted_at: str
    source_updated_at: str | None
    status_code: int
    checksum_sha256: str
    schema_fingerprint_sha256: str
    request_id: str
    response_headers: dict[str, str]
    payload: dict[str, Any]


class SourceError(RuntimeError):
    """Raised when an official source cannot provide a valid bounded response."""


def _sanitized_url(url: httpx.URL, secret_query_keys: frozenset[str]) -> str:
    """Keep reproducibility parameters while removing authentication material."""

    parsed = urlsplit(str(url))
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in secret_query_keys
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _shape(value: object, *, depth: int = 0) -> object:
    """Return a bounded structural signature without copying source values."""

    if depth >= 4:
        return type(value).__name__
    if isinstance(value, dict):
        return {
            str(key): _shape(item, depth=depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_shape(value[0], depth=depth + 1)] if value else []
    return type(value).__name__


def _source_updated_at(body: dict[str, Any], response: httpx.Response) -> str | None:
    updated = body.get("updated")
    if isinstance(updated, str):
        return updated
    data = body.get("data")
    if isinstance(data, dict):
        attributes = data.get("attributes")
        if isinstance(attributes, dict):
            last_update = attributes.get("last-update")
            if isinstance(last_update, str):
                return last_update
    last_modified = response.headers.get("last-modified")
    return last_modified if last_modified else None


def _payload(
    source_id: str,
    response: httpx.Response,
    *,
    secret_query_keys: frozenset[str] = frozenset(),
) -> SourcePayload:
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
    signature = json.dumps(_shape(body), sort_keys=True, separators=(",", ":")).encode()
    allowed_headers = {
        key.lower(): value
        for key, value in response.headers.items()
        if key.lower() in {"content-type", "etag", "last-modified"}
    }
    return SourcePayload(
        source_id=source_id,
        requested_url=_sanitized_url(response.request.url, secret_query_keys),
        extracted_at=datetime.now(UTC).isoformat(),
        source_updated_at=_source_updated_at(body, response),
        status_code=response.status_code,
        checksum_sha256=hashlib.sha256(encoded).hexdigest(),
        schema_fingerprint_sha256=hashlib.sha256(signature).hexdigest(),
        request_id=str(uuid.uuid4()),
        response_headers=allowed_headers,
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
    start: str = "2025-07-20T00:00",
    end: str = "2025-07-21T23:59",
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
                "time_trunc": "day",
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
def fetch_eurostat(
    *,
    geography: str = "ES",
    year: int = 2024,
    client: httpx.Client | None = None,
) -> SourcePayload:
    """Fetch Spain's official renewable-energy indicators from Eurostat."""

    owns_client = client is None
    active_client = client or httpx.Client(timeout=25, headers={"User-Agent": "RenewableOpsAI/1.0"})
    try:
        response = active_client.get(
            ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_ind_ren"),
            params={
                "lang": "EN",
                "geo": geography,
                "time": str(year),
            },
        )
        payload = _payload("eurostat_renewables", response)
        if payload.payload.get("class") != "dataset" or payload.payload.get("source") != "ESTAT":
            raise SourceError("eurostat_renewables returned an unexpected dataset envelope")
        return payload
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
        first = _payload(
            "aemet_discovery",
            discovery,
            secret_query_keys=frozenset({"api_key"}),
        )
        data_url = first.payload.get("datos")
        if not isinstance(data_url, str) or not data_url.startswith("https://"):
            raise SourceError("aemet discovery response omitted a valid datos URL")
        observations = active_client.get(data_url)
        return _payload(
            "aemet",
            observations,
            secret_query_keys=frozenset({"api_key", "token"}),
        )
    finally:
        if owns_client:
            active_client.close()
