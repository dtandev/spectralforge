"""Compare the B1 cosine and C-correction models on one Alunite USGS spectrum.

The same 10 Sun/terrain geometries are applied in both models; c_λ comes from the clear-sky
parameterisation (spectralforge.atmosphere) at El Abra-like elevation.

Usage:
    python examples/b1_c_correction_alunite.py [csv_path] [output_png]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize

from spectralforge.atmosphere import diffuse_to_direct_ratio
from spectralforge.io import load_splib_csv
from spectralforge.operators.illumination import c_illumination, cosine_illumination
from spectralforge.terrain import sample_geometry_uniform

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/signatures/pcd_minerals 2.csv"
OUT_PATH = (
    Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/output/b1_c_correction_alunite.png"
)
N_VARIANTS = 10
SEED = 7
AOT_550, ANGSTROM, ELEVATION_KM = 0.15, 1.3, 4.0  # illustrative clear sky, high-altitude site

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

library = load_splib_csv(CSV_PATH).select("Alunite")
source = library.reflectance[0]
wl = library.wavelengths_nm

# min_cos_i=-1 keeps self-shadowed slopes: black in the cosine model, lit by sky in the C model.
geometry = sample_geometry_uniform(
    np.random.default_rng(SEED),
    N_VARIANTS,
    solar_zenith_deg=(25.0, 55.0),
    slope_deg=(0.0, 45.0),
    min_cos_i=-1.0,
)
cos_i, sz = geometry.cos_i, geometry.solar_zenith_deg
c = diffuse_to_direct_ratio(wl, sz, AOT_550, ANGSTROM, ELEVATION_KM)  # (n_variants, n_bands)
variants = {
    "model cosinusowy": cosine_illumination(
        np.broadcast_to(source, (N_VARIANTS, wl.size)), cos_i, sz
    ),
    "C-correction": c_illumination(source, cos_i, sz, c),
}

cmap = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)
norm = Normalize(max(cos_i.min(), 0.0), cos_i.max())
order = np.argsort(cos_i)

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK_2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
fig, axes = plt.subplots(
    2,
    2,
    figsize=(14, 8.5),
    sharex=True,
    sharey="row",
    gridspec_kw={"height_ratios": [3, 1.6], "hspace": 0.1, "wspace": 0.06},
)
fig.patch.set_facecolor(SURFACE)

for col, (title, spectra) in enumerate(variants.items()):
    ax, ax_ratio = axes[0, col], axes[1, col]
    for k in order:
        color = cmap(norm(max(cos_i[k], 0.0)))
        ax.plot(wl, spectra[k], color=color, lw=1.4)
        ax_ratio.plot(wl, spectra[k] / source, color=color, lw=1.4)
    ax.plot(wl, source, color=INK, lw=2.4, label=f"oryginał USGS: {library.names[0]}")
    ax_ratio.axhline(1.0, color=INK, lw=2.0)
    ax.axhline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_title(title, loc="left", color=INK, fontsize=12)
    for a in (ax, ax_ratio):
        a.set_facecolor(SURFACE)
        a.grid(color=GRID, lw=0.6)
        a.set_axisbelow(True)
    ax_ratio.set_xlabel("długość fali [nm]")

shadowed = int(np.sum(cos_i <= 0))
axes[0, 0].text(
    420,
    0.03,
    f"{shadowed} z {N_VARIANTS} stoków samozacienionych (cos i ≤ 0) → widmo zerowe",
    color=INK_2,
    fontsize=8.5,
)
axes[0, 1].text(
    1000,
    0.17,
    "stok samozacieniony: oświetla go tylko niebo →\n"
    "widmo „niebieskie”, cechy SWIR prawie wygaszone",
    color=INK_2,
    fontsize=8.5,
)
axes[1, 1].text(
    0.3,
    0.45,
    "c_λ = E_d/E_b maleje od niebieskiego do SWIR →\n"
    "stosunek zależy od λ (zmienia się kształt widma)",
    transform=axes[1, 1].transAxes,
    va="top",
    color=INK_2,
    fontsize=8.5,
)
axes[1, 0].text(
    0.02,
    0.94,
    "stosunek stały → tylko zmiana jasności",
    transform=axes[1, 0].transAxes,
    va="top",
    color=INK_2,
    fontsize=8.5,
)
axes[0, 0].set_ylabel("odbicie pozorne ρ_T")
axes[1, 0].set_ylabel("ρ_T / ρ_H")
axes[0, 0].set_ylim(0, None)
axes[0, 0].set_xlim(wl[0], wl[-1])
axes[0, 0].legend(loc="upper right", frameon=False, labelcolor=INK_2, fontsize=9)

fig.suptitle(
    f"B1 — model cosinusowy vs C-correction: Alunite, te same {N_VARIANTS} geometrii",
    x=0.125,
    y=0.985,
    ha="left",
    color=INK,
    fontsize=14,
)
fig.text(
    0.125,
    0.935,
    f"θs ~ U(25°, 55°), nachylenie ~ U(0°, 45°), ekspozycja i azymut ~ U(0°, 360°)   ·   "
    f"c_λ: czyste niebo, AOT₅₅₀ = {AOT_550}, α = {ANGSTROM}, wysokość {ELEVATION_KM:.0f} km "
    f"(c₄₅₀ ≈ {np.interp(450, wl, c.mean(0)):.2f}, c₂₂₀₀ ≈ {np.interp(2200, wl, c.mean(0)):.3f})",
    color=INK_2,
    fontsize=9,
)

cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, fraction=0.02, pad=0.03)
cbar.set_label("cos i  (≤ 0 = stok samozacieniony)", color=INK_2)
cbar.outline.set_visible(False)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved {OUT_PATH}")
print("cos i:", np.round(np.sort(cos_i), 2))
