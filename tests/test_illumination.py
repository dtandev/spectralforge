from functools import partial

import numpy as np
import pytest

from spectralforge.operators.illumination import (
    c_correction,
    c_factor,
    c_illumination,
    cosine_correction,
    cosine_factor,
    cosine_illumination,
    fit_c_coefficients,
    fit_minnaert_k,
    generate_c_correction,
    generate_cosine,
    generate_minnaert,
    generate_physical,
    minnaert_correction,
    minnaert_factor,
    minnaert_illumination,
    physical_correction,
    physical_factor,
    physical_illumination,
)
from spectralforge.terrain import cos_incidence, sample_geometry_uniform

RNG_SEED = 42


@pytest.fixture
def spectra():
    wl = np.linspace(400, 2500, 50)
    return np.stack([0.4 + 0.1 * np.sin(wl / 300), 0.6 - 0.2 * np.exp(-(((wl - 2200) / 30) ** 2))])


def test_flat_terrain_is_identity(spectra):
    sz = np.array([25.0, 55.0])
    out = cosine_illumination(spectra, np.cos(np.radians(sz)), sz)
    np.testing.assert_allclose(out, spectra)


def test_spectral_shape_is_preserved(spectra):
    out = cosine_illumination(spectra, np.array([0.3, 0.9]), 40.0)
    ratio = out / spectra
    np.testing.assert_allclose(ratio, ratio[:, :1] * np.ones_like(ratio))


def test_self_shadowed_pixel_is_black(spectra):
    out = cosine_illumination(spectra, np.array([-0.2, 0.0]), 30.0)
    np.testing.assert_array_equal(out, 0.0)


def test_sun_facing_slope_is_brighter_and_not_clipped(spectra):
    out = cosine_illumination(spectra, 1.0, 60.0)  # factor = 1 / cos 60° = 2
    np.testing.assert_allclose(out, 2 * spectra)
    assert out.max() > 1.0


def test_generation_then_correction_round_trip(spectra):
    cos_i = np.array([0.5, 0.95])
    out = cosine_correction(cosine_illumination(spectra, cos_i, 35.0), cos_i, 35.0)
    np.testing.assert_allclose(out, spectra)


def test_correction_masks_weakly_illuminated_pixels(spectra):
    out = cosine_correction(spectra, np.array([0.01, 0.5]), 35.0)
    assert np.all(np.isnan(out[0]))
    assert np.all(np.isfinite(out[1]))


def test_generate_cosine_batch(spectra):
    sampler = partial(sample_geometry_uniform, solar_zenith_deg=(20.0, 50.0))
    batch = generate_cosine(spectra, 30, sampler, np.random.default_rng(RNG_SEED))

    assert batch.reflectance.shape == (60, spectra.shape[1])
    np.testing.assert_array_equal(np.bincount(batch.source_index), [30, 30])
    expected = spectra[batch.source_index] * batch.illumination_factor[:, None]
    np.testing.assert_allclose(batch.reflectance, expected)
    assert np.all(batch.illumination_factor > 0)

    params = batch.parameters(0)
    assert params["model"] == "cosine"
    assert params["illumination_factor"] == pytest.approx(
        params["cos_i"] / np.cos(np.radians(params["solar_zenith_deg"]))
    )


def test_generate_cosine_accepts_single_spectrum(spectra):
    batch = generate_cosine(spectra[0], 5, sample_geometry_uniform, np.random.default_rng(0))
    assert batch.reflectance.shape == (5, spectra.shape[1])


# --- C-correction -------------------------------------------------------------------------


@pytest.fixture
def c_coefficients(spectra):
    return np.linspace(0.5, 0.03, spectra.shape[1])  # blue-to-SWIR-like decrease


def test_c_model_with_zero_c_equals_cosine_model(spectra):
    cos_i, sz = np.array([0.3, 0.9]), 40.0
    np.testing.assert_allclose(
        c_illumination(spectra, cos_i, sz, np.zeros(spectra.shape[1])),
        cosine_illumination(spectra, cos_i, sz),
    )


def test_c_model_flat_terrain_is_identity(spectra, c_coefficients):
    sz = np.array([25.0, 55.0])
    out = c_illumination(spectra, np.cos(np.radians(sz)), sz, c_coefficients)
    np.testing.assert_allclose(out, spectra)


