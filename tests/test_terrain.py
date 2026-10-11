from functools import partial

import numpy as np
import pytest

from spectralforge.terrain import (
    TerrainGeometry,
    TerrainHorizons,
    cos_incidence,
    horizon_elevation,
    sample_geometry_from_dem,
    sample_geometry_uniform,
    sky_view_factor,
    slope_aspect_from_dem,
)


def test_flat_terrain_cos_i_equals_cos_solar_zenith():
    sz = np.array([0.0, 30.0, 60.0])
    np.testing.assert_allclose(cos_incidence(sz, 123.0, 0.0, 45.0), np.cos(np.radians(sz)))


def test_slope_facing_sun_at_solar_zenith_is_normal_incidence():
    assert cos_incidence(35.0, 140.0, 35.0, 140.0) == pytest.approx(1.0)


def test_slope_facing_away_beyond_horizon_is_self_shadowed():
    # Sun from the south at 50° zenith, steep north-facing slope (aspect 0°) of 45°.
    assert cos_incidence(50.0, 180.0, 45.0, 0.0) < 0


@pytest.mark.parametrize(
    ("rising_towards", "expected_aspect"),
    [("east", 270.0), ("north", 180.0), ("west", 90.0), ("south", 0.0)],
)
def test_slope_aspect_from_dem_planes(rising_towards, expected_aspect):
    rows, cols = np.mgrid[0:5, 0:5].astype(float)  # rows grow southward
    pixel = 10.0
    dem = {
        "east": cols * pixel * 0.5,
        "west": -cols * pixel * 0.5,
        "north": -rows * pixel * 0.5,
        "south": rows * pixel * 0.5,
    }[rising_towards]
    slope, aspect = slope_aspect_from_dem(dem, pixel)
    np.testing.assert_allclose(slope, np.degrees(np.arctan(0.5)))
    np.testing.assert_allclose(aspect, expected_aspect)


def test_uniform_sampler_rejects_self_shadow_and_is_reproducible():
    kwargs = dict(solar_zenith_deg=60.0, slope_deg=(0.0, 60.0))
    g1 = sample_geometry_uniform(np.random.default_rng(0), 500, **kwargs)
    g2 = sample_geometry_uniform(np.random.default_rng(0), 500, **kwargs)
    assert len(g1) == 500
    assert np.all(g1.cos_i > 0)
    np.testing.assert_array_equal(g1.slope_deg, g2.slope_deg)


def test_uniform_sampler_fails_loudly_when_no_illuminated_terrain():
    with pytest.raises(ValueError, match="cos i"):
        sample_geometry_uniform(
            np.random.default_rng(0),
            10,
            solar_zenith_deg=80.0,
            solar_azimuth_deg=180.0,
            slope_deg=60.0,
            aspect_deg=0.0,
        )


def test_dem_sampler_draws_only_valid_pixels():
    slope = np.array([[10.0, np.nan], [20.0, 30.0]])
    aspect = np.array([[180.0, 0.0], [180.0, 180.0]])
    sampler = partial(
        sample_geometry_from_dem,
        slope_deg=slope,
        aspect_deg=aspect,
        solar_zenith_deg=40.0,
        solar_azimuth_deg=(170.0, 190.0),
    )
    g = sampler(np.random.default_rng(1), 200)
    assert len(g) == 200
    assert set(np.unique(g.slope_deg)) <= {10.0, 20.0, 30.0}


def test_geometry_rejects_sun_below_horizon():
    with pytest.raises(ValueError, match="horizon"):
        TerrainGeometry(np.array([95.0]), np.array([0.0]), np.array([0.0]), np.array([0.0]))


# --- horizons, sky view, cast shadows -----------------------------------------------------


def wall_dem(height=50.0, size=21, wall_col=15):
    """Flat plain with a north-south wall of `height` from column `wall_col` eastward."""
    dem = np.zeros((size, size))
    dem[:, wall_col:] = height
    return dem


