import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from spectralforge.dem import (
    download_copernicus_dem,
    load_aoi,
    load_region,
    tile_name,
    tiles_for_bounds,
    utm_crs,
)

# AOI straddling the 22°S tile boundary (El Abra-like).
AOI = box(-68.95, -22.05, -68.85, -21.95)


def test_tile_names_follow_the_south_west_corner():
    assert tile_name(-22, -69) == "Copernicus_DSM_COG_10_S22_00_W069_00_DEM"
    assert tile_name(50, 19) == "Copernicus_DSM_COG_10_N50_00_E019_00_DEM"
    assert tile_name(0, 0) == "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"


def test_tiles_for_bounds_covers_every_intersected_tile_only():
    assert tiles_for_bounds(-68.97, -22.02, -68.77, -21.86) == [
        tile_name(-23, -69),
        tile_name(-22, -69),
    ]
    assert tiles_for_bounds(10.0, 50.0, 11.0, 51.0) == [tile_name(50, 10)]  # edges on degrees
    assert len(tiles_for_bounds(10.5, 50.5, 12.5, 51.5)) == 6
    with pytest.raises(ValueError, match="antimeridian"):
        tiles_for_bounds(179.5, 0.0, -179.5, 1.0)


@pytest.mark.parametrize(
    ("lon", "lat", "epsg"), [(-68.8, -21.9, 32719), (19.94, 50.06, 32634), (0.5, 0.0, 32631)]
)
def test_utm_crs(lon, lat, epsg):
    assert utm_crs(lon, lat).to_epsg() == epsg


@pytest.mark.parametrize("wrap", ["collection", "feature", "geometry"])
def test_load_aoi_accepts_geojson_variants(tmp_path, wrap):
    geometry = mapping(AOI)
    data = {
        "collection": {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": geometry}],
        },
        "feature": {"type": "Feature", "properties": {}, "geometry": geometry},
        "geometry": geometry,
    }[wrap]
    path = tmp_path / "aoi.geojson"
    path.write_text(json.dumps(data))
    assert load_aoi(path).equals(AOI)


def test_load_aoi_rejects_projected_crs(tmp_path):
    path = tmp_path / "aoi.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3857"}},
                "features": [{"type": "Feature", "properties": {}, "geometry": mapping(AOI)}],
            }
        )
    )
    with pytest.raises(ValueError, match="WGS84"):
        load_aoi(path)


def synthetic_elevation(lon, lat):
    """Plane rising 500 m per degree northward and 200 m per degree eastward."""
    return 3000.0 + 500.0 * (lat + 22.0) + 200.0 * (lon + 69.0)


@pytest.fixture
def local_tiles(tmp_path):
    """Two 1° GLO-30-like tiles (EPSG:4326, 0.005° pixels) named like the real ones."""
    size, step = 200, 0.005
    for lat_floor in (-23, -22):
        transform = from_origin(-69.0, lat_floor + 1.0, step, step)
        rows, cols = np.mgrid[0:size, 0:size]
        lon = -69.0 + (cols + 0.5) * step
        lat = lat_floor + 1.0 - (rows + 0.5) * step
        with rasterio.open(
            tmp_path / f"{tile_name(lat_floor, -69)}.tif",
            "w",
            driver="GTiff",
            width=size,
            height=size,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(synthetic_elevation(lon, lat).astype("float32"), 1)
    return str(tmp_path / "{name}.tif")


def test_download_mosaics_tiles_and_reprojects_to_utm(tmp_path, local_tiles):
    out = download_copernicus_dem(
        AOI, tmp_path / "dem.tif", buffer_m=2000, resolution_m=100, url_template=local_tiles
    )
    with rasterio.open(out) as src:
        assert src.crs.to_epsg() == 32719
        assert src.res == (100.0, 100.0)
        assert set(src.tags()["tiles"].split(",")) == {tile_name(-23, -69), tile_name(-22, -69)}
    region = load_region(out, AOI)
    assert np.isfinite(region.elevation[region.aoi_mask]).all()
    lon, lat = AOI.centroid.coords[0]
    assert region.elevation_km * 1000 == pytest.approx(synthetic_elevation(lon, lat), abs=5)
    _, aspect = region.slope_aspect
    # Terrain rises towards N-NE, so slopes face roughly S-SW (aspect ~ 180–200°).
    assert 170 < np.nanmedian(aspect[region.aoi_mask]) < 210


def test_download_reuses_existing_file_unless_overwrite(tmp_path, local_tiles):
    out = tmp_path / "dem.tif"
    out.write_bytes(b"not a tiff")
    assert download_copernicus_dem(AOI, out, url_template=local_tiles) == out
    assert out.read_bytes() == b"not a tiff"


def test_download_skips_missing_tiles_and_fails_without_any(tmp_path, local_tiles):
    (tmp_path / f"{tile_name(-23, -69)}.tif").unlink()
    with pytest.warns(UserWarning, match="Skipped missing tiles"):
        out = download_copernicus_dem(
            AOI, tmp_path / "dem.tif", buffer_m=0, resolution_m=200, url_template=local_tiles
        )
    region = load_region(out, AOI)
    assert np.isnan(region.elevation).any() and np.isfinite(region.elevation).any()
    with pytest.raises(RuntimeError, match="No Copernicus"):
        download_copernicus_dem(
            box(10.1, 50.1, 10.2, 50.2), tmp_path / "none.tif", url_template=local_tiles
        )
