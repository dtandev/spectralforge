from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from spectralforge.solar import solar_position, time_range, to_utc

# Reference values: NREL SPA (pvlib.solarposition.spa_python, altitude as given).
SPA_CASES = [
    # time UTC, lat, lon, zenith, azimuth
    ("2026-06-21T14:30:00Z", -21.87, -68.80, 54.8462, 36.2053),  # El Abra, austral winter
    ("2026-12-21T15:00:00Z", -21.87, -68.80, 21.5661, 98.6526),  # El Abra, austral summer
    ("2026-06-21T10:00:00Z", 50.06, 19.94, 27.8601, 159.0146),  # Kraków
    ("2026-01-15T11:00:00Z", 69.65, 18.96, 90.7361, 181.5075),  # Tromsø, polar night
]


@pytest.mark.parametrize(("time", "lat", "lon", "zenith", "azimuth"), SPA_CASES)
def test_matches_nrel_spa(time, lat, lon, zenith, azimuth):
    sun = solar_position(time, lat, lon)
    assert sun.zenith_deg[0] == pytest.approx(zenith, abs=0.02)
    assert sun.azimuth_deg[0] == pytest.approx(azimuth, abs=0.02)


def test_sun_below_horizon_in_polar_night():
    sun = solar_position("2026-01-15T11:00:00Z", 69.65, 18.96)
    assert not sun.above_horizon[0]
    assert sun.elevation_deg[0] < 0


def test_refraction_lifts_the_sun_most_near_the_horizon():
    sun = solar_position(["2026-06-21T12:00Z", "2026-06-21T16:30Z"], -21.87, -68.80)
    lift = sun.zenith_deg - sun.apparent_zenith_deg
    assert np.all(lift > 0)
    assert lift[0] > lift[1]  # 12:00Z — Sun low; 16:30Z — near noon


def test_southern_hemisphere_noon_sun_is_north_and_morning_sun_is_east():
    noon = solar_position("2026-06-21T16:37Z", -21.87, -68.80)  # ~local solar noon
    assert min(noon.azimuth_deg[0], 360 - noon.azimuth_deg[0]) < 3
    assert abs(noon.hour_angle_deg[0]) < 1.5
    morning = solar_position("2026-06-21T13:00Z", -21.87, -68.80)
    assert 0 < morning.azimuth_deg[0] < 90


def test_earth_sun_distance_is_smallest_in_january():
    sun = solar_position(["2026-01-03T12:00Z", "2026-07-05T12:00Z"], 0.0, 0.0)
    assert sun.earth_sun_distance_au[0] < 0.984 < 1.016 < sun.earth_sun_distance_au[1]
    assert sun.irradiance_factor[0] > 1 > sun.irradiance_factor[1]


def test_broadcasts_times_against_locations():
    times = time_range("2026-06-21T12:00Z", "2026-06-21T14:00Z", "1h")
    sun = solar_position(times[:, None], np.array([-21.9, 50.1]), np.array([-68.8, 19.9]))
    assert sun.zenith_deg.shape == (3, 2)
    assert sun.times_utc.shape == (3, 2)


def test_to_utc_handles_offsets_aware_and_naive_values():
    expected = np.datetime64("2026-06-21T14:30:00")
    aware = datetime(2026, 6, 21, 10, 30, tzinfo=timezone(timedelta(hours=-4)))
    values = to_utc(["2026-06-21T10:30-04:00", "2026-06-21T14:30Z", aware, "2026-06-21T14:30"])
    np.testing.assert_array_equal(values, expected)


def test_time_range_is_inclusive_and_validates_step():
    times = time_range("2026-06-21T10:00Z", "2026-06-21T11:00Z", "15min")
    assert len(times) == 5
    assert times[-1] == np.datetime64("2026-06-21T11:00:00")
    with pytest.raises(ValueError, match="step"):
        time_range("2026-06-21T10:00Z", "2026-06-21T11:00Z", "quarter")


def test_rejects_invalid_coordinates():
    with pytest.raises(ValueError, match="latitude"):
        solar_position("2026-06-21T12:00Z", 95.0, 0.0)
