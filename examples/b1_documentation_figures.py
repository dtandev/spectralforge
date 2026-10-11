"""Generate all figures of docs/B1_oswietlenie_topografia.md into docs/figures/.

Usage:
    python examples/b1_documentation_figures.py [csv_path] [output_dir]
"""

import sys
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from spectralforge.atmosphere import diffuse_to_direct_ratio, direct_transmittance
from spectralforge.io import load_splib_csv
from spectralforge.operators.illumination import (
    c_factor,
    c_illumination,
    cosine_factor,
    cosine_illumination,
    generate_c_correction,
    generate_cosine,
    generate_minnaert,
    generate_physical,
    minnaert_factor,
    minnaert_illumination,
    physical_factor,
    physical_illumination,
)
from spectralforge.terrain import (
    TerrainHorizons,
    cos_incidence,
    sample_geometry_from_dem,
    sample_geometry_uniform,
)

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/signatures/pcd_minerals 2.csv"
OUT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs/figures"

# Illustrative clear-sky atmosphere at a high-altitude site (El Abra ~4 km a.s.l.).
AOT, ALPHA, ELEV = 0.15, 1.3, 4.0

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)
# Categorical slots in fixed order, plus a line style as secondary encoding.
MODELS = {
    "cosinusowy": ("#2a78d6", "-"),
    "C-correction": ("#eb6834", "--"),
    "Minnaert (k = 0,8)": ("#1baf7a", "-."),
    "fizyczny, niebo izotropowe": ("#eda100", (0, (1, 1.5))),
    "fizyczny, Hay": ("#e87ba4", (0, (5, 1.5, 1, 1.5))),
}

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "legend.labelcolor": INK_2,
    }
)

library = load_splib_csv(CSV_PATH)
alunite_lib = library.select("Alunite")
alunite = alunite_lib.reflectance[0]
hematite = library.select("Hematite").reflectance[0]
wl = library.wavelengths_nm
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save(fig: plt.Figure, name: str) -> None:
    path = OUT_DIR / name
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def atmosphere(sz: float, wavelengths: np.ndarray = wl, aot: float = AOT):
    c = diffuse_to_direct_ratio(wavelengths, sz, aot, ALPHA, ELEV)
    a = direct_transmittance(wavelengths, sz, aot, ALPHA, ELEV)
    return c, a


def all_models(
    rho: np.ndarray,
    sz: float,
    slope: float,
    aspect: float,
    saz: float,
    sky_view: float,
    shadow: float,
) -> dict[str, np.ndarray]:
    """One spectrum under every model for one geometry (shadow/sky view only in physical)."""
    cos_i = np.array([cos_incidence(sz, saz, slope, aspect)])
    cos_e = np.array([np.cos(np.radians(slope))])
    c, a = atmosphere(sz)
    return {
        "cosinusowy": cosine_illumination(rho, cos_i, sz)[0],
        "C-correction": c_illumination(rho, cos_i, sz, c)[0],
        "Minnaert (k = 0,8)": minnaert_illumination(rho, cos_i, sz, 0.8, cos_e)[0],
        "fizyczny, niebo izotropowe": physical_illumination(rho, cos_i, sz, c, sky_view, shadow)[0],
        "fizyczny, Hay": physical_illumination(rho, cos_i, sz, c, sky_view, shadow, a)[0],
    }


