"""Compare the B1 cosine and Minnaert models on one Alunite USGS spectrum.

The same 10 Sun/terrain geometries are applied in both models; Minnaert uses one random,
wavelength-independent k per sample and the exitance term for a nadir-looking sensor.

Usage:
    python examples/b1_minnaert_alunite.py [csv_path] [output_png]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize

from spectralforge.io import load_splib_csv
from spectralforge.operators.illumination import cosine_illumination, minnaert_illumination
from spectralforge.terrain import sample_geometry_uniform

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/signatures/pcd_minerals 2.csv"
OUT_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/output/b1_minnaert_alunite.png"
N_VARIANTS = 10
SEED = 7
K_RANGE = (0.6, 1.0)  # illustrative roughness range, not fitted to any scene

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

library = load_splib_csv(CSV_PATH).select("Alunite")
source = library.reflectance[0]
wl = library.wavelengths_nm

rng = np.random.default_rng(SEED)
geometry = sample_geometry_uniform(
    rng, N_VARIANTS, solar_zenith_deg=(25.0, 55.0), slope_deg=(0.0, 45.0)
)
k = rng.uniform(*K_RANGE, N_VARIANTS)
cos_i, sz = geometry.cos_i, geometry.solar_zenith_deg
cos_e = np.cos(np.radians(geometry.slope_deg))  # nadir view: e = slope
stack = np.broadcast_to(source, (N_VARIANTS, wl.size))
variants = {
    "model cosinusowy (k = 1, lambertowski)": cosine_illumination(stack, cos_i, sz),
    f"Minnaert (k ~ U{K_RANGE}, z członem cos e)": minnaert_illumination(
        stack, cos_i, sz, k[:, None], cos_e
    ),
}

cmap = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)
norm = Normalize(cos_i.min(), cos_i.max())
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
    gridspec_kw={"height_ratios": [3, 1.6], "hspace": 0.16, "wspace": 0.06},
)
fig.patch.set_facecolor(SURFACE)

for col, (title, spectra) in enumerate(variants.items()):
    ax, ax_ratio = axes[0, col], axes[1, col]
    for j in order:
        color = cmap(norm(cos_i[j]))
        ax.plot(wl, spectra[j], color=color, lw=1.4)
        ax_ratio.plot(wl, spectra[j] / source, color=color, lw=1.4)
    ax.plot(wl, source, color=INK, lw=2.4, label=f"oryginał USGS: {library.names[0]}")
    ax_ratio.axhline(1.0, color=INK, lw=2.0)
    ax.axhline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_title(title, loc="left", color=INK, fontsize=12)
    for a in (ax, ax_ratio):
        a.set_facecolor(SURFACE)
        a.grid(color=GRID, lw=0.6)
        a.set_axisbelow(True)
    ax_ratio.set_xlabel("długość fali [nm]")
    ratios = spectra[:, 0] / source[0]
    ax.text(
        420,
        0.04,
        f"zakres współczynnika: ×{ratios.min():.2f} – ×{ratios.max():.2f}",
        color=INK_2,
        fontsize=9,
    )

ratio_notes = (
    "stosunek stały → tylko zmiana jasności",
    f"k = {k.min():.2f}–{k.max():.2f} < 1 → współczynnik bliżej 1, mniejszy kontrast stoków; "
    "nadal płasko",
)
for ax_ratio, note in zip(axes[1], ratio_notes, strict=True):
    ax_ratio.set_title(note, loc="left", color=INK_2, fontsize=9, pad=4)

axes[0, 0].set_ylabel("odbicie pozorne ρ_T")
axes[1, 0].set_ylabel("ρ_T / ρ_H")
axes[0, 0].set_ylim(0, None)
axes[0, 0].set_xlim(wl[0], wl[-1])
axes[0, 0].legend(loc="upper right", frameon=False, labelcolor=INK_2, fontsize=9)

fig.suptitle(
    f"B1 — model cosinusowy vs Minnaert: Alunite, te same {N_VARIANTS} geometrii",
    x=0.125,
    y=0.985,
    ha="left",
    color=INK,
    fontsize=14,
)
fig.text(
    0.125,
    0.935,
    "ρ_T = ρ_H · (cos i / cos θs)^k · (cos e)^(k−1),  e = nachylenie (sensor w nadirze)   ·   "
    "θs ~ U(25°, 55°), nachylenie ~ U(0°, 45°), ekspozycja i azymut ~ U(0°, 360°)",
    color=INK_2,
    fontsize=9,
)

cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, fraction=0.02, pad=0.04)
cbar.set_label("cos i", color=INK_2)
cbar.outline.set_visible(False)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved {OUT_PATH}")
