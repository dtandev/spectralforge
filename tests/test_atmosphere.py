import numpy as np
import pytest

from spectralforge.atmosphere import diffuse_to_direct_ratio, rayleigh_optical_depth

WL = np.array([450.0, 550.0, 865.0, 1650.0, 2200.0])


def test_rayleigh_optical_depth_at_550nm_matches_literature():
    assert rayleigh_optical_depth(550.0) == pytest.approx(0.097, abs=0.002)


def test_rayleigh_optical_depth_decreases_with_elevation():
    assert rayleigh_optical_depth(550.0, elevation_km=4.0) < rayleigh_optical_depth(550.0)


def test_diffuse_ratio_falls_from_blue_to_swir():
    c = diffuse_to_direct_ratio(WL, 40.0)
    assert np.all(np.diff(c) < 0)
    assert c[0] > 5 * c[-1]


def test_diffuse_ratio_grows_with_solar_zenith_and_aerosol():
    low_sun = diffuse_to_direct_ratio(WL, 60.0)
    high_sun = diffuse_to_direct_ratio(WL, 20.0)
    assert np.all(low_sun > high_sun)
    assert np.all(
        diffuse_to_direct_ratio(WL, 40.0, aot_550=0.4) > diffuse_to_direct_ratio(WL, 40.0)
    )


def test_diffuse_ratio_broadcasts_per_sample():
    c = diffuse_to_direct_ratio(WL, np.array([20.0, 40.0, 60.0]), aot_550=np.array([0.1, 0.2, 0.3]))
    assert c.shape == (3, WL.size)
