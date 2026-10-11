import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import box

from spectralforge.dem import RegionDEM
from spectralforge.region import (
    region_horizons,
    region_sampler,
    sun_for_aoi,
    terrain_illumination,
)
from spectralforge.solar import time_range

AOI = box(-68.95, -22.05, -68.85, -21.95)


@pytest.fixture
def ridge_region():
    """Flat plain at 3500 m with a 400 m north–south ridge; AOI = central block."""
    size = 60
    elevation = np.full((size, size), 3500.0)
    elevation[:, 30:34] = 3900.0
    mask = np.zeros((size, size), dtype=bool)
    mask[10:50, 10:50] = True
    return RegionDEM(
        elevation, from_origin(500_000, 7_570_000, 30, 30), CRS.from_epsg(32719), AOI, mask
    )


def test_sun_for_aoi_uses_centroid_and_site_pressure():
    times = time_range("2026-06-21T12:00Z", "2026-06-21T20:00Z", "4h")
    sea = sun_for_aoi(AOI, times)
    high = sun_for_aoi(AOI, times, elevation_km=4.0)
    np.testing.assert_allclose(sea.latitude_deg, -22.0)
    np.testing.assert_allclose(sea.zenith_deg, high.zenith_deg)
    lift_sea = sea.zenith_deg - sea.apparent_zenith_deg
    lift_high = high.zenith_deg - high.apparent_zenith_deg
    assert np.all(lift_high < lift_sea)  # thinner air, less refraction


def test_low_sun_from_east_shadows_the_west_side_of_the_ridge(ridge_region):
    illum = terrain_illumination(ridge_region, solar_zenith_deg=80.0, solar_azimuth_deg=90.0)
    assert illum.cast_shadow[25, 25]  # 5 px (150 m) west of a 400 m ridge, Sun 10° high
    assert not illum.cast_shadow[25, 40]  # east of the ridge
    summary = illum.summary()
    assert 0 < summary["cast_shadow_fraction"] < 0.5
    assert summary["directly_lit_fraction"] + summary["cast_shadow_fraction"] + summary[
        "self_shadow_fraction"
    ] == pytest.approx(1.0, abs=1e-9)
    np.testing.assert_allclose(illum.incidence_deg[25, 15], 80.0)  # flat ground: i = θs


def test_terrain_illumination_rejects_sun_below_horizon(ridge_region):
    with pytest.raises(ValueError, match="horizon"):
        terrain_illumination(ridge_region, 95.0, 90.0)


def test_region_sampler_draws_aoi_pixels_and_real_sun_pairs(ridge_region):
    sun = sun_for_aoi(AOI, time_range("2026-06-21T10:00Z", "2026-06-21T22:00Z", "1h"))
    sampler = region_sampler(ridge_region, sun, horizons=region_horizons(ridge_region, 8, 1500))
    g = sampler(np.random.default_rng(0), 400)
    up = sun.above_horizon
    pairs = set(
        zip(np.round(sun.apparent_zenith_deg[up], 9), np.round(sun.azimuth_deg[up], 9), strict=True)
    )
    assert (
        set(zip(np.round(g.solar_zenith_deg, 9), np.round(g.solar_azimuth_deg, 9), strict=True))
        <= pairs
    )
    assert np.all(g.solar_zenith_deg < 90)
    assert g.sky_view is not None and g.cast_shadow is not None
    # Only the AOI block holds ridge pixels with slopes; the plain outside is flat anyway,
    # so check the sky view: AOI pixels next to the ridge see less sky than open plain.
    assert g.sky_view.min() < 1.0


def test_region_sampler_needs_the_sun_up(ridge_region):
    night = sun_for_aoi(AOI, ["2026-06-21T06:00Z"])
    with pytest.raises(ValueError, match="below the horizon"):
        region_sampler(ridge_region, night)