def test_c_model_self_shadow_keeps_diffuse_light(spectra, c_coefficients):
    factor = c_factor(np.array([-0.3]), 40.0, c_coefficients)[0]
    np.testing.assert_allclose(factor, c_coefficients / (np.cos(np.radians(40.0)) + c_coefficients))
    assert np.all(factor > 0)


def test_c_model_changes_spectral_shape_on_shaded_slope(spectra, c_coefficients):
    # Weakly lit slope: more diffuse light (larger c) → relatively brighter band.
    factor = c_factor(np.array([0.2]), 40.0, c_coefficients)[0]
    assert np.all(np.diff(factor) < 0)


def test_c_generation_then_correction_round_trip(spectra, c_coefficients):
    cos_i = np.array([-0.1, 0.95])
    out = c_correction(
        c_illumination(spectra, cos_i, 35.0, c_coefficients), cos_i, 35.0, c_coefficients
    )
    np.testing.assert_allclose(out, spectra)


def test_fit_c_coefficients_recovers_known_c(spectra, c_coefficients):
    rng = np.random.default_rng(RNG_SEED)
    cos_i = rng.uniform(0.1, 1.0, 400)
    pixels = c_illumination(
        np.broadcast_to(spectra[0], (400, spectra.shape[1])), cos_i, 40.0, c_coefficients
    )
    np.testing.assert_allclose(fit_c_coefficients(pixels, cos_i), c_coefficients)


def test_fit_c_coefficients_rejects_constant_cos_i(spectra):
    with pytest.raises(ValueError, match="spread"):
        fit_c_coefficients(spectra, np.array([0.5, 0.5]))


def test_generate_c_correction_clear_sky(spectra):
    wl = np.linspace(400, 2500, spectra.shape[1])
    sampler = partial(sample_geometry_uniform, solar_zenith_deg=(20.0, 50.0), min_cos_i=-1.0)
    batch = generate_c_correction(
        spectra, 20, sampler, np.random.default_rng(RNG_SEED), wavelengths_nm=wl, elevation_km=4.0
    )
    assert batch.reflectance.shape == (40, spectra.shape[1])
    assert batch.illumination_factor.shape == (40, spectra.shape[1])
    assert np.all(batch.reflectance > 0)  # self-shadowed samples keep diffuse light

    params = batch.parameters(3)
    assert params["model"] == "c_correction"
    assert params["c_source"] == "clear_sky"
    assert 0.05 <= params["aot_550"] <= 0.3
    assert params["elevation_km"] == 4.0
    assert params["illumination_factor_min"] <= params["illumination_factor_max"]


def test_generate_c_correction_fixed_c(spectra, c_coefficients):
    batch = generate_c_correction(
        spectra, 5, sample_geometry_uniform, np.random.default_rng(0), c=c_coefficients
    )
    g = batch.geometry
    expected = c_illumination(
        spectra[batch.source_index], g.cos_i, g.solar_zenith_deg, c_coefficients
    )
    np.testing.assert_allclose(batch.reflectance, expected)
    assert batch.parameters(0)["c_source"] == "fixed"


def test_generate_c_correction_needs_wavelengths_without_c(spectra):
    with pytest.raises(ValueError, match="wavelengths_nm"):
        generate_c_correction(spectra, 2, sample_geometry_uniform, np.random.default_rng(0))


# --- Minnaert -----------------------------------------------------------------------------


def test_minnaert_with_k_one_equals_cosine_model(spectra):
    cos_i, sz = np.array([0.3, 0.9]), 40.0
    cosine = cosine_illumination(spectra, cos_i, sz)
    np.testing.assert_allclose(minnaert_illumination(spectra, cos_i, sz, 1.0), cosine)
    np.testing.assert_allclose(
        minnaert_illumination(spectra, cos_i, sz, 1.0, cos_e=np.array([0.8, 0.95])), cosine
    )


@pytest.mark.parametrize("k", [0.4, 0.8, 1.2])
def test_minnaert_flat_terrain_is_identity(spectra, k):
    sz = np.array([25.0, 55.0])
    out = minnaert_illumination(spectra, np.cos(np.radians(sz)), sz, k, cos_e=np.ones(2))
    np.testing.assert_allclose(out, spectra)


