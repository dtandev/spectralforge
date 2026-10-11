"""B0 — area of interest (AOI) and Copernicus DEM GLO-30 for it.

Copernicus DEM GLO-30: global 1 arc-second (~30 m) DSM, free, distributed as Cloud-Optimized
GeoTIFF tiles of 1° × 1° on AWS Open Data (no account needed). Heights are orthometric,
relative to the EGM2008 geoid. Tiles are named after their south-west corner, e.g.
`Copernicus_DSM_COG_10_S22_00_W069_00_DEM` covers 22°S–21°S, 69°W–68°W. Ocean-only tiles do
not exist (HTTP 404) and are skipped.

The DEM is written reprojected to the AOI's UTM zone (metres — needed for slopes and
horizons) and extended by a buffer around the AOI, because terrain outside the AOI still
casts shadows and blocks the sky inside it (see `spectralforge.terrain.TerrainHorizons`).
"""

import json
import math
import warnings
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.errors import RasterioIOError
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds, transform_geom
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from spectralforge.terrain import slope_aspect_from_dem

COPERNICUS_GLO30_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
WGS84_NAMES = {"urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:EPSG::4326", "EPSG:4326"}
GDAL_REMOTE_OPTIONS = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "AWS_NO_SIGN_REQUEST": "YES"}