# --- Figure 1: all models in four illumination situations --------------------------------
def figure_situations() -> None:
    sz, saz = 40.0, 180.0
    situations = [
        ("a) stok zwrócony do Słońca", dict(slope=30, aspect=180, sky_view=0.93, shadow=0)),
        ("b) stok słabo oświetlony", dict(slope=30, aspect=0, sky_view=0.93, shadow=0)),
        (
            "c) cień rzucany przez sąsiednie zbocze",
            dict(slope=10, aspect=180, sky_view=0.75, shadow=1),
        ),
        ("d) stok samozacieniony", dict(slope=60, aspect=0, sky_view=0.75, shadow=0)),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True, sharey=True)
    for ax, (title, g) in zip(axes.flat, situations, strict=True):
        cos_i = cos_incidence(sz, saz, g["slope"], g["aspect"])
        for name, spectrum in all_models(alunite, sz, saz=saz, **g).items():
            color, ls = MODELS[name]
            ax.plot(wl, spectrum, color=color, ls=ls, lw=1.8, label=name)
        ax.plot(wl, alunite, color=INK, lw=2.2, label="oryginał (teren płaski)")
        ax.set_title(title, loc="left", fontsize=11)
        ax.text(
            0.98,
            0.97,
            f"nachylenie {g['slope']}°, ekspozycja {g['aspect']}°\n"
            f"cos i = {cos_i:.2f},  V_d = {g['sky_view']},  S = {g['shadow']}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8.5,
            color=INK_2,
        )
    axes[0, 0].legend(loc="lower left", fontsize=8.5)
    for ax in axes[1]:
        ax.set_xlabel("długość fali [nm]")
    for ax in axes[:, 0]:
        ax.set_ylabel("odbicie pozorne ρ_T")
    axes[0, 0].set_xlim(wl[0], wl[-1])
    axes[0, 0].set_ylim(0, 1.35)
    fig.suptitle(
        "Rys. 1. Alunite pod pięcioma modelami B1 w czterech sytuacjach oświetlenia "
        f"(θs = {sz:.0f}°, Słońce z południa; AOT₅₅₀ = {AOT}, 4 km n.p.m.)",
        x=0.07,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig1_sytuacje.png")


# --- Figure 2: illumination factor vs cos i at two wavelengths ---------------------------
def figure_factor_vs_cos_i() -> None:
    sz = 40.0
    cos_i = np.linspace(-0.3, 1.0, 261)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, lam in zip(axes, (500.0, 2200.0), strict=True):
        band = np.array([lam])
        rho = np.interp(lam, wl, alunite)
        c, a = atmosphere(sz, band)
        curves = {
            "cosinusowy": cosine_factor(cos_i, sz),
            "C-correction": c_factor(cos_i, sz, c)[:, 0],
            "Minnaert (k = 0,8)": minnaert_factor(cos_i, sz, 0.8)[:, 0],
            "fizyczny, niebo izotropowe": physical_factor(cos_i, sz, c, 0.9, 0, None, rho)[:, 0],
            "fizyczny, Hay": physical_factor(cos_i, sz, c, 0.9, 0, a, rho)[:, 0],
        }
        for name, y in curves.items():
            color, ls = MODELS[name]
            ax.plot(cos_i, y, color=color, ls=ls, lw=1.8, label=name)
        ax.axvline(np.cos(np.radians(sz)), color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.axhline(1, color=MUTED, lw=0.8)
        ax.text(
            np.cos(np.radians(sz)) + 0.01,
            0.05,
            "teren płaski\n(cos i = cos θs)",
            fontsize=8,
            color=INK_2,
        )
        ax.text(-0.29, 0.6, "samo-\nzacienienie", fontsize=8, color=INK_2)
        ax.set_title(f"λ = {lam:.0f} nm   (c = {c[0]:.3f})", loc="left", fontsize=11)
        ax.set_xlabel("cos i")
    axes[0].set_ylabel("współczynnik ρ_T / ρ_H")
    axes[0].legend(loc="upper left", fontsize=8.5, bbox_to_anchor=(0.1, 1.0))
    fig.suptitle(
        "Rys. 2. Współczynnik oświetlenia w funkcji cos i (θs = 40°, V_d = 0,9 w modelu fizycznym)",
        x=0.07,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig2_wspolczynnik_vs_cos_i.png")


# --- Figure 3: atmosphere parameters → c_λ -----------------------------------------------
def figure_atmosphere() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
    panels = [
        (
            "a) aerozol: AOT₅₅₀",
            [0.05, 0.15, 0.3, 0.5],
            lambda v: diffuse_to_direct_ratio(wl, 40, v, ALPHA, ELEV),
        ),
        (
            "b) zenit Słońca θs",
            [20, 40, 55, 70],
            lambda v: diffuse_to_direct_ratio(wl, v, AOT, ALPHA, ELEV),
        ),
        (
            "c) wysokość terenu [km]",
            [0, 2, 4],
            lambda v: diffuse_to_direct_ratio(wl, 40, AOT, ALPHA, v),
        ),
    ]
    for ax, (title, values, fn) in zip(axes, panels, strict=True):
        for j, v in enumerate(values):
            color = SEQ(0.35 + 0.65 * j / max(len(values) - 1, 1))
            ax.plot(wl, fn(v), color=color, lw=1.8, label=f"{v}")
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel("długość fali [nm]")
        ax.set_yscale("log")
        ax.legend(fontsize=8.5, loc="upper right")
    axes[0].set_ylabel("c_λ = E_d / E_b  (skala log)")
    axes[0].set_xlim(wl[0], wl[-1])
    fig.suptitle(
        "Rys. 3. Wpływ parametrów atmosfery na c_λ (pozostałe: θs = 40°, "
        f"AOT₅₅₀ = {AOT}, α = {ALPHA}, 4 km)",
        x=0.07,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig3_atmosfera_c.png")


# --- Figure 4: Minnaert k and the exitance term ------------------------------------------
def figure_minnaert() -> None:
    sz = 40.0
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    cos_i = np.linspace(0.0, 1.0, 201)
    ks = [0.4, 0.6, 0.8, 1.0]
    for j, k in enumerate(ks):
        axes[0].plot(
            cos_i,
            minnaert_factor(cos_i, sz, k)[:, 0],
            color=SEQ(0.35 + 0.65 * j / 3),
            lw=1.8,
            label=f"k = {k}" + (" (= cosinusowy)" if k == 1 else ""),
        )
    axes[0].axvline(np.cos(np.radians(sz)), color=MUTED, lw=1, ls=(0, (4, 3)))
    axes[0].set_xlabel("cos i")
    axes[0].set_ylabel("współczynnik ρ_T / ρ_H")
    axes[0].set_title("a) stała Minnaerta k (bez członu cos e)", loc="left", fontsize=11)
    axes[0].legend(fontsize=8.5)

    slope = np.linspace(0, 60, 121)
    for aspect, label_side in ((180.0, "stok do Słońca"), (0.0, "stok od Słońca")):
        ci = cos_incidence(sz, 180.0, slope, aspect)
        ce = np.cos(np.radians(slope))
        with np.errstate(invalid="ignore"):
            with_e = minnaert_factor(ci, sz, 0.7, ce)[:, 0]
            without = minnaert_factor(ci, sz, 0.7)[:, 0]
        ls = "-" if aspect == 180 else "--"
        axes[1].plot(
            slope,
            with_e,
            color=MODELS["Minnaert (k = 0,8)"][0],
            ls=ls,
            lw=1.8,
            label=f"{label_side}, z cos e",
        )
        axes[1].plot(slope, without, color=MUTED, ls=ls, lw=1.4, label=f"{label_side}, bez cos e")
    axes[1].set_xlabel("nachylenie [°]  (sensor w nadirze, e = nachylenie)")
    axes[1].set_title("b) człon cos e przy k = 0,7", loc="left", fontsize=11)
    axes[1].legend(fontsize=8.5)
    fig.suptitle(
        "Rys. 4. Model Minnaerta: wpływ k i członu obserwacji (θs = 40°)",
        x=0.07,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig4_minnaert.png")


# --- Figure 5: physical model — effect of each term --------------------------------------
def figure_physical_terms() -> None:
    sz = 40.0
    c, a = atmosphere(sz)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    ax = axes[0, 0]
    for j, vd in enumerate([1.0, 0.85, 0.7, 0.55]):
        ax.plot(
            wl,
            physical_illumination(alunite, np.array([0.8]), sz, c, vd, 1.0, a)[0],
            color=SEQ(1 - 0.6 * j / 3),
            lw=1.8,
            label=f"V_d = {vd}",
        )
    ax.set_title(
        "a) sky-view V_d w cieniu rzuconym (S = 1, otoczenie = alunit)", loc="left", fontsize=11
    )

    ax = axes[0, 1]
    for label, rho_adj, color in (
        ("bez światła od terenu", None, MUTED),
        ("otoczenie = alunit (ten sam materiał)", "self", MODELS["fizyczny, Hay"][0]),
        ("otoczenie = hematyt (ciemne tło)", hematite, "#6250d6"),
    ):
        ax.plot(
            wl,
            physical_illumination(alunite, np.array([0.8]), sz, c, 0.6, 1.0, a, rho_adj)[0],
            color=color,
            lw=1.8,
            label=label,
        )
    ax.set_title("b) odbicie terenu ρ_adj (S = 1, V_d = 0,6)", loc="left", fontsize=11)

    ax = axes[1, 0]
    for shadow, situation, cos_i in ((0.0, "stok w słońcu", 0.98), (1.0, "cień rzucany", 0.98)):
        for aniso, ls, sky in ((None, "-", "izotropowe"), (a, "--", "Hay")):
            color = MODELS["fizyczny, niebo izotropowe" if aniso is None else "fizyczny, Hay"][0]
            ax.plot(
                wl,
                physical_illumination(alunite, np.array([cos_i]), sz, c, 0.9, shadow, aniso)[0],
                color=color,
                ls=ls,
                lw=1.8,
                label=f"{situation}, niebo {sky}",
            )
    ax.set_title("c) niebo izotropowe vs Hay (V_d = 0,9)", loc="left", fontsize=11)

    ax = axes[1, 1]
    for j, aot in enumerate([0.05, 0.15, 0.3, 0.5]):
        c_a, a_a = atmosphere(sz, aot=aot)
        ax.plot(
            wl,
            physical_illumination(alunite, np.array([0.3]), sz, c_a, 0.93, 0.0, a_a)[0],
            color=SEQ(0.35 + 0.65 * j / 3),
            lw=1.8,
            label=f"AOT₅₅₀ = {aot}",
        )
    ax.set_title("d) aerozol na stoku słabo oświetlonym (cos i = 0,3)", loc="left", fontsize=11)

    for ax in axes.flat:
        ax.plot(wl, alunite, color=INK, lw=1.2, alpha=0.5, label="oryginał")
        ax.set_ylim(0, None)
    for ax in (axes[0, 0], axes[0, 1], axes[1, 1]):
        ax.set_ylim(0, 1.4)
        ax.legend(fontsize=8, loc="upper right")
    axes[1, 0].set_ylim(0, 1.75)
    axes[1, 0].legend(fontsize=8, loc="upper right", ncol=2)
    for ax in axes[1]:
        ax.set_xlabel("długość fali [nm]")
    for ax in axes[:, 0]:
        ax.set_ylabel("odbicie pozorne ρ_T")
    axes[0, 0].set_xlim(wl[0], wl[-1])
    fig.suptitle(
        "Rys. 5. Model fizyczny: wpływ poszczególnych składników (Alunite, θs = 40°)",
        x=0.07,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig5_fizyczny_skladniki.png")


# --- Figure 6: maps on a synthetic DEM ---------------------------------------------------
def synthetic_dem(size: int = 140) -> np.ndarray:
    y, x = np.mgrid[0:size, 0:size].astype(float)
    return (
        650 * np.exp(-((x - 45) ** 2 + (y - 55) ** 2) / (2 * 22**2))
        + 480 * np.exp(-((x - 100) ** 2 + (y - 90) ** 2) / (2 * 18**2))
        + 180 * np.exp(-((y - 0.6 * x - 30) ** 2) / (2 * 7**2))
    )


def figure_dem_maps(dem: np.ndarray, horizons: TerrainHorizons, pixel: float) -> None:
    sz, saz = 60.0, 45.0
    cos_i = cos_incidence(sz, saz, horizons.slope_deg, horizons.aspect_deg)
    sky = horizons.sky_view()
    idx = np.arange(dem.size)
    shadow = horizons.cast_shadow(np.full(dem.size, sz), np.full(dem.size, saz), idx).reshape(
        dem.shape
    )
    bands = np.array([500.0, 2200.0])
    c, a = atmosphere(sz, bands)
    rho = np.interp(bands, wl, alunite)
    factor = physical_factor(cos_i, sz, c, sky, shadow, a, rho)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8.8))
    extent = (0, dem.shape[1] * pixel / 1000, 0, dem.shape[0] * pixel / 1000)
    panels = [
        ("a) DEM [m]", dem, "Greys", None),
        ("b) cos i", cos_i, SEQ, (-0.2, 1.0)),
        ("c) sky-view V_d", sky, SEQ, (0.6, 1.0)),
        (
            "d) cień: rzucany (1), samozacienienie (0,5)",
            np.where(shadow > 0, 1.0, np.where(cos_i <= 0, 0.5, 0.0)),
            "Greys",
            (0, 1),
        ),
        ("e) współczynnik modelu fizycznego, 500 nm", factor[..., 0], SEQ, (0, 1.6)),
        ("f) współczynnik modelu fizycznego, 2200 nm", factor[..., 1], SEQ, (0, 1.6)),
    ]
    for ax, (title, data, cmap, lim) in zip(axes.flat, panels, strict=True):
        im = ax.imshow(
            data,
            cmap=cmap,
            extent=extent,
            vmin=None if lim is None else lim[0],
            vmax=None if lim is None else lim[1],
        )
        ax.set_title(title, loc="left", fontsize=10.5)
        ax.grid(False)
        ax.set_xlabel("km")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.outline.set_visible(False)
    axes[0, 0].annotate(
        "",
        xy=(0.85, 0.85),
        xytext=(0.72, 0.72),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color="#eb6834", lw=2),
    )
    axes[0, 0].text(
        0.55,
        0.9,
        "kierunek do Słońca",
        transform=axes[0, 0].transAxes,
        color="#eb6834",
        fontsize=8.5,
    )
    fig.suptitle(
        f"Rys. 6. Syntetyczny DEM (piksel {pixel:.0f} m): geometria i współczynnik modelu fizycznego "
        f"(θs = {sz:.0f}°, azymut Słońca {saz:.0f}°, niebo Hay, otoczenie = alunit)",
        x=0.05,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    save(fig, "b1_fig6_mapy_dem.png")


# --- Figure 7: diversity of generated sets -----------------------------------------------
def spectral_angle_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    cos = np.sum(a * b, axis=-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def figure_diversity(horizons: TerrainHorizons) -> None:
    n = 2000
    rng = np.random.default_rng(11)
    uniform = partial(sample_geometry_uniform, solar_zenith_deg=(25.0, 55.0), slope_deg=(0.0, 35.0))
    dem_sampler = partial(
        sample_geometry_from_dem,
        slope_deg=horizons.slope_deg,
        aspect_deg=horizons.aspect_deg,
        solar_zenith_deg=(25.0, 55.0),
        solar_azimuth_deg=(0.0, 360.0),
        min_cos_i=-1.0,
        horizons=horizons,
    )
    batches = {
        "cosinusowy": generate_cosine(alunite, n, uniform, rng),
        "C-correction": generate_c_correction(alunite, n, uniform, rng, wl, elevation_km=ELEV),
        "Minnaert (k ~ U(0,6; 1))": generate_minnaert(alunite, n, uniform, rng, k=(0.6, 1.0)),
        "fizyczny, izotropowe": generate_physical(
            alunite, n, uniform, rng, wl, elevation_km=ELEV, diffuse="isotropic"
        ),
        "fizyczny, Hay": generate_physical(alunite, n, uniform, rng, wl, elevation_km=ELEV),
        "fizyczny, Hay + DEM\n(cienie, V_d, samozacien.)": generate_physical(
            alunite, n, dem_sampler, rng, wl, elevation_km=ELEV
        ),
    }
    colors = [MODELS[m][0] for m in MODELS] + ["#008300"]
    names = list(batches)
    brightness = [b.reflectance.mean(axis=1) / alunite.mean() for b in batches.values()]
    sam = [spectral_angle_deg(b.reflectance, alunite) for b in batches.values()]
    above_one = [100 * np.mean(b.reflectance.max(axis=1) > 1) for b in batches.values()]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, data, title, xlabel in (
        (axes[0], brightness, "a) jasność: średni ρ_T / średni ρ_H", "współczynnik jasności"),
        (axes[1], sam, "b) zmiana kształtu: kąt spektralny SAM do oryginału", "SAM [°]"),
    ):
        parts = ax.boxplot(
            data,
            vert=False,
            widths=0.55,
            patch_artist=True,
            showfliers=False,
            medianprops=dict(color=INK, lw=1.5),
            whiskerprops=dict(color=MUTED),
            capprops=dict(color=MUTED),
        )
        for patch, color in zip(parts["boxes"], colors, strict=True):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
            patch.set_edgecolor(SURFACE)
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel(xlabel)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(1, len(names) + 1), names)
    axes[0].invert_yaxis()
    for j, pct in enumerate(above_one, start=1):
        axes[0].text(
            1.02,
            j,
            f"{pct:.0f}% widm z ρ > 1",
            transform=axes[0].get_yaxis_transform(),
            va="center",
            fontsize=8,
            color=INK_2,
        )
    fig.suptitle(
        f"Rys. 7. Zróżnicowanie {n} wariantów Alunite na model (θs ~ U(25°, 55°); bez DEM: nachylenie "
        "~ U(0°, 35°), bez samozacienienia; pudełko = kwartyle, wąsy = 1,5 IQR)",
        x=0.03,
        ha="left",
        fontsize=11.5,
    )
    fig.tight_layout()
    save(fig, "b1_fig7_zroznicowanie.png")
    for name, b_, s_, p_ in zip(names, brightness, sam, above_one, strict=True):
        print(
            f"{name.replace(chr(10), ' '):45s} jasność p5–p95 {np.percentile(b_, 5):.2f}–{np.percentile(b_, 95):.2f}"
            f"  SAM median {np.median(s_):.2f}° p95 {np.percentile(s_, 95):.2f}°  ρ>1: {p_:.0f}%"
        )


if __name__ == "__main__":
    pixel = 30.0
    dem = synthetic_dem()
    horizons = TerrainHorizons.from_dem(dem, pixel, n_directions=32)
    figure_situations()
    figure_factor_vs_cos_i()
    figure_atmosphere()
    figure_minnaert()
    figure_physical_terms()
    figure_dem_maps(dem, horizons, pixel)
    figure_diversity(horizons)