def test_minnaert_k_below_one_dampens_illumination_contrast():
    sz, cos_sz = 40.0, np.cos(np.radians(40.0))
    shaded, sunlit = np.array([0.3 * cos_sz]), np.array([1.0])
    for cos_i in (shaded, sunlit):
        lambertian = cosine_factor(cos_i, sz)[0]
        damped = minnaert_factor(cos_i, sz, 0.6)[0, 0]
        assert abs(damped - 1) < abs(lambertian - 1)


def test_minnaert_self_shadow_is_black_and_invisible_pixel_is_nan(spectra):
    assert np.all(minnaert_illumination(spectra[:1], np.array([-0.2]), 30.0, 0.7) == 0)
    out = minnaert_illumination(spectra[:1], np.array([0.5]), 30.0, 0.7, cos_e=np.array([-0.1]))
    assert np.all(np.isnan(out))


def test_minnaert_only_per_band_k_changes_shape(spectra):
    cos_i = np.array([0.3])
    scalar = minnaert_illumination(spectra[:1], cos_i, 40.0, 0.7) / spectra[:1]
    per_band = (
        minnaert_illumination(spectra[:1], cos_i, 40.0, np.linspace(0.5, 0.9, spectra.shape[1]))
        / spectra[:1]
    )
    np.testing.assert_allclose(scalar, scalar[0, 0])
    assert np.ptp(per_band) > 0.05


def test_minnaert_generation_then_correction_round_trip(spectra):
    cos_i, cos_e = np.array([0.4, 0.95]), np.array([0.85, 0.99])
    k = np.linspace(0.5, 0.9, spectra.shape[1])
    out = minnaert_correction(
        minnaert_illumination(spectra, cos_i, 35.0, k, cos_e), cos_i, 35.0, k, cos_e
    )
    np.testing.assert_allclose(out, spectra)


@pytest.mark.parametrize("exitance", [True, False])
def test_fit_minnaert_k_recovers_known_k(spectra, exitance):
    rng = np.random.default_rng(RNG_SEED)
    k = np.linspace(0.5, 0.95, spectra.shape[1])
    slope, aspect = rng.uniform(0, 35, 400), rng.uniform(0, 360, 400)
    cos_i = cos_incidence(40.0, 150.0, slope, aspect)
    cos_e = np.cos(np.radians(slope)) if exitance else None  # nadir view: e = s
    keep = cos_i > 0.05
    pixels = minnaert_illumination(
        np.broadcast_to(spectra[0], (400, spectra.shape[1])), cos_i, 40.0, k, cos_e
    )
    fitted = fit_minnaert_k(pixels[keep], cos_i[keep], None if cos_e is None else cos_e[keep])
    np.testing.assert_allclose(fitted, k)


def test_generate_minnaert_random_k(spectra):
    batch = generate_minnaert(
        spectra, 25, sample_geometry_uniform, np.random.default_rng(RNG_SEED), k=(0.5, 0.9)
    )
    assert batch.reflectance.shape == (50, spectra.shape[1])
    assert batch.illumination_factor.shape == (50,)
    params = batch.parameters(0)
    assert params["model"] == "minnaert"
    assert params["k_source"] == "random"
    assert 0.5 <= params["k"] <= 0.9
    g = batch.geometry
    expected = minnaert_illumination(
        spectra[batch.source_index],
        g.cos_i,
        g.solar_zenith_deg,
        batch.extra["k"][:, None],
        np.cos(np.radians(g.slope_deg)),
    )
    np.testing.assert_allclose(batch.reflectance, expected)


def test_generate_minnaert_fixed_per_band_k_without_exitance(spectra):
    k = np.linspace(0.5, 0.9, spectra.shape[1])
    batch = generate_minnaert(
        spectra, 4, sample_geometry_uniform, np.random.default_rng(0), k=k, exitance=False
    )
    g = batch.geometry
    expected = minnaert_illumination(spectra[batch.source_index], g.cos_i, g.solar_zenith_deg, k)
    np.testing.assert_allclose(batch.reflectance, expected)
    assert batch.illumination_factor.shape == (8, spectra.shape[1])
    assert batch.parameters(0)["k_source"] == "fixed"
    assert batch.parameters(0)["exitance"] == "no"


# --- physical model -----------------------------------------------------------------------


