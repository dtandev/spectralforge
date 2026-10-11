"""Simple clear-sky atmosphere parameterisations shared by the operators.

Not a radiative-transfer code: a single-scattering approximation good enough to give the
diffuse/direct irradiance ratio its correct order of magnitude and wavelength trend
(large in the blue, small in the SWIR). Gas absorption (H2O, O2, CO2 bands), multiple
scattering and ground–atmosphere coupling are ignored.
TODO: verify this against 6S/libRadtran runs before using the absolute values in a paper.
"""

import numpy as np

RAYLEIGH_SCALE_HEIGHT_KM = 8.0


def rayleigh_optical_depth(wavelengths_nm: np.ndarray, elevation_km: float = 0.0) -> np.ndarray:
    """Rayleigh optical depth (Hansen & Travis 1974), scaled by surface pressure."""
    lam = np.asarray(wavelengths_nm, dtype=float) / 1000.0
    tau_sea_level = 0.008569 * lam**-4 * (1 + 0.0113 * lam**-2 + 0.00013 * lam**-4)
    return tau_sea_level * np.exp(-elevation_km / RAYLEIGH_SCALE_HEIGHT_KM)


def aerosol_optical_depth(
    wavelengths_nm: np.ndarray, aot_550: np.ndarray | float, angstrom: np.ndarray | float
) -> np.ndarray:
    """Ångström law τ_a(λ) = AOT_550 · (λ / 550 nm)^(−α); broadcasts to (..., n_bands)."""
    aot = np.asarray(aot_550, dtype=float)[..., np.newaxis]
    alpha = np.asarray(angstrom, dtype=float)[..., np.newaxis]
    return aot * (np.asarray(wavelengths_nm, dtype=float) / 550.0) ** (-alpha)


def diffuse_to_direct_ratio(
    wavelengths_nm: np.ndarray,
    solar_zenith_deg: np.ndarray | float,
    aot_550: np.ndarray | float = 0.1,
    angstrom: np.ndarray | float = 1.3,
    elevation_km: float = 0.0,
    aerosol_forward_fraction: float = 0.8,
) -> np.ndarray:
    """E_d / E_b — the physical meaning of the C-correction coefficient c_λ.

    E_b is the direct-beam irradiance on a surface normal to the beam, E_d the diffuse sky
    irradiance on a horizontal surface. Single-scattering estimate: half of the Rayleigh-
    scattered and `aerosol_forward_fraction` of the aerosol-scattered beam reach the ground.
    `solar_zenith_deg`, `aot_550` and `angstrom` broadcast together (one value per sample);
    the result has shape (..., n_bands).
    """
    mu = np.cos(np.radians(np.asarray(solar_zenith_deg, dtype=float)))[..., np.newaxis]
    if np.any(mu <= 0):
        raise ValueError("solar_zenith_deg must be < 90° (Sun above the horizon)")
    tau_r = rayleigh_optical_depth(wavelengths_nm, elevation_km)
    tau_a = aerosol_optical_depth(wavelengths_nm, aot_550, angstrom)
    diffuse = mu * (
        0.5 * (1 - np.exp(-tau_r / mu)) + aerosol_forward_fraction * (1 - np.exp(-tau_a / mu))
    )
    direct = np.exp(-(tau_r + tau_a) / mu)
    return diffuse / direct


def direct_transmittance(
    wavelengths_nm: np.ndarray,
    solar_zenith_deg: np.ndarray | float,
    aot_550: np.ndarray | float = 0.1,
    angstrom: np.ndarray | float = 1.3,
    elevation_km: float = 0.0,
) -> np.ndarray:
    """Direct-beam transmittance T_b = exp(−(τ_R + τ_a) / cos θ_s), shape (..., n_bands).

    Used as Hay's anisotropy index (the circumsolar share of the diffuse sky light).
    """
    mu = np.cos(np.radians(np.asarray(solar_zenith_deg, dtype=float)))[..., np.newaxis]
    if np.any(mu <= 0):
        raise ValueError("solar_zenith_deg must be < 90° (Sun above the horizon)")
    tau = rayleigh_optical_depth(wavelengths_nm, elevation_km) + aerosol_optical_depth(
        wavelengths_nm, aot_550, angstrom
    )
    return np.exp(-tau / mu)
