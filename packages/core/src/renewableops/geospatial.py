"""Small, dependency-free geospatial utilities using WGS84 coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np


@dataclass(frozen=True)
class Station:
    station_id: str
    latitude: float
    longitude: float


def haversine_km(
    latitude: float,
    longitude: float,
    other_latitude: np.ndarray,
    other_longitude: np.ndarray,
) -> np.ndarray:
    """Vectorized great-circle distance for WGS84 latitude/longitude pairs."""

    earth_radius_km = 6371.0088
    lat1 = np.radians(latitude)
    lon1 = np.radians(longitude)
    lat2 = np.radians(other_latitude)
    lon2 = np.radians(other_longitude)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2) ** 2
    distance = earth_radius_km * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return cast(np.ndarray, distance)


def nearest_station(
    latitude: float,
    longitude: float,
    stations: list[Station],
    *,
    maximum_distance_km: float = 100,
) -> tuple[Station, float] | None:
    """Match an asset to its nearest station within an explicit distance cap."""

    if not stations:
        return None
    distances = haversine_km(
        latitude,
        longitude,
        np.asarray([station.latitude for station in stations]),
        np.asarray([station.longitude for station in stations]),
    )
    index = int(np.argmin(distances))
    distance = float(distances[index])
    if distance > maximum_distance_km:
        return None
    return stations[index], round(distance, 3)