@pytest.fixture
def anisotropy(spectra):
    return np.linspace(0.6, 0.95, spectra.shape[1])  # direct transmittance, blue to SWIR


@pytest.mark.parametrize("diffuse", ["isotropic", "hay"])
def test_physical_flat_open_terrain_is_identity(spectra, c_coefficients, anisotropy, diffuse):
    sz = np.array([25.0, 55.0])
    a = anisotropy if diffuse == "hay" else None
    out = physical_illumination(spectra, np.cos(np.radians(sz)), sz, c_coefficients, 1.0, 0.0, a)
    np.testing.assert_allclose(out, spectra)


def test_physical_reduces_to_c_model(spectra, c_coefficients):
    cos_i = np.array([-0.2, 0.6])
    out = physical_illumination(spectra, cos_i, 40.0, c_coefficients, 1.0, terrain_reflectance=None)
    np.testing.assert_allclose(out, c_illumination(spectra, cos_i, 40.0, c_coefficients))


def test_physical_cast_shadow_keeps_only_sky_light(c_coefficients):
    cos_sz = np.cos(np.radians(40.0))
    factor = physical_factor(np.array([0.9]), 40.0, c_coefficients, 0.8, cast_shadow=1.0)[0]
    np.testing.assert_allclose(factor, c_coefficients * 0.8 / (cos_sz + c_coefficients))


def test_hay_brightens_sunlit_slopes_and_darkens_cast_shadows(c_coefficients, anisotropy):
    cos_i = np.array([1.0])
    iso = physical_factor(cos_i, 40.0, c_coefficients, 0.9)[0]
    hay = physical_factor(cos_i, 40.0, c_coefficients, 0.9, anisotropy=anisotropy)[0]
    assert np.all(hay > iso)
    iso = physical_factor(cos_i, 40.0, c_coefficients, 0.9, cast_shadow=1.0)[0]
    hay = physical_factor(cos_i, 40.0, c_coefficients, 0.9, cast_shadow=1.0, anisotropy=anisotropy)[
        0
    ]
    assert np.all(hay < iso)


def test_terrain_reflected_light_adds_rho_adj_times_terrain_view(c_coefficients):
    without = physical_factor(np.array([0.5]), 40.0, c_coefficients, 0.7)
    with_terrain = physical_factor(
        np.array([0.5]), 40.0, c_coefficients, 0.7, terrain_reflectance=0.4
    )
    np.testing.assert_allclose(with_terrain - without, 0.4 * 0.3)


@pytest.mark.parametrize("terrain", ["self", "background", None])
def test_physical_generation_then_correction_round_trip(
    spectra, c_coefficients, anisotropy, terrain
):
    rho_adj = spectra[1] if terrain == "background" else terrain
    kwargs = dict(
        c=c_coefficients,
        sky_view=np.array([0.7, 0.95]),
        cast_shadow=np.array([1.0, 0.0]),
        anisotropy=anisotropy,
        terrain_reflectance=rho_adj,
    )
    cos_i = np.array([0.4, 0.9])
    apparent = physical_illumination(spectra, cos_i, 35.0, **kwargs)
    np.testing.assert_allclose(physical_correction(apparent, cos_i, 35.0, **kwargs), spectra)


def test_generate_physical_default_geometry(spectra):
    wl = np.linspace(400, 2500, spectra.shape[1])
    sampler = partial(sample_geometry_uniform, min_cos_i=-1.0)
    batch = generate_physical(
        spectra, 10, sampler, np.random.default_rng(RNG_SEED), wl, elevation_km=4.0
    )
    assert batch.reflectance.shape == (20, spectra.shape[1])
    assert np.all(batch.reflectance > 0)
    params = batch.parameters(0)
    assert params["model"] == "physical"
    assert params["diffuse"] == "hay"
    assert params["terrain_reflectance"] == "self"
    assert params["cast_shadow"] == 0.0
    assert params["sky_view"] == pytest.approx((1 + np.cos(np.radians(params["slope_deg"]))) / 2)


def test_generate_physical_rejects_unknown_diffuse_model(spectra):
    with pytest.raises(ValueError, match="diffuse"):
        generate_physical(
            spectra,
            1,
            sample_geometry_uniform,
            np.random.default_rng(0),
            np.linspace(400, 2500, spectra.shape[1]),
            diffuse="perez",
        )
