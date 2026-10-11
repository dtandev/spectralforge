"""B0 overview figure for El Abra: DEM, illumination at two times, and the solar path.

Needs the DEM from: python scripts/download_dem.py examples/AOI_el_abra.geojson

Usage:
    python examples/b0_el_abra_figure.py [dem_path] [output_png]
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from rasterio.warp import transform_geom
from shapely.geometry import mapping, shape

from spectralforge.dem import load_aoi, load_region
from spectralforge.region import sun_for_aoi, terrain_illumination
from spectralforge.solar import time_range

ROOT = Path(__file__).resolve().parent.parent
DEM_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/dem/AOI_el_abra_glo30.tif"
OUT_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs/figures/b0_el_abra.png"

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list(
    "blue", ["#cde2fb", "#86b6ef", "#3987e5", "#184f95", "#0d366b"]
)
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK_2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
    }
)

aoi = load_aoi(ROOT / "examples/AOI_el_abra.geojson")
region = load_region(DEM_PATH, aoi)
rows, cols = region.elevation.shape
x0, y0 = region.transform.c, region.transform.f
extent_km = (0, cols * region.pixel_size / 1000, 0, rows * region.pixel_size / 1000)
outline = shape(transform_geom("EPSG:4326", region.crs, mapping(aoi))).exterior.coords.xy
outline_km = (
    (np.array(outline[0]) - x0) / 1000,
    (np.array(outline[1]) - (y0 - rows * region.pixel_size)) / 1000,
)

times = ["2026-06-21T12:00Z", "2026-06-21T16:00Z"]
sun = sun_for_aoi(aoi, times, elevation_km=region.elevation_km)
illum = [
    terrain_illumination(region, sun.apparent_zenith_deg[k], sun.azimuth_deg[k]) for k in range(2)
]

fig, axes = plt.subplots(2, 3, figsize=(15, 9.5))
ax = axes[0, 0]
slope, aspect = region.slope_aspect
hillshade = np.clip(
    np.cos(np.radians(45)) * np.cos(np.radians(slope))
    + np.sin(np.radians(45)) * np.sin(np.radians(slope)) * np.cos(np.radians(315 - aspect)),
    0,
    1,
)
ax.imshow(hillshade, cmap="Greys_r", extent=extent_km, alpha=0.9)
im = ax.imshow(region.elevation, cmap=SEQ, extent=extent_km, alpha=0.55)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="m n.p.m.")
cb.outline.set_visible(False)
ax.set_title("a) Copernicus GLO-30, UTM 19S, bufor 10 km", loc="left", fontsize=10.5)

for col, (k, label) in enumerate(((0, "b"), (1, "c")), start=1):
    il = illum[k]
    ax = axes[0, col]
    im = ax.imshow(il.cos_i, cmap=SEQ, extent=extent_km, vmin=-0.3, vmax=1.0)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="cos i")
    cb.outline.set_visible(False)
    s = il.summary()
    ax.set_title(
        f"{label}) cos i, {times[k][11:16]}Z (Słońce {90 - il.solar_zenith_deg:.0f}°, az. {il.solar_azimuth_deg:.0f}°)",
        loc="left",
        fontsize=10.5,
    )
    ax.text(
        0.02,
        0.03,
        f"w AOI: cień własny {s['self_shadow_fraction']:.0%}, rzucany {s['cast_shadow_fraction']:.0%}",
        transform=ax.transAxes,
        fontsize=8.5,
        color=INK,
        bbox=dict(facecolor=SURFACE, edgecolor="none", alpha=0.85),
    )

il = illum[0]
ax = axes[1, 0]
classes = np.where(il.self_shadow, 1, np.where(il.cast_shadow, 2, 0)).astype(float)
ax.imshow(
    classes,
    cmap=ListedColormap(["#fcfcfb", "#86b6ef", "#184f95"]),
    extent=extent_km,
    vmin=0,
    vmax=2,
)
ax.set_title("d) cienie 12:00Z: jasne = własny, ciemne = rzucany", loc="left", fontsize=10.5)

ax = axes[1, 1]
im = ax.imshow(illum[1].incidence_deg, cmap=SEQ.reversed(), extent=extent_km, vmin=0, vmax=90)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="i [°]")
cb.outline.set_visible(False)
ax.set_title("e) kąt padania i, 16:00Z", loc="left", fontsize=10.5)

for ax in (*axes[0], axes[1, 0], axes[1, 1]):
    ax.plot(*outline_km, color="#eb6834", lw=1.6)
    ax.set_xlabel("km")

ax = axes[1, 2]
for day, color in (("2026-06-21", "#2a78d6"), ("2026-12-21", "#eb6834")):
    path = sun_for_aoi(
        aoi, time_range(f"{day}T09:00Z", f"{day}T24:00Z".replace("T24", "T23"), "10min")
    )
    az, el = path.azimuth_deg.copy(), path.elevation_deg.copy()
    el[~path.above_horizon] = np.nan
    az[1:][np.abs(np.diff(az)) > 180] = np.nan  # break the line where the path crosses north
    ax.plot(az, el, color=color, lw=2, label=day)
    hours = time_range(f"{day}T10:00Z", f"{day}T23:00Z", "1h")
    hp = sun_for_aoi(aoi, hours)
    hu = hp.above_horizon
    ax.plot(hp.azimuth_deg[hu], hp.elevation_deg[hu], "o", color=color, ms=4)
    for t, az, el in zip(hours[hu], hp.azimuth_deg[hu], hp.elevation_deg[hu], strict=True):
        if str(t)[11:13] in ("12", "16", "20"):
            ax.annotate(
                f"{str(t)[11:13]}Z",
                (az, el),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
                color=INK_2,
            )
ax.set_xlim(0, 360)
ax.set_xticks([0, 90, 180, 270, 360], ["N", "E", "S", "W", "N"])
ax.set_ylim(0, 90)
ax.set_xlabel("azymut Słońca")
ax.set_ylabel("wysokość Słońca [°]")
ax.grid(color=GRID, lw=0.6)
ax.legend(frameon=False, labelcolor=INK_2)
ax.set_title("f) ścieżka Słońca w przesilenia (punkty co 1 h)", loc="left", fontsize=10.5)

fig.suptitle(
    f"B0 — El Abra (AOI pomarańczowy): DEM i oświetlenie terenu 21.06.2026; mediana wysokości AOI {region.elevation_km * 1000:.0f} m",
    x=0.04,
    ha="left",
    fontsize=12.5,
)
fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, dpi=130, bbox_inches="tight")
print(f"Saved {OUT_PATH}")