@pytest.mark.parametrize("slope", [0.0, 10.0, 30.0, 60.0])
def test_sky_view_of_unobstructed_slope_matches_analytic(slope):
    az = np.arange(0, 360, 1.0)
    v = sky_view_factor(np.full(az.size, -5.0), az, slope, 135.0)
    assert v == pytest.approx((1 + np.cos(np.radians(slope))) / 2, abs=1e-4)


def test_sky_view_of_flat_pixel_with_uniform_horizon():
    az = np.arange(0, 360, 1.0)
    assert sky_view_factor(np.full(az.size, 30.0), az, 0.0, 0.0) == pytest.approx(0.75)


def test_horizon_elevation_towards_wall():
    h = horizon_elevation(wall_dem(), 10.0, azimuth_deg=90.0, max_distance=200.0)
    # 5 columns (50 m) west of a 50 m wall -> 45 degrees.
    assert h[10, 10] == pytest.approx(45.0)
    assert h[10, 2] < h[10, 10]


def test_flat_dem_sees_whole_sky_and_casts_no_shadow():
    horizons = TerrainHorizons.from_dem(np.zeros((9, 9)), 10.0, n_directions=16)
    np.testing.assert_allclose(horizons.sky_view(), 1.0)
    idx = np.arange(81)
    assert np.all(horizons.cast_shadow(np.full(81, 80.0), np.full(81, 90.0), idx) == 0)


def test_wall_casts_shadow_on_low_sun_side_and_reduces_sky_view():
    horizons = TerrainHorizons.from_dem(wall_dem(), 10.0, n_directions=32, max_distance=300.0)
    pixel_west = np.ravel_multi_index((10, 12), (21, 21))  # 30 m west of the wall
    pixel_far = np.ravel_multi_index((10, 1), (21, 21))
    low_sun_east = horizons.cast_shadow(
        np.array([70.0, 70.0]), np.array([90.0, 90.0]), np.array([pixel_west, pixel_far])
    )
    np.testing.assert_array_equal(low_sun_east, [1.0, 0.0])
    sun_west = horizons.cast_shadow(np.array([70.0]), np.array([270.0]), np.array([pixel_west]))
    assert sun_west[0] == 0.0
    sky = horizons.sky_view()
    assert sky[10, 12] < sky[10, 1] <= 1.0


def test_dem_sampler_with_horizons_fills_sky_view_and_shadow():
    horizons = TerrainHorizons.from_dem(wall_dem(), 10.0, n_directions=16, max_distance=300.0)
    g = sample_geometry_from_dem(
        np.random.default_rng(3),
        300,
        horizons.slope_deg,
        horizons.aspect_deg,
        solar_zenith_deg=75.0,
        solar_azimuth_deg=90.0,
        horizons=horizons,
    )
    assert g.sky_view is not None and g.cast_shadow is not None
    assert 0 < g.cast_shadow.mean() < 1
    assert np.all((g.sky_view > 0) & (g.sky_view <= 1))


def test_geometry_optional_fields_survive_subset_and_concatenate():
    g = TerrainGeometry(
        np.array([30.0, 40.0]),
        np.zeros(2),
        np.zeros(2),
        np.zeros(2),
        sky_view=np.array([0.9, 0.8]),
        cast_shadow=np.array([0.0, 1.0]),
    )
    both = TerrainGeometry.concatenate([g, g.subset(np.array([1]))])
    np.testing.assert_array_equal(both.cast_shadow, [0.0, 1.0, 1.0])
    plain = TerrainGeometry(np.array([30.0]), np.zeros(1), np.array([60.0]), np.zeros(1))
    assert TerrainGeometry.concatenate([g, plain]).sky_view is None
    assert plain.sky_view_or_default[0] == pytest.approx(0.75)
    assert plain.cast_shadow_or_default[0] == 0.0
