"""Plot one Alunite USGS spectrum and 10 synthetic variants from the B1 cosine model.

Usage:
    python examples/b1_cosine_alunite.py [csv_path] [output_png]
"""

import sys
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize

from spectralforge.io import load_splib_csv
from spectralforge.operators.illumination import generate_cosine
from spectralforge.terrain import sample_geometry_uniform

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/signatures/pcd_minerals 2.csv"
OUT_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/output/b1_cosine_alunite.png"
N_VARIANTS = 10
SEED = 7

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

library = load_splib_csv(CSV_PATH).select("Alunite")
source = library.reflectance[0]
wl = library.wavelengths_nm

sampler = partial(sample_geometry_uniform, solar_zenith_deg=(25.0, 55.0), slope_deg=(0.0, 35.0))
batch = generate_cosine(source, N_VARIANTS, sampler, np.random.default_rng(SEED))
order = np.argsort(batch.illumination_factor)
factor = batch.illumination_factor[order]

cmap = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)
norm = Normalize(factor.min(), factor.max())

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
fig, (ax, ax_ratio) = plt.subplots(
    2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1.3], "hspace": 0.08}
)
fig.patch.set_facecolor(SURFACE)

for k in order:
    color = cmap(norm(batch.illumination_factor[k]))
    ax.plot(wl, batch.reflectance[k], color=color, lw=1.4)
    ax_ratio.plot(wl, batch.reflectance[k] / source, color=color, lw=1.4)
ax.plot(wl, source, color=INK, lw=2.4, label=f"oryginał USGS: {library.names[0]}")
ax_ratio.axhline(1.0, color=INK, lw=2.0)

ax.axhline(1.0, color=MUTED, lw=1, ls=(0, (4, 3)))
ax.text(2490, 1.005, "ρ = 1 (próg B8)", ha="right", va="bottom", color=MUTED, fontsize=9)

# Direct labels for the extremes only, in the empty band above the darkest variant;
# the colorbar carries the rest.
for k, where, y in ((order[-1], "najjaśniejszy", 0.36), (order[0], "najciemniejszy", 0.30)):
    p = batch.parameters(int(k))
    ax.text(
        420,
        y,
        f"{where}: ×{p['illumination_factor']:.2f}   (θs = {p['solar_zenith_deg']:.0f}°, "
        f"nachylenie = {p['slope_deg']:.0f}°, ekspozycja = {p['aspect_deg']:.0f}°, "
        f"azymut Słońca = {p['solar_azimuth_deg']:.0f}°)",
        fontsize=8.5,
        color=INK_2,
    )

for a in (ax, ax_ratio):
    a.set_facecolor(SURFACE)
    a.grid(color=GRID, lw=0.6)
    a.set_axisbelow(True)
ax.set_ylabel("odbicie pozorne ρ_T")
ax.set_ylim(0, None)
ax.legend(loc="lower left", frameon=False, labelcolor=INK_2)
ax.set_title(
    f"B1 — model cosinusowy: Alunite i {N_VARIANTS} wariantów oświetlenia/topografii",
    loc="left",
    color=INK,
    fontsize=13,
    pad=26,
)
ax.text(
    0,
    1.02,
    "ρ_T = ρ_H · cos i / cos θs   ·   θs ~ U(25°, 55°), nachylenie ~ U(0°, 35°), "
    "ekspozycja i azymut Słońca ~ U(0°, 360°)",
    transform=ax.transAxes,
    color=INK_2,
    fontsize=9,
)
ax_ratio.set_ylabel("ρ_T / ρ_H")
ax_ratio.set_xlabel("długość fali [nm]")
ax_ratio.text(
    0.01,
    0.42,
    "stosunek stały w całym zakresie → model zmienia jasność, nie kształt widma",
    transform=ax_ratio.transAxes,
    va="top",
    color=INK_2,
    fontsize=9,
)
ax_ratio.set_xlim(wl[0], wl[-1])
ax_ratio.set_ylim(0.1, 1.4)

cbar = fig.colorbar(
    plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=(ax, ax_ratio), fraction=0.03, pad=0.02
)
cbar.set_label("współczynnik oświetlenia cos i / cos θs", color=INK_2)
cbar.outline.set_visible(False)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, dpi=160, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved {OUT_PATH}")
