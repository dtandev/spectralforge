"""B0 — everything B1 needs about a region: Sun, terrain illumination, and a geometry sampler.

Typical flow:

    aoi = load_aoi("AOI.geojson")
    download_copernicus_dem(aoi, "data/dem/aoi_glo30.tif")
    region = load_region("data/dem/aoi_glo30.tif", aoi)
    sun = sun_for_aoi(aoi, time_range("2026-05-01T14:00Z", "2026-09-30T15:00Z", "1h"),
                      elevation_km=region.elevation_km)
    illum = terrain_illumination(region, sun.apparent_zenith_deg[k], sun.azimuth_deg[k])
    sampler = region_sampler(region, sun)            # → generate_physical(..., sampler, ...)
"""

from dataclasses import dataclass
from functools import partial

import numpy as np
from shapely.geometry.base import BaseGeometry

from spectralforge.dem import RegionDEM
from spectralforge.solar import SolarPosition, TimesLike, solar_position
from spectralforge.terrain import (
    GeometrySampler,
    TerrainHorizons,
    cos_incidence,
    horizon_elevation,
    sample_geometry_from_dem,
)

PRESSURE_SCALE_HEIGHT_KM = 8.4


def sun_for_aoi(aoi: BaseGeometry, times: TimesLike, elevation_km: float = 0.0) -> SolarPosition:
    """Solar position at the AOI centroid for each time.

    One point represents the whole AOI: across ~50 km the solar angles differ by well
    under 0.5°. `elevation_km` lowers the pressure used in the refraction correction.
    """
    lon, lat = aoi.centroid.coords[0][:2]
    pressure = 1013.25 * np.exp(-elevation_km / PRESSURE_SCALE_HEIGHT_KM)
    return solar_position(times, lat, lon, pressure_hpa=float(pressure))


@dataclass(frozen=True)
class TerrainIllumination:
    """Per-pixel illumination of a region for one Sun position."""

    solar_zenith_deg: float
    solar_azimuth_deg: float
    cos_i: np.ndarray  # (rows, cols)
    cast_shadow: np.ndarray  # (rows, cols) bool — Sun below the terrain horizon
    aoi_mask: np.ndarray  # (rows, cols) bool

    @property
    def incidence_deg(self) -> np.ndarray:
        """Local solar incidence angle i (0° = Sun perpendicular to the slope)."""
        return np.degrees(np.arccos(np.clip(self.cos_i, -1.0, 1.0)))

    @property
    def self_shadow(self) -> np.ndarray:
        """Slopes facing away from the Sun (cos i ≤ 0)."""
        return self.cos_i <= 0

    @property
    def directly_lit(self) -> np.ndarray:
        return ~self.self_shadow & ~self.cast_shadow & np.isfinite(self.cos_i)

    def summary(self) -> dict[str, float]:
        """Statistics over the AOI, e.g. to choose acquisition times or check a sampler."""
        inside = self.aoi_mask & np.isfinite(self.cos_i)
        cos_i = self.cos_i[inside]
        return {
            "solar_zenith_deg": self.solar_zenith_deg,
            "solar_azimuth_deg": self.solar_azimuth_deg,
            "cos_i_mean": float(cos_i.mean()),
            "cos_i_p05": float(np.percentile(cos_i, 5)),
            "cos_i_p95": float(np.percentile(cos_i, 95)),
            "incidence_deg_median": float(np.median(self.incidence_deg[inside])),
            "self_shadow_fraction": float(self.self_shadow[inside].mean()),
            "cast_shadow_fraction": float((self.cast_shadow & ~self.self_shadow)[inside].mean()),
            "directly_lit_fraction": float(self.directly_lit[inside].mean()),
        }


def terrain_illumination(
    region: RegionDEM,
    solar_zenith_deg: float,
    solar_azimuth_deg: float,
    max_shadow_distance_m: float = 5_000.0,
) -> TerrainIllumination:
    """cos i, self-shadow and cast-shadow maps of the region for one Sun position.

    Cast shadows trace the terrain towards the Sun up to `max_shadow_distance_m`; farther
    terrain is ignored (a 1 km ridge 5 km away rises ~11° — beyond that, shadows only
    matter at very low Sun).
    """
    if solar_zenith_deg >= 90.0:
        raise ValueError("the Sun is below the horizon")
    slope, aspect = region.slope_aspect
    cos_i = cos_incidence(solar_zenith_deg, solar_azimuth_deg, slope, aspect)
    horizon = horizon_elevation(
        region.elevation, region.pixel_size, solar_azimuth_deg, max_shadow_distance_m
    )
    return TerrainIllumination(
        solar_zenith_deg=float(solar_zenith_deg),
        solar_azimuth_deg=float(solar_azimuth_deg),
        cos_i=cos_i,
        cast_shadow=(90.0 - solar_zenith_deg) < horizon,
        aoi_mask=region.aoi_mask,
    )


def region_horizons(
    region: RegionDEM, n_directions: int = 16, max_distance_m: float = 5_000.0
) -> TerrainHorizons:
    """Horizons of the whole buffered DEM (for sky-view factors and per-draw cast shadows).

    Cost grows with pixels × directions × distance/pixel — for a ~40 km × 40 km region at
    30 m keep `max_distance_m` at a few km.
    """
    return TerrainHorizons.from_dem(
        region.elevation, region.pixel_size, n_directions=n_directions, max_distance=max_distance_m
    )


def region_sampler(
    region: RegionDEM,
    sun: SolarPosition,
    horizons: TerrainHorizons | None = None,
    min_cos_i: float = -1.0,
) -> GeometrySampler:
    """B1 geometry sampler for the region: AOI pixels × real Sun positions.

    Pixels are drawn from inside the AOI only (the buffer just provides context for
    horizons). Solar angles are drawn as real (apparent zenith, azimuth) pairs from `sun`,
    keeping only times with the Sun above the horizon. With `horizons` each draw also
    carries the pixel's sky-view factor and cast-shadow state. The default `min_cos_i=-1`
    keeps self-shadowed slopes, which C-correction and the physical model handle; use 0
    for the cosine and Minnaert models.
    """
    up = sun.above_horizon
    if not up.any():
        raise ValueError("the Sun is below the horizon at every given time")
    slope, aspect = region.slope_aspect
    return partial(
        sample_geometry_from_dem,
        slope_deg=slope,
        aspect_deg=aspect,
        min_cos_i=min_cos_i,
        horizons=horizons,
        sun_positions=(sun.apparent_zenith_deg[up], sun.azimuth_deg[up]),
        valid_mask=region.aoi_mask,
    )
