from renewableops.battery import optimize_dispatch
from renewableops.geospatial import Station, nearest_station


def test_dispatch_respects_soc_and_exclusivity():
    schedule, _ = optimize_dispatch(
        [20, 18, 25, 70, 90, 60],
        capacity_mwh=10,
        max_power_mw=4,
    )
    assert all(1 <= item.state_of_charge_mwh <= 10 for item in schedule)
    assert all(not (item.charge_mw and item.discharge_mw) for item in schedule)


def test_nearest_station_honors_distance_cap():
    stations = [
        Station("MAD", 40.4168, -3.7038),
        Station("BCN", 41.3874, 2.1686),
    ]
    match = nearest_station(40.40, -3.70, stations, maximum_distance_km=20)
    assert match is not None
    assert match[0].station_id == "MAD"
