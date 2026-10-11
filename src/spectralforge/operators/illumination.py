"""B1 — illumination / topography operator (research plan Section 4.1.1).

Generation direction of the classical topographic corrections: from a reference
reflectance spectrum ρ_H (horizontal surface, e.g. a USGS library spectrum) simulate the
apparent reflectance ρ_T that a sensor product retrieves for a pixel on a slope, when the
atmospheric correction assumed flat terrain (i.e. NO topographic correction was applied).

Implemented models:

    cosine — Lambertian cosine model (Smith et al. 1980; Teillet et al. 1982)
        generation:  ρ_T = ρ_H · cos i / cos θ_s
        correction:  ρ_H = ρ_T · cos θ_s / cos i
        Direct irradiance only: no diffuse skylight, no cast shadows, no terrain-reflected
        light. The factor is wavelength independent — it changes brightness, never spectral
        shape, so it is invisible to SAM/cosine metrics and to continuum-removed spectra.
        Self-shadowed pixels (cos i ≤ 0) become black, unlike reality where skylight still
        illuminates them — samplers in `spectralforge.terrain` reject them by default.

    c_correction — C-correction (Teillet et al. 1982)
        generation:  ρ_T = ρ_H · (cos i + c_λ) / (cos θ_s + c_λ)
        correction:  ρ_H = ρ_T · (cos θ_s + c_λ) / (cos i + c_λ)
        Adds isotropic diffuse skylight: c_λ ≈ E_d(λ) / E_b(λ), the diffuse-to-direct
        irradiance ratio, so the factor depends on wavelength (spectral shape changes) and
        self-shadowed pixels keep the diffuse part c_λ / (cos θ_s + c_λ) instead of turning
        black — sample geometry with `min_cos_i=-1.0` to include them. Still no cast
        shadows, no sky-view reduction in valleys, no terrain-reflected light.
        c_λ comes from: a regression on a real scene (`fit_c_coefficients`), the clear-sky
        parameterisation in `spectralforge.atmosphere`, or an explicit array.

    minnaert — Minnaert model (Minnaert 1941; Smith et al. 1980)
        L = L_n · cos^k(i) · cos^(k−1)(e),  e — angle between the view direction and the
        terrain normal (e = s for a nadir view). Relative to a horizontal surface:
        generation:  ρ_T = ρ_H · (cos i / cos θ_s)^k_λ · (cos e / cos θ_v)^(k_λ−1)
        correction:  ρ_H = ρ_T / [same factor]
        With `exitance=False` the cos e term is dropped (the common simplified form).
        k = 1 is a Lambertian surface (reduces to the cosine model), k < 1 a surface less
        sensitive to illumination (rough, non-Lambertian, or skylight-lit). Only a per-band
        k_λ changes spectral shape — a single k only rescales brightness, like the cosine
        model with a different dependence on geometry. No diffuse floor: self-shadowed
        pixels still become black. k_λ comes from a regression on a real scene
        (`fit_minnaert_k`), an explicit array, or a random draw of one k per sample.

    physical — irradiance split into direct, sky-diffuse and terrain-reflected components
        (Sandmeier & Itten 1997; Richter 1998, ATCOR-3), written per unit direct irradiance
        with c_λ = E_d/E_b:
        generation:  ρ_T = ρ_H · { [cos⁺i·(1−S) + c_λ·D] / (cos θ_s + c_λ) + ρ_adj·(1 − V_d) }
            cos⁺i = max(cos i, 0);  S — cast shadow (0/1);  V_d — sky-view factor;
            D = V_d (isotropic sky)  or  D = A_λ·cos⁺i·(1−S)/cos θ_s + (1−A_λ)·V_d  (Hay),
            A_λ = direct-beam transmittance (circumsolar share of the sky light);
            ρ_adj — reflectance of the surrounding terrain (default: the spectrum itself).
        Reduces to the C model for V_d = 1, S = 0, A = 0 and no terrain term, and to the
        identity on flat open terrain. V_d and S come from the DEM (`TerrainHorizons`);
        without them V_d = (1 + cos s)/2 (unobstructed slope) and S = 0. Still Lambertian.

Output is NOT clipped to [0, 1]: sun-facing slopes genuinely produce apparent reflectance
above the flat-terrain value (possibly > 1) in uncorrected products. Physical plausibility
checks belong to the B8 guardrail, not to this operator.
"""

