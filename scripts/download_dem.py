"""Download Copernicus DEM GLO-30 (30 m) for an AOI, reprojected to UTM with a buffer (B0).

Usage:
    uv run python scripts/download_dem.py AOI.geojson
    uv run python scripts/download_dem.py AOI.geojson --out data/dem/el_abra.tif --buffer-km 10

Reads only the needed parts of the public COG tiles on AWS (no account needed) and writes a
float32 GeoTIFF (NaN = no data). The buffer matters: terrain outside the AOI still casts
shadows and blocks the sky inside it. Prints the numbers B1 needs (e.g. elevation_km).
"""

import argparse
from pathlib import Path

import numpy as np

from spectralforge.dem import download_copernicus_dem, load_aoi, load_region


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("aoi", type=Path, help="GeoJSON with the area of interest (lon/lat)")
    parser.add_argument(
        "--out", type=Path, help="output GeoTIFF (default: data/dem/<aoi>_glo30.tif)"
    )
    parser.add_argument("--buffer-km", type=float, default=10.0, help="buffer around the AOI [km]")
    parser.add_argument("--resolution", type=float, default=30.0, help="output pixel size [m]")
    parser.add_argument("--crs", help="output CRS, e.g. EPSG:32719 (default: UTM zone of the AOI)")
    parser.add_argument(
        "--overwrite", action="store_true", help="re-download even if the file exists"
    )
    args = parser.parse_args()

    out = args.out or Path("data/dem") / f"{args.aoi.stem}_glo30.tif"
    aoi = load_aoi(args.aoi)
    existed = out.exists() and not args.overwrite
    download_copernicus_dem(
        aoi,
        out,
        buffer_m=args.buffer_km * 1000,
        resolution_m=args.resolution,
        crs=args.crs,
        overwrite=args.overwrite,
    )
    region = load_region(out, aoi)
    inside = region.elevation[region.aoi_mask]
    slope, _ = region.slope_aspect
    print(f"{'Reused' if existed else 'Wrote'} {out}")
    print(
        f"  CRS {region.crs.to_string()}, {region.elevation.shape[1]} × {region.elevation.shape[0]} px of {region.pixel_size:g} m"
    )
    print(
        f"  AOI: {region.aoi_mask.sum()} px, elevation {np.nanmin(inside):.0f}–{np.nanmax(inside):.0f} m"
    )
    print(
        f"  AOI slope: median {np.nanmedian(slope[region.aoi_mask]):.1f}°, p95 {np.nanpercentile(slope[region.aoi_mask], 95):.1f}°"
    )
    print(f"  no-data pixels: {np.isnan(region.elevation).mean():.1%}")
    print(f"  → B1: elevation_km = {region.elevation_km:.3f}")


if __name__ == "__main__":
    main()
