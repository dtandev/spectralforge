"""Solar parameters for an AOI at given dates/times, optionally with terrain illumination (B0).

Usage:
    uv run python scripts/sun_parameters.py AOI.geojson --time 2026-06-21T14:30Z
    uv run python scripts/sun_parameters.py AOI.geojson --time 2026-06-21T10:30-04:00 --time 2026-12-21T10:30-03:00
    uv run python scripts/sun_parameters.py AOI.geojson --start 2026-06-21T10:00Z --end 2026-06-21T23:00Z \\
        --step 1h --dem data/dem/AOI_glo30.tif --out sun.csv --maps data/output/sun_maps

Times are UTC unless they carry an offset (ISO 8601). Per time it reports solar zenith
(geometric and apparent), elevation, azimuth (clockwise from north, towards the Sun),
declination, hour angle, equation of time, local solar time and Earth–Sun distance. With
`--dem` it adds, over the AOI: cos i statistics, median local incidence angle and the
fractions of self-shadowed, cast-shadowed and directly lit terrain; `--maps` writes per-time
GeoTIFFs (cos i, incidence angle, shadow class: 0 lit, 1 self-shadow, 2 cast shadow).
Ends with the ranges to feed into B1.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import rasterio

from spectralforge.dem import load_aoi, load_region
from spectralforge.region import sun_for_aoi, terrain_illumination
from spectralforge.solar import time_range, to_utc

SUN_COLUMNS = [
    "time_utc",
    "local_solar_time",
    "solar_zenith_deg",
    "apparent_zenith_deg",
    "solar_elevation_deg",
    "solar_azimuth_deg",
    "declination_deg",
    "hour_angle_deg",
    "equation_of_time_min",
    "earth_sun_distance_au",
    "above_horizon",
]


def azimuth_span(azimuth_deg: np.ndarray) -> tuple[float, float]:
    """Smallest arc (start, end), clockwise, containing all azimuths; may cross north."""
    az = np.sort(np.mod(azimuth_deg, 360.0))
    gaps = np.diff(np.append(az, az[0] + 360.0))
    widest = int(np.argmax(gaps))
    return float(az[(widest + 1) % az.size]), float(az[widest])


def format_solar_time(hours: float) -> str:
    minutes = int(round(hours * 60)) % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def write_maps(path: Path, region, illum) -> None:
    shadow_class = np.where(illum.self_shadow, 1.0, np.where(illum.cast_shadow, 2.0, 0.0))
    shadow_class[~np.isfinite(illum.cos_i)] = np.nan
    bands = {
        "cos_i": illum.cos_i,
        "incidence_deg": illum.incidence_deg,
        "shadow_class": shadow_class,
    }
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": len(bands),
        "width": region.elevation.shape[1],
        "height": region.elevation.shape[0],
        "crs": region.crs,
        "transform": region.transform,
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        for i, (name, data) in enumerate(bands.items(), start=1):
            dst.write(data.astype("float32"), i)
            dst.set_band_description(i, name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("aoi", type=Path, help="GeoJSON with the area of interest (lon/lat)")
    parser.add_argument("--time", action="append", default=[], help="ISO time; repeat for several")
    parser.add_argument("--start", help="start of a time series (ISO)")
    parser.add_argument("--end", help="end of a time series (ISO, inclusive)")
    parser.add_argument("--step", default="1h", help="series step: 30s, 15min, 1h, 1d (default 1h)")
    parser.add_argument(
        "--dem", type=Path, help="DEM from download_dem.py → adds terrain statistics"
    )
    parser.add_argument(
        "--min-elevation",
        type=float,
        default=None,
        help="drop times with lower solar elevation [deg]",
    )
    parser.add_argument(
        "--max-shadow-km", type=float, default=5.0, help="cast-shadow search distance [km]"
    )
    parser.add_argument("--out", type=Path, help="write the table as CSV")
    parser.add_argument(
        "--maps", type=Path, help="directory for per-time illumination GeoTIFFs (needs --dem)"
    )
    parser.add_argument(
        "--max-maps", type=int, default=24, help="refuse to write more maps than this"
    )
    args = parser.parse_args()

    times = list(to_utc(args.time)) if args.time else []
    if args.start or args.end:
        if not (args.start and args.end):
            parser.error("--start and --end go together")
        times += list(time_range(args.start, args.end, args.step))
    if not times:
        parser.error("give --time or --start/--end")
    if args.maps and not args.dem:
        parser.error("--maps needs --dem")

    aoi = load_aoi(args.aoi)
    region = load_region(args.dem, aoi) if args.dem else None
    elevation_km = region.elevation_km if region is not None else 0.0
    sun = sun_for_aoi(aoi, np.array(times, dtype="datetime64[s]"), elevation_km=elevation_km)

    if args.min_elevation is None:
        keep = np.ones(sun.zenith_deg.shape, dtype=bool)
    else:
        keep = sun.elevation_deg >= args.min_elevation
    rows = []
    for k in np.flatnonzero(keep):
        row = {
            "time_utc": f"{sun.times_utc[k]}Z",
            "local_solar_time": format_solar_time(sun.local_solar_time_h[k]),
            "solar_zenith_deg": round(float(sun.zenith_deg[k]), 3),
            "apparent_zenith_deg": round(float(sun.apparent_zenith_deg[k]), 3),
            "solar_elevation_deg": round(float(sun.elevation_deg[k]), 3),
            "solar_azimuth_deg": round(float(sun.azimuth_deg[k]), 3),
            "declination_deg": round(float(sun.declination_deg[k]), 3),
            "hour_angle_deg": round(float(sun.hour_angle_deg[k]), 3),
            "equation_of_time_min": round(float(sun.equation_of_time_min[k]), 2),
            "earth_sun_distance_au": round(float(sun.earth_sun_distance_au[k]), 5),
            "above_horizon": bool(sun.above_horizon[k]),
        }
        if region is not None and sun.above_horizon[k]:
            illum = terrain_illumination(
                region, sun.apparent_zenith_deg[k], sun.azimuth_deg[k], args.max_shadow_km * 1000
            )
            row |= {
                key: round(v, 4)
                for key, v in illum.summary().items()
                if key not in ("solar_zenith_deg", "solar_azimuth_deg")
            }
            if args.maps:
                if len(rows) >= args.max_maps:
                    sys.exit(
                        f"more than --max-maps={args.max_maps} maps requested; narrow the time range"
                    )
                args.maps.mkdir(parents=True, exist_ok=True)
                stamp = str(sun.times_utc[k]).replace(":", "").replace("-", "")
                write_maps(args.maps / f"illumination_{stamp}Z.tif", region, illum)
        rows.append(row)

    if not rows:
        sys.exit("no times left after filtering")
    columns = list(SUN_COLUMNS)
    for row in rows:  # terrain columns exist only for rows with the Sun up
        columns += [c for c in row if c not in columns]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, restval="")
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {args.out}")

    lon, lat = aoi.centroid.coords[0][:2]
    print(
        f"AOI centroid: {lat:.4f}°, {lon:.4f}°"
        + (f"   terrain median {elevation_km * 1000:.0f} m" if region else "")
    )
    shown = ["time_utc", "local_solar_time", "solar_elevation_deg", "solar_azimuth_deg"]
    if region is not None:
        shown += ["cos_i_mean", "self_shadow_fraction", "cast_shadow_fraction"]
    print("  ".join(f"{c:>22s}" for c in shown))
    for row in rows:
        print("  ".join(f"{str(row.get(c, '')):>22s}" for c in shown))

    up = sun.above_horizon & keep
    if up.any():
        zen, az = sun.apparent_zenith_deg[up], sun.azimuth_deg[up]
        print("\nB1 inputs:")
        print(
            f"  solar_zenith_deg  = ({zen.min():.1f}, {zen.max():.1f})   # or sun_positions=(zenith, azimuth) pairs"
        )
        start, end = azimuth_span(az)
        if start <= end:
            print(f"  solar_azimuth_deg = ({start:.1f}, {end:.1f})")
        else:
            print(
                f"  solar azimuth spans {start:.1f}° → north → {end:.1f}°: a single (low, high) range"
            )
            print(
                "  cannot express it — pass sun_positions instead (spectralforge.region.region_sampler)"
            )
        if region is not None:
            print(f"  elevation_km      = {elevation_km:.3f}")


if __name__ == "__main__":
    main()