from dataclasses import dataclass, field

import numpy as np

from spectralforge.atmosphere import diffuse_to_direct_ratio, direct_transmittance
from spectralforge.terrain import (
    AngleSpec,
    GeometrySampler,
    TerrainGeometry,
    cos_incidence,
    draw_uniform,
)

OPERATOR_CODE = "B1"


def cosine_illumination(
    reflectance: np.ndarray, cos_i: np.ndarray | float, solar_zenith_deg: np.ndarray | float
) -> np.ndarray:
    """Apparent reflectance on sloped terrain under the Lambertian cosine model.

    `reflectance` has bands on the last axis, shape (..., n_bands); `cos_i` and
    `solar_zenith_deg` broadcast against its leading axes (one value per spectrum).
    """
    factor = cosine_factor(cos_i, solar_zenith_deg)
    return np.asarray(reflectance, dtype=float) * factor[..., np.newaxis]


def cosine_correction(
    apparent_reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    min_cos_i: float = 0.05,
) -> np.ndarray:
    """Inverse of `cosine_illumination` — the classical cosine topographic correction.

    Pixels with cos i < `min_cos_i` are returned as NaN: the correction diverges there
    (the well-known over-correction of weakly illuminated slopes).
    """
    cos_i = np.asarray(cos_i, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        corrected = (
            np.asarray(apparent_reflectance, dtype=float)
            / cosine_factor(cos_i, solar_zenith_deg)[..., np.newaxis]
        )
    return np.where((cos_i >= min_cos_i)[..., np.newaxis], corrected, np.nan)


def cosine_factor(cos_i: np.ndarray | float, solar_zenith_deg: np.ndarray | float) -> np.ndarray:
    """Illumination factor ρ_T / ρ_H = max(cos i, 0) / cos θ_s."""
    return np.clip(np.asarray(cos_i, dtype=float), 0.0, None) / _cos_solar_zenith(solar_zenith_deg)


def c_factor(
    cos_i: np.ndarray | float, solar_zenith_deg: np.ndarray | float, c: np.ndarray
) -> np.ndarray:
    """Illumination factor ρ_T / ρ_H = (max(cos i, 0) + c_λ) / (cos θ_s + c_λ).

    `cos_i` and `solar_zenith_deg` have one value per spectrum, shape (...); `c` is either
    one coefficient per band (n_bands,) or one set per spectrum (..., n_bands).
    Result has shape (..., n_bands).
    """
    direct = np.clip(np.asarray(cos_i, dtype=float), 0.0, None)[..., np.newaxis]
    cos_sz = _cos_solar_zenith(solar_zenith_deg)[..., np.newaxis]
    c = np.asarray(c, dtype=float)
    if np.any(c < 0):
        raise ValueError("c must be non-negative (it is a diffuse/direct irradiance ratio)")
    return (direct + c) / (cos_sz + c)


def c_illumination(
    reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    c: np.ndarray,
) -> np.ndarray:
    """Apparent reflectance on sloped terrain under the C-correction model (see `c_factor`)."""
    return np.asarray(reflectance, dtype=float) * c_factor(cos_i, solar_zenith_deg, c)


def c_correction(
    apparent_reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    c: np.ndarray,
) -> np.ndarray:
    """Inverse of `c_illumination` — the classical C topographic correction.

    Bands where the factor is 0 (cos i ≤ 0 with c_λ = 0) cannot be inverted and are NaN.
    """
    factor = c_factor(cos_i, solar_zenith_deg, c)
    with np.errstate(divide="ignore", invalid="ignore"):
        corrected = np.asarray(apparent_reflectance, dtype=float) / factor
    return np.where(factor > 0, corrected, np.nan)


def fit_c_coefficients(reflectance: np.ndarray, cos_i: np.ndarray) -> np.ndarray:
    """Per-band C coefficients from a regression ρ_T = m_λ · cos i + b_λ;  c_λ = b_λ / m_λ.

    `reflectance` is (n_pixels, n_bands) from a real, uncorrected scene and `cos_i`
    (n_pixels,) from its DEM. Use pixels of ONE homogeneous surface type spanning a wide
    range of cos i — otherwise land-cover differences leak into the fit. Bands with a
    non-positive slope (no measurable illumination dependence) get NaN.
    """
    slope, intercept = _fit_per_band(cos_i, reflectance)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(slope > 0, intercept / slope, np.nan)


def minnaert_factor(
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    k: np.ndarray | float,
    cos_e: np.ndarray | float | None = None,
    view_zenith_deg: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Illumination factor ρ_T / ρ_H = (max(cos i, 0)/cos θ_s)^k · (cos e/cos θ_v)^(k−1).

    `cos_i`, `solar_zenith_deg` (and `cos_e`, `view_zenith_deg`) have one value per
    spectrum, shape (...); `k` is a scalar, one value per band (n_bands,), or per spectrum
    (..., 1) / (..., n_bands). `cos_e=None` drops the exitance term. Pixels the sensor
    cannot see (cos e ≤ 0) are NaN. Result has shape (..., n_bands) or (..., 1).
    """
    k = np.asarray(k, dtype=float)
    if np.any(k <= 0):
        raise ValueError("Minnaert k must be positive")
    direct = np.clip(np.asarray(cos_i, dtype=float), 0.0, None)[..., np.newaxis]
    cos_sz = _cos_solar_zenith(solar_zenith_deg)[..., np.newaxis]
    factor = (direct / cos_sz) ** k
    if cos_e is None:
        return factor
    cos_e = np.asarray(cos_e, dtype=float)[..., np.newaxis]
    cos_v = np.cos(np.radians(np.asarray(view_zenith_deg, dtype=float)))[..., np.newaxis]
    with np.errstate(divide="ignore", invalid="ignore"):
        exitance = (cos_e / cos_v) ** (k - 1)
    return np.where(cos_e > 0, factor * exitance, np.nan)


def minnaert_illumination(
    reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    k: np.ndarray | float,
    cos_e: np.ndarray | float | None = None,
    view_zenith_deg: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Apparent reflectance on sloped terrain under the Minnaert model (see `minnaert_factor`)."""
    factor = minnaert_factor(cos_i, solar_zenith_deg, k, cos_e, view_zenith_deg)
    return np.asarray(reflectance, dtype=float) * factor


def minnaert_correction(
    apparent_reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    k: np.ndarray | float,
    cos_e: np.ndarray | float | None = None,
    view_zenith_deg: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Inverse of `minnaert_illumination` — the classical Minnaert topographic correction.

    Self-shadowed (factor 0) and invisible (cos e ≤ 0) pixels are NaN.
    """
    factor = minnaert_factor(cos_i, solar_zenith_deg, k, cos_e, view_zenith_deg)
    with np.errstate(divide="ignore", invalid="ignore"):
        corrected = np.asarray(apparent_reflectance, dtype=float) / factor
    return np.where(factor > 0, corrected, np.nan)


def fit_minnaert_k(
    reflectance: np.ndarray, cos_i: np.ndarray, cos_e: np.ndarray | None = None
) -> np.ndarray:
    """Per-band Minnaert constants from a log-log regression on a real, uncorrected scene.

    With exitance:     ln(ρ_T · cos e) = ln ρ_n + k_λ · ln(cos i · cos e)
    Without (cos_e=None):        ln ρ_T = ln ρ_n + k_λ · ln cos i
    `reflectance` is (n_pixels, n_bands), `cos_i`/`cos_e` are (n_pixels,). Pixels with
    cos i ≤ 0, cos e ≤ 0 or any non-positive reflectance are skipped. As for
    `fit_c_coefficients`: use ONE homogeneous surface type over a wide range of cos i.
    """
    cos_i = np.asarray(cos_i, dtype=float)
    y = np.asarray(reflectance, dtype=float)
    cos_e = np.ones_like(cos_i) if cos_e is None else np.asarray(cos_e, dtype=float)
    if y.ndim != 2 or y.shape[0] != cos_i.size or cos_e.shape != cos_i.shape:
        raise ValueError(
            "reflectance must be (n_pixels, n_bands) with cos_i/cos_e of shape (n_pixels,)"
        )
    valid = (cos_i > 0) & (cos_e > 0) & np.all(y > 0, axis=1)
    if valid.sum() < 2:
        raise ValueError("fewer than 2 usable pixels (cos i > 0, cos e > 0, reflectance > 0)")
    x = np.log(cos_i[valid] * cos_e[valid])
    slope, _ = _fit_per_band(x, np.log(y[valid] * cos_e[valid, np.newaxis]))
    return slope


def physical_factor(
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    c: np.ndarray,
    sky_view: np.ndarray | float,
    cast_shadow: np.ndarray | float = 0.0,
    anisotropy: np.ndarray | None = None,
    terrain_reflectance: np.ndarray | float | None = None,
) -> np.ndarray:
    """Illumination factor ρ_T / ρ_H of the physical model (see module docstring).

    Per-spectrum inputs, shape (...): `cos_i`, `solar_zenith_deg`, `sky_view` (V_d, 0–1),
    `cast_shadow` (S, 0–1). Per-band inputs, shape (n_bands,) or (..., n_bands): `c`
    (E_d/E_b), `anisotropy` (A, Hay; None = isotropic sky) and `terrain_reflectance`
    (ρ_adj; None = no terrain-reflected light). Result has shape (..., n_bands).
    """
    c = np.asarray(c, dtype=float)
    if np.any(c < 0):
        raise ValueError("c must be non-negative (it is a diffuse/direct irradiance ratio)")
    sky_view = np.asarray(sky_view, dtype=float)[..., np.newaxis]
    shadow = np.asarray(cast_shadow, dtype=float)[..., np.newaxis]
    if np.any((sky_view < 0) | (sky_view > 1)) or np.any((shadow < 0) | (shadow > 1)):
        raise ValueError("sky_view and cast_shadow must lie in [0, 1]")
    cos_sz = _cos_solar_zenith(solar_zenith_deg)[..., np.newaxis]
    direct = np.clip(np.asarray(cos_i, dtype=float), 0.0, None)[..., np.newaxis] * (1 - shadow)
    if anisotropy is None:
        diffuse = sky_view
    else:
        a = np.asarray(anisotropy, dtype=float)
        diffuse = a * direct / cos_sz + (1 - a) * sky_view
    factor = (direct + c * diffuse) / (cos_sz + c)
    if terrain_reflectance is not None:
        factor = factor + np.asarray(terrain_reflectance, dtype=float) * (1 - sky_view)
    return factor


def physical_illumination(
    reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    c: np.ndarray,
    sky_view: np.ndarray | float,
    cast_shadow: np.ndarray | float = 0.0,
    anisotropy: np.ndarray | None = None,
    terrain_reflectance: np.ndarray | float | str | None = "self",
) -> np.ndarray:
    """Apparent reflectance on sloped terrain under the physical model.

    `terrain_reflectance="self"` assumes surroundings of the same material (homogeneous
    outcrop); pass a background spectrum instead, or None to drop the terrain term.
    """
    reflectance = np.asarray(reflectance, dtype=float)
    rho_adj = reflectance if _is_self(terrain_reflectance) else terrain_reflectance
    factor = physical_factor(cos_i, solar_zenith_deg, c, sky_view, cast_shadow, anisotropy, rho_adj)
    return reflectance * factor


def physical_correction(
    apparent_reflectance: np.ndarray,
    cos_i: np.ndarray | float,
    solar_zenith_deg: np.ndarray | float,
    c: np.ndarray,
    sky_view: np.ndarray | float,
    cast_shadow: np.ndarray | float = 0.0,
    anisotropy: np.ndarray | None = None,
    terrain_reflectance: np.ndarray | float | str | None = "self",
) -> np.ndarray:
    """Inverse of `physical_illumination`.

    With `terrain_reflectance="self"` the model is quadratic in ρ_H
    (ρ_T = a·ρ_H + (1 − V_d)·ρ_H²) and is solved for its positive root.
    """
    rho_t = np.asarray(apparent_reflectance, dtype=float)
    if not _is_self(terrain_reflectance):
        factor = physical_factor(
            cos_i, solar_zenith_deg, c, sky_view, cast_shadow, anisotropy, terrain_reflectance
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(factor > 0, rho_t / factor, np.nan)
    a = physical_factor(cos_i, solar_zenith_deg, c, sky_view, cast_shadow, anisotropy, None)
    b = 1 - np.asarray(sky_view, dtype=float)[..., np.newaxis]
    with np.errstate(divide="ignore", invalid="ignore"):
        quadratic = (np.sqrt(a**2 + 4 * b * rho_t) - a) / (2 * b)
        linear = rho_t / a
    return np.where(b > 0, quadratic, linear)


def _is_self(terrain_reflectance: object) -> bool:
    return isinstance(terrain_reflectance, str) and terrain_reflectance == "self"


def _fit_per_band(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares y = slope · x + intercept, one fit per column of `y` (n, n_bands)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 2 or y.shape[0] != x.size:
        raise ValueError("reflectance must be (n_pixels, n_bands) with cos_i of shape (n_pixels,)")
    x_dev = x - x.mean()
    var_x = np.sum(x_dev**2)
    if var_x == 0:
        raise ValueError("cos_i has no spread — cannot fit an illumination dependence")
    slope = x_dev @ (y - y.mean(axis=0)) / var_x
    return slope, y.mean(axis=0) - slope * x.mean()


def _cos_solar_zenith(solar_zenith_deg: np.ndarray | float) -> np.ndarray:
    cos_sz = np.cos(np.radians(np.asarray(solar_zenith_deg, dtype=float)))
    if np.any(cos_sz <= 0):
        raise ValueError("solar_zenith_deg must be < 90° (Sun above the horizon)")
    return cos_sz


@dataclass(frozen=True)
class SyntheticBatch:
    """Generated spectra plus everything needed to record their provenance.

    Row k of `reflectance` was generated from `spectra[source_index[k]]` with geometry
    row k — maps onto spectralforge.operator_runs / generated_spectra / generation_inputs.
    """

    reflectance: np.ndarray  # (n_samples, n_bands)
    source_index: np.ndarray  # (n_samples,)
    geometry: TerrainGeometry
    illumination_factor: np.ndarray  # (n_samples,), or (n_samples, n_bands) if λ-dependent
    model: str
    operator_code: str = OPERATOR_CODE
    extra: dict[str, np.ndarray | float | str] = field(default_factory=dict)
    """Model-specific parameters: per-sample arrays (n_samples,) or run-wide scalars."""

    def parameters(self, k: int) -> dict[str, float | str]:
        """Parameters of sample k, in the shape stored in operator_runs.parameters (JSONB)."""
        g = self.geometry
        factor = self.illumination_factor[k]
        params: dict[str, float | str] = {
            "model": self.model,
            "solar_zenith_deg": float(g.solar_zenith_deg[k]),
            "solar_azimuth_deg": float(g.solar_azimuth_deg[k]),
            "slope_deg": float(g.slope_deg[k]),
            "aspect_deg": float(g.aspect_deg[k]),
            "cos_i": float(g.cos_i[k]),
        }
        if np.ndim(factor) == 0:
            params["illumination_factor"] = float(factor)
        else:
            params["illumination_factor_min"] = float(np.min(factor))
            params["illumination_factor_max"] = float(np.max(factor))
        for key, value in self.extra.items():
            params[key] = float(value[k]) if isinstance(value, np.ndarray) else value
        return params


def generate_cosine(
    spectra: np.ndarray,
    n_per_spectrum: int,
    sampler: GeometrySampler,
    rng: np.random.Generator,
) -> SyntheticBatch:
    """Generate `n_per_spectrum` cosine-model variants of every input spectrum.

    `spectra` is (n_spectra, n_bands) or a single (n_bands,) spectrum. `sampler` draws the
    Sun/terrain geometry, e.g. `functools.partial(sample_geometry_from_dem, slope_deg=...,
    aspect_deg=..., solar_zenith_deg=..., solar_azimuth_deg=...)`.
    """
    spectra = np.atleast_2d(np.asarray(spectra, dtype=float))
    source_index = np.repeat(np.arange(len(spectra)), n_per_spectrum)
    geometry = sampler(rng, len(source_index))
    factor = cosine_factor(geometry.cos_i, geometry.solar_zenith_deg)
    return SyntheticBatch(
        reflectance=spectra[source_index] * factor[:, np.newaxis],
        source_index=source_index,
        geometry=geometry,
        illumination_factor=factor,
        model="cosine",
    )


def generate_c_correction(
    spectra: np.ndarray,
    n_per_spectrum: int,
    sampler: GeometrySampler,
    rng: np.random.Generator,
    wavelengths_nm: np.ndarray | None = None,
    c: np.ndarray | None = None,
    aot_550: AngleSpec = (0.05, 0.3),
    angstrom: AngleSpec = 1.3,
    elevation_km: float = 0.0,
) -> SyntheticBatch:
    """Generate `n_per_spectrum` C-correction variants of every input spectrum.

    Two sources of c_λ:
      * `c` given — fixed coefficients (n_bands,), e.g. from `fit_c_coefficients` on the
        target scene (conditioning on a known scene);
      * `c` omitted — per-sample c_λ = E_d/E_b from the clear-sky parameterisation, with the
        aerosol load drawn from `aot_550` / `angstrom` (fixed value or (low, high) range):
        randomising the atmosphere for users who do not know theirs. Needs `wavelengths_nm`.
    Default AOT/Ångström ranges are illustrative clear-sky values, not tied to any region.
    """
    spectra = np.atleast_2d(np.asarray(spectra, dtype=float))
    source_index = np.repeat(np.arange(len(spectra)), n_per_spectrum)
    n = len(source_index)
    geometry = sampler(rng, n)

    extra: dict[str, np.ndarray | float | str]
    if c is not None:
        coefficients = np.broadcast_to(np.asarray(c, dtype=float), (n, spectra.shape[1]))
        extra = {"c_source": "fixed"}
    else:
        if wavelengths_nm is None:
            raise ValueError("wavelengths_nm is required when c is not given")
        aot = draw_uniform(rng, aot_550, n)
        alpha = draw_uniform(rng, angstrom, n)
        coefficients = diffuse_to_direct_ratio(
            wavelengths_nm, geometry.solar_zenith_deg, aot, alpha, elevation_km
        )
        extra = {
            "c_source": "clear_sky",
            "aot_550": aot,
            "angstrom": alpha,
            "elevation_km": float(elevation_km),
        }

    factor = c_factor(geometry.cos_i, geometry.solar_zenith_deg, coefficients)
    return SyntheticBatch(
        reflectance=spectra[source_index] * factor,
        source_index=source_index,
        geometry=geometry,
        illumination_factor=factor,
        model="c_correction",
        extra=extra,
    )


def generate_minnaert(
    spectra: np.ndarray,
    n_per_spectrum: int,
    sampler: GeometrySampler,
    rng: np.random.Generator,
    k: AngleSpec | np.ndarray = (0.6, 1.0),
    exitance: bool = True,
    view_zenith_deg: float = 0.0,
    view_azimuth_deg: float = 0.0,
) -> SyntheticBatch:
    """Generate `n_per_spectrum` Minnaert-model variants of every input spectrum.

    `k` is one of:
      * an array (n_bands,) — fixed per-band constants, e.g. from `fit_minnaert_k` on the
        target scene; the only option that changes spectral shape;
      * a float or a (low, high) range — one wavelength-independent k per sample, drawn
        uniformly (roughness randomisation). The default range is illustrative only.
    The view direction (`view_zenith_deg`, `view_azimuth_deg`; default nadir) enters the
    exitance term cos e; tilted sensors such as EnMAP need the actual angles.
    """
    spectra = np.atleast_2d(np.asarray(spectra, dtype=float))
    source_index = np.repeat(np.arange(len(spectra)), n_per_spectrum)
    n = len(source_index)
    geometry = sampler(rng, n)

    extra: dict[str, np.ndarray | float | str] = {
        "exitance": "yes" if exitance else "no",
        "view_zenith_deg": float(view_zenith_deg),
        "view_azimuth_deg": float(view_azimuth_deg),
    }
    if isinstance(k, np.ndarray) and k.ndim == 1 and k.size == spectra.shape[1]:
        k_per_sample = k
        extra["k_source"] = "fixed"
    else:
        drawn = draw_uniform(rng, k, n)
        k_per_sample = drawn[:, np.newaxis]
        extra |= {"k_source": "random", "k": drawn}

    cos_e = (
        cos_incidence(view_zenith_deg, view_azimuth_deg, geometry.slope_deg, geometry.aspect_deg)
        if exitance
        else None
    )
    factor = minnaert_factor(
        geometry.cos_i, geometry.solar_zenith_deg, k_per_sample, cos_e, view_zenith_deg
    )
    if factor.shape[-1] == 1:
        factor = factor[:, 0]
        reflectance = spectra[source_index] * factor[:, np.newaxis]
    else:
        reflectance = spectra[source_index] * factor
    return SyntheticBatch(
        reflectance=reflectance,
        source_index=source_index,
        geometry=geometry,
        illumination_factor=factor,
        model="minnaert",
        extra=extra,
    )


def generate_physical(
    spectra: np.ndarray,
    n_per_spectrum: int,
    sampler: GeometrySampler,
    rng: np.random.Generator,
    wavelengths_nm: np.ndarray,
    aot_550: AngleSpec = (0.05, 0.3),
    angstrom: AngleSpec = 1.3,
    elevation_km: float = 0.0,
    diffuse: str = "hay",
    terrain_reflectance: np.ndarray | str | None = "self",
) -> SyntheticBatch:
    """Generate `n_per_spectrum` physical-model variants of every input spectrum.

    The atmosphere (c_λ = E_d/E_b and, for `diffuse="hay"`, the anisotropy A_λ) comes from
    the clear-sky parameterisation with AOT/Ångström drawn from the given values/ranges.
    Sky-view factor and cast shadow come from the sampled geometry — use
    `sample_geometry_from_dem(..., horizons=TerrainHorizons.from_dem(...))` to get them from
    a real DEM; other samplers fall back to an unobstructed slope without cast shadows.
    Sample with `min_cos_i=-1.0` to keep self-shadowed slopes (lit by sky and terrain).
    """
    if diffuse not in ("isotropic", "hay"):
        raise ValueError("diffuse must be 'isotropic' or 'hay'")
    spectra = np.atleast_2d(np.asarray(spectra, dtype=float))
    source_index = np.repeat(np.arange(len(spectra)), n_per_spectrum)
    n = len(source_index)
    geometry = sampler(rng, n)
    aot = draw_uniform(rng, aot_550, n)
    alpha = draw_uniform(rng, angstrom, n)
    sz = geometry.solar_zenith_deg
    c = diffuse_to_direct_ratio(wavelengths_nm, sz, aot, alpha, elevation_km)
    anisotropy = (
        direct_transmittance(wavelengths_nm, sz, aot, alpha, elevation_km)
        if diffuse == "hay"
        else None
    )
    sources = spectra[source_index]
    rho_adj = sources if _is_self(terrain_reflectance) else terrain_reflectance
    sky_view = geometry.sky_view_or_default
    shadow = geometry.cast_shadow_or_default
    factor = physical_factor(geometry.cos_i, sz, c, sky_view, shadow, anisotropy, rho_adj)

    if _is_self(terrain_reflectance):
        terrain_source = "self"
    else:
        terrain_source = "none" if terrain_reflectance is None else "background"
    return SyntheticBatch(
        reflectance=sources * factor,
        source_index=source_index,
        geometry=geometry,
        illumination_factor=factor,
        model="physical",
        extra={
            "diffuse": diffuse,
            "terrain_reflectance": terrain_source,
            "sky_view": sky_view,
            "cast_shadow": shadow,
            "aot_550": aot,
            "angstrom": alpha,
            "elevation_km": float(elevation_km),
        },
    )