def load_aoi(path: str | Path) -> BaseGeometry:
    """Union of all geometries in a GeoJSON file, in lon/lat (WGS84).

    GeoJSON is lon/lat by definition (RFC 7946); a legacy `crs` member other than WGS84 is
    rejected rather than silently misread.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    crs_name = (data.get("crs") or {}).get("properties", {}).get("name")
    if crs_name is not None and crs_name not in WGS84_NAMES:
        raise ValueError(f"AOI must be in WGS84 lon/lat, got crs {crs_name!r}")
    if data.get("type") == "FeatureCollection":
        geometries = [shape(f["geometry"]) for f in data["features"] if f.get("geometry")]
    elif data.get("type") == "Feature":
        geometries = [shape(data["geometry"])]
    else:
        geometries = [shape(data)]
    if not geometries:
        raise ValueError(f"{path}: no geometries found")
    aoi = unary_union(geometries)
    west, south, east, north = aoi.bounds
    if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise ValueError(f"AOI bounds {aoi.bounds} are not valid lon/lat")
    return aoi


def utm_crs(lon: float, lat: float) -> CRS:
    """UTM zone (WGS84) containing the point."""
    zone = int((lon + 180) // 6) % 60 + 1
    return CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)


def tile_name(lat_floor: int, lon_floor: int) -> str:
    """Copernicus GLO-30 tile covering [lat_floor, lat_floor+1] × [lon_floor, lon_floor+1]."""
    lat = f"{'N' if lat_floor >= 0 else 'S'}{abs(lat_floor):02d}_00"
    lon = f"{'E' if lon_floor >= 0 else 'W'}{abs(lon_floor):03d}_00"
    return f"Copernicus_DSM_COG_10_{lat}_{lon}_DEM"


def tiles_for_bounds(west: float, south: float, east: float, north: float) -> list[str]:
    """Names of all 1° tiles intersecting a lon/lat box (antimeridian crossing unsupported)."""
    if west > east or south > north:
        raise ValueError("expected west <= east and south <= north (antimeridian unsupported)")
    # A box ending exactly on a degree line does not need the tile beyond it.
    lat_max = math.ceil(north) - 1 if north > math.floor(south) else math.floor(south)
    lon_max = math.ceil(east) - 1 if east > math.floor(west) else math.floor(west)
    return [
        tile_name(lat, lon)
        for lat in range(math.floor(south), lat_max + 1)
        for lon in range(math.floor(west), lon_max + 1)
    ]


def download_copernicus_dem(
    aoi: BaseGeometry | str | Path,
    out_path: str | Path,
    buffer_m: float = 10_000.0,
    resolution_m: float = 30.0,
    crs: CRS | str | None = None,
    overwrite: bool = False,
    url_template: str = COPERNICUS_GLO30_URL,
) -> Path:
    """Download Copernicus GLO-30 for the AOI plus a buffer, reprojected to a metric grid.

    Only the needed parts of each remote COG are read (via GDAL /vsicurl/ range requests).
    The output GeoTIFF is float32, NaN = no data, on a `resolution_m` grid in `crs`
    (default: the UTM zone of the AOI centroid). An existing file is reused unless
    `overwrite=True`. `url_template` (with `{name}`) can point to a local mirror.
    """
    out_path = Path(out_path)
    if out_path.exists() and not overwrite:
        return out_path
    aoi = load_aoi(aoi) if isinstance(aoi, str | Path) else aoi
    dst_crs = CRS.from_user_input(crs) if crs is not None else utm_crs(*aoi.centroid.coords[0][:2])

    # Target grid: AOI bounds in the metric CRS, buffered and snapped to the resolution.
    x0, y0, x1, y1 = transform_bounds("EPSG:4326", dst_crs, *aoi.bounds, densify_pts=21)
    west = math.floor((x0 - buffer_m) / resolution_m) * resolution_m
    south = math.floor((y0 - buffer_m) / resolution_m) * resolution_m
    east = math.ceil((x1 + buffer_m) / resolution_m) * resolution_m
    north = math.ceil((y1 + buffer_m) / resolution_m) * resolution_m
    width, height = round((east - west) / resolution_m), round((north - south) / resolution_m)
    transform = from_origin(west, north, resolution_m, resolution_m)

    lonlat_bounds = transform_bounds(dst_crs, "EPSG:4326", west, south, east, north, densify_pts=21)
    elevation = np.full((height, width), np.nan, dtype=np.float32)
    used, missing = [], []
    with rasterio.Env(**GDAL_REMOTE_OPTIONS):
        for name in tiles_for_bounds(*lonlat_bounds):
            try:
                with rasterio.open(url_template.format(name=name)) as src:
                    with WarpedVRT(
                        src,
                        crs=dst_crs,
                        transform=transform,
                        width=width,
                        height=height,
                        resampling=Resampling.bilinear,
                        src_nodata=src.nodata,
                        nodata=np.nan,
                        dtype="float32",
                    ) as vrt:
                        part = vrt.read(1)
            except RasterioIOError:
                missing.append(name)
                continue
            fill = np.isnan(elevation) & np.isfinite(part)
            elevation[fill] = part[fill]
            used.append(name)

    if not used:
        raise RuntimeError(f"No Copernicus GLO-30 tile available for the AOI (tried {missing})")
    if missing:
        warnings.warn(f"Skipped missing tiles (ocean or no coverage): {missing}", stacklevel=2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "width": width,
        "height": height,
        "crs": dst_crs,
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate",
        "predictor": 3,
        "tiled": True,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(elevation, 1)
        dst.update_tags(
            source="Copernicus DEM GLO-30 (AWS Open Data)",
            vertical_datum="EGM2008",
            tiles=",".join(used),
            buffer_m=str(buffer_m),
            aoi_bounds_lonlat=",".join(f"{v:.6f}" for v in aoi.bounds),
        )
    return out_path


@dataclass(frozen=True)
class RegionDEM:
    """A metric DEM of the AOI plus its buffer, with the AOI footprint as a mask."""

    elevation: np.ndarray  # (rows, cols) metres, NaN = no data
    transform: rasterio.Affine
    crs: CRS
    aoi: BaseGeometry  # lon/lat
    aoi_mask: np.ndarray  # (rows, cols) True inside the AOI

    @property
    def pixel_size(self) -> float:
        x, y = abs(self.transform.a), abs(self.transform.e)
        if not math.isclose(x, y, rel_tol=1e-6):
            raise ValueError(f"non-square pixels ({x} × {y}) are not supported")
        return x

    @property
    def center_lonlat(self) -> tuple[float, float]:
        lon, lat = self.aoi.centroid.coords[0][:2]
        return lon, lat

    @property
    def elevation_km(self) -> float:
        """Median terrain height inside the AOI, in km — the `elevation_km` input of B1."""
        return float(np.nanmedian(self.elevation[self.aoi_mask])) / 1000.0

    @cached_property
    def slope_aspect(self) -> tuple[np.ndarray, np.ndarray]:
        return slope_aspect_from_dem(self.elevation, self.pixel_size)


def load_region(dem_path: str | Path, aoi: BaseGeometry | str | Path) -> RegionDEM:
    """Read a DEM written by `download_copernicus_dem` and rasterise the AOI onto it."""
    aoi = load_aoi(aoi) if isinstance(aoi, str | Path) else aoi
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype(float)
        if src.nodata is not None and not np.isnan(src.nodata):
            elevation[elevation == src.nodata] = np.nan
        aoi_projected = transform_geom("EPSG:4326", src.crs, mapping(aoi))
        mask = ~geometry_mask([aoi_projected], out_shape=elevation.shape, transform=src.transform)
        region = RegionDEM(elevation, src.transform, src.crs, aoi, mask)
    if not region.aoi_mask.any():
        raise ValueError("AOI does not overlap the DEM")
    return region
