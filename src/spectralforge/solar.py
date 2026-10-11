"""B0 — solar position for given times and places.

Implements the NOAA solar position algorithm (the one behind the NOAA Solar Calculator,
after Meeus, *Astronomical Algorithms*), vectorised over times and locations. Accuracy is
about 0.01° for dates within a few centuries of 2000 — far below what matters for the
illumination models of B1 (checked against NREL SPA in the tests).

Conventions match `spectralforge.terrain`: azimuth is the direction TO the Sun, clockwise
from north; zenith 0° = Sun overhead. Times are UTC: timezone-aware datetimes and ISO
strings with an offset (e.g. "2026-06-21T10:30-04:00") are converted, naive values are
taken as UTC.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

TimesLike = str | datetime | np.datetime64 | Iterable[str | datetime | np.datetime64]


def to_utc(times: TimesLike) -> np.ndarray:
    """Times as a `datetime64[s]` array in UTC.

    A `datetime64` array is taken as UTC and keeps its shape (so times can be broadcast
    against locations); anything else becomes a 1-D array.
    """
    if isinstance(times, np.ndarray) and np.issubdtype(times.dtype, np.datetime64):
        return times.astype("datetime64[s]")
    if isinstance(times, str | datetime | np.datetime64):
        times = [times]
    converted = []
    for t in times:
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if isinstance(t, datetime):
            if t.tzinfo is not None:
                t = t.astimezone(UTC).replace(tzinfo=None)
            t = np.datetime64(t, "s")
        converted.append(np.datetime64(t, "s"))
    return np.array(converted, dtype="datetime64[s]")


def time_range(start: TimesLike, end: TimesLike, step: str) -> np.ndarray:
    """UTC times from `start` to `end` inclusive every `step` ("15min", "1h", "1d", "30s")."""
    units = {"s": "s", "sec": "s", "min": "m", "m": "m", "h": "h", "d": "D"}
    number = "".join(ch for ch in step if ch.isdigit() or ch == ".")
    unit = step[len(number) :].strip().lower()
    if unit not in units or not number or float(number) <= 0 or float(number) != int(float(number)):
        raise ValueError(f"step must look like '15min', '1h', '1d' or '30s', got {step!r}")
    delta = np.timedelta64(int(number), units[unit]).astype("timedelta64[s]")
    t0, t1 = to_utc(start)[0], to_utc(end)[0]
    if t1 < t0:
        raise ValueError("end must not be before start")
    return np.arange(t0, t1 + np.timedelta64(1, "s"), delta)


@dataclass(frozen=True)
class SolarPosition:
    """Solar geometry for each (time, location); all arrays broadcast to the same shape."""

    times_utc: np.ndarray
    latitude_deg: np.ndarray
    longitude_deg: np.ndarray
    zenith_deg: np.ndarray  # geometric (no refraction)
    apparent_zenith_deg: np.ndarray  # with atmospheric refraction — what an observer sees
    azimuth_deg: np.ndarray  # clockwise from north, direction to the Sun
    declination_deg: np.ndarray
    hour_angle_deg: np.ndarray  # 0 at local solar noon, negative in the morning
    equation_of_time_min: np.ndarray
    earth_sun_distance_au: np.ndarray
    local_solar_time_h: np.ndarray

    @property
    def elevation_deg(self) -> np.ndarray:
        """Apparent solar elevation above the horizon (90° − apparent zenith)."""
        return 90.0 - self.apparent_zenith_deg

    @property
    def above_horizon(self) -> np.ndarray:
        return self.apparent_zenith_deg < 90.0

    @property
    def irradiance_factor(self) -> np.ndarray:
        """(1 AU / d)² — scales top-of-atmosphere irradiance for the Earth–Sun distance."""
        return 1.0 / self.earth_sun_distance_au**2


def solar_position(
    times: TimesLike,
    latitude_deg: np.ndarray | float,
    longitude_deg: np.ndarray | float,
    pressure_hpa: float = 1010.0,
    temperature_c: float = 10.0,
) -> SolarPosition:
    """Solar position (NOAA algorithm) for every time × location (numpy broadcasting).

    `pressure_hpa` / `temperature_c` scale the refraction correction (NOAA's formula is for
    1010 hPa and 10 °C); refraction only matters close to the horizon.
    """
    times_utc = to_utc(times)
    lat = np.asarray(latitude_deg, dtype=float)
    lon = np.asarray(longitude_deg, dtype=float)
    if np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 180):
        raise ValueError("latitude must be within ±90° and longitude within ±180°")

    unix_s = times_utc.astype("int64").astype(float)
    julian_day = unix_s / 86400.0 + 2440587.5
    jc = (julian_day - 2451545.0) / 36525.0  # Julian centuries since J2000

    mean_long = np.mod(280.46646 + jc * (36000.76983 + jc * 0.0003032), 360.0)
    mean_anom = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    eccentricity = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    m = np.radians(mean_anom)
    centre = (
        np.sin(m) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + np.sin(2 * m) * (0.019993 - 0.000101 * jc)
        + np.sin(3 * m) * 0.000289
    )
    true_long = mean_long + centre
    true_anom = mean_anom + centre
    distance = (1.000001018 * (1 - eccentricity**2)) / (
        1 + eccentricity * np.cos(np.radians(true_anom))
    )
    omega = np.radians(125.04 - 1934.136 * jc)
    apparent_long = np.radians(true_long - 0.00569 - 0.00478 * np.sin(omega))
    mean_obliquity = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliquity = np.radians(mean_obliquity + 0.00256 * np.cos(omega))
    declination = np.arcsin(np.sin(obliquity) * np.sin(apparent_long))

    y = np.tan(obliquity / 2) ** 2
    l0 = np.radians(mean_long)
    eot_min = 4 * np.degrees(
        y * np.sin(2 * l0)
        - 2 * eccentricity * np.sin(m)
        + 4 * eccentricity * y * np.sin(m) * np.cos(2 * l0)
        - 0.5 * y**2 * np.sin(4 * l0)
        - 1.25 * eccentricity**2 * np.sin(2 * m)
    )

    minutes_utc = np.mod(unix_s, 86400.0) / 60.0
    true_solar_min = np.mod(minutes_utc + eot_min + 4 * lon, 1440.0)
    hour_angle = np.radians(true_solar_min / 4 - 180.0)

    phi = np.radians(lat)
    cos_zenith = np.sin(phi) * np.sin(declination) + np.cos(phi) * np.cos(declination) * np.cos(
        hour_angle
    )
    zenith = np.degrees(np.arccos(np.clip(cos_zenith, -1.0, 1.0)))
    azimuth = np.mod(
        np.degrees(
            np.arctan2(
                np.sin(hour_angle),
                np.cos(hour_angle) * np.sin(phi) - np.tan(declination) * np.cos(phi),
            )
        )
        + 180.0,
        360.0,
    )
    refraction = (
        _refraction_deg(90.0 - zenith) * (pressure_hpa / 1010.0) * (283.0 / (273.0 + temperature_c))
    )

    shape = np.broadcast(zenith, lat, lon).shape
    expand = lambda a: np.broadcast_to(a, shape).copy()  # noqa: E731
    return SolarPosition(
        times_utc=expand(times_utc),
        latitude_deg=expand(lat),
        longitude_deg=expand(lon),
        zenith_deg=expand(zenith),
        apparent_zenith_deg=expand(zenith - refraction),
        azimuth_deg=expand(azimuth),
        declination_deg=expand(np.degrees(declination)),
        hour_angle_deg=expand(np.degrees(hour_angle)),
        equation_of_time_min=expand(eot_min),
        earth_sun_distance_au=expand(distance),
        local_solar_time_h=expand(true_solar_min / 60.0),
    )


def _refraction_deg(elevation_deg: np.ndarray) -> np.ndarray:
    """NOAA's piecewise approximation of atmospheric refraction (degrees)."""
    e = np.asarray(elevation_deg, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.tan(np.radians(e))
        arcsec = np.select(
            [e > 85.0, e > 5.0, e > -0.575],
            [
                0.0,
                58.1 / t - 0.07 / t**3 + 0.000086 / t**5,
                1735.0 + e * (-518.2 + e * (103.4 + e * (-12.79 + e * 0.711))),
            ],
            default=-20.772 / t,
        )
    return arcsec / 3600.0
