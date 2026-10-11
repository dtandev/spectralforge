"""Terrain and solar geometry shared by the illumination operators (B1).

Angle conventions (all in degrees):
    solar_zenith   θ_s — 0° = Sun at zenith, must be < 90°.
    solar_azimuth  φ_s — direction TO the Sun, clockwise from north (90° = east).
    slope          s   — 0° = horizontal.
    aspect         φ_n — direction the slope FACES (downslope), clockwise from north.

Local incidence angle i between the Sun and the terrain normal:

    cos i = cos θ_s · cos s + sin θ_s · sin s · cos(φ_s − φ_n)

cos i ≤ 0 means the pixel is self-shadowed (faces away from the Sun). A pixel with
cos i > 0 can still lie in a CAST shadow of surrounding terrain — that, and the fraction of
the sky a pixel sees (sky-view factor), need the DEM neighbourhood: see `TerrainHorizons`.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

AngleSpec = float | tuple[float, float]
"""A fixed angle, or a (low, high) range drawn uniformly."""


def cos_incidence(
    solar_zenith_deg: np.ndarray | float,
    solar_azimuth_deg: np.ndarray | float,
    slope_deg: np.ndarray | float,
    aspect_deg: np.ndarray | float,
) -> np.ndarray:
    """Cosine of the local solar incidence angle (broadcasts over all inputs)."""
    sz = np.radians(solar_zenith_deg)
    s = np.radians(slope_deg)
    return np.cos(sz) * np.cos(s) + np.sin(sz) * np.sin(s) * np.cos(
        np.radians(np.asarray(solar_azimuth_deg) - np.asarray(aspect_deg))
    )


def slope_aspect_from_dem(
    dem: np.ndarray, pixel_size: float | tuple[float, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Slope and aspect (degrees) of a north-up DEM raster.

    Rows are assumed to grow southward and columns eastward (standard north-up GeoTIFF).
    `pixel_size` is in the same unit as the elevations (metres for a projected DEM) —
    a DEM in geographic degrees must be reprojected first. Pass (x_size, y_size) for
    non-square pixels. Aspect of perfectly flat pixels is reported as 0.
    """
    x_size, y_size = (pixel_size, pixel_size) if np.isscalar(pixel_size) else pixel_size
    dz_drow, dz_dcol = np.gradient(np.asarray(dem, dtype=float))
    dz_dx = dz_dcol / x_size  # eastward gradient
    dz_dy = -dz_drow / y_size  # northward gradient
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    aspect = np.degrees(np.arctan2(-dz_dx, -dz_dy)) % 360.0
    return slope, aspect


@dataclass(frozen=True)
class TerrainGeometry:
    """Per-sample Sun/terrain geometry; every field is a 1-D array of equal length.

    `sky_view` (V_d, 0–1) and `cast_shadow` (0 = lit, 1 = in a cast shadow) are optional:
    they need a DEM neighbourhood (`TerrainHorizons`). When absent, models that use them
    fall back to an unobstructed infinite slope: V_d = (1 + cos s) / 2, no cast shadow.
    """

    solar_zenith_deg: np.ndarray
    solar_azimuth_deg: np.ndarray
    slope_deg: np.ndarray
    aspect_deg: np.ndarray
    sky_view: np.ndarray | None = None
    cast_shadow: np.ndarray | None = None

    def __post_init__(self) -> None:
        lengths = {len(np.atleast_1d(v)) for v in vars(self).values() if v is not None}
        if len(lengths) != 1:
            raise ValueError(f"All geometry arrays must have equal length, got {lengths}")
        if np.any(np.asarray(self.solar_zenith_deg) >= 90.0):
            raise ValueError("solar_zenith_deg must be < 90° (Sun above the horizon)")

    def __len__(self) -> int:
        return len(np.atleast_1d(self.solar_zenith_deg))

    @property
    def cos_i(self) -> np.ndarray:
        return cos_incidence(
            self.solar_zenith_deg, self.solar_azimuth_deg, self.slope_deg, self.aspect_deg
        )

    @property
    def sky_view_or_default(self) -> np.ndarray:
        """V_d, or the unobstructed infinite-slope value (1 + cos s) / 2 when unknown."""
        if self.sky_view is not None:
            return np.asarray(self.sky_view, dtype=float)
        return (1 + np.cos(np.radians(self.slope_deg))) / 2

    @property
    def cast_shadow_or_default(self) -> np.ndarray:
        if self.cast_shadow is not None:
            return np.asarray(self.cast_shadow, dtype=float)
        return np.zeros(len(self))

    @classmethod
    def concatenate(cls, parts: list["TerrainGeometry"]) -> "TerrainGeometry":
        fields = {}
        for f in cls.__dataclass_fields__:
            values = [getattr(p, f) for p in parts]
            fields[f] = None if any(v is None for v in values) else np.concatenate(values)
        return cls(**fields)

    def subset(self, mask: np.ndarray) -> "TerrainGeometry":
        return TerrainGeometry(
            **{
                f: None if getattr(self, f) is None else np.asarray(getattr(self, f))[mask]
                for f in self.__dataclass_fields__
            }
        )


GeometrySampler = Callable[[np.random.Generator, int], TerrainGeometry]


def horizon_elevation(
    dem: np.ndarray, pixel_size: float, azimuth_deg: float, max_distance: float
) -> np.ndarray:
    """Elevation angle (degrees) of the terrain horizon seen from every pixel along one azimuth.

    Marches outward pixel by pixel (nearest neighbour) up to `max_distance` (same unit as
    `pixel_size`, square pixels). Terrain beyond the raster edge is treated as absent, so
    pixels near the edge may have their horizon underestimated. Returns −90° where nothing
    is found in range.
    """
    z = np.asarray(dem, dtype=float)
    rows, cols = np.indices(z.shape)
    d_row, d_col = -np.cos(np.radians(azimuth_deg)), np.sin(np.radians(azimuth_deg))
    best = np.full(z.shape, -90.0)
    for step in range(1, int(np.ceil(max_distance / pixel_size)) + 1):
        r = np.rint(rows + step * d_row).astype(int)
        c = np.rint(cols + step * d_col).astype(int)
        inside = (r >= 0) & (r < z.shape[0]) & (c >= 0) & (c < z.shape[1])
        if not inside.any():
            break
        rise = np.where(
            inside, z[r.clip(0, z.shape[0] - 1), c.clip(0, z.shape[1] - 1)] - z, -np.inf
        )
        best = np.maximum(best, np.degrees(np.arctan(rise / (step * pixel_size))))
    return best


def sky_view_factor(
    horizon_elevation_deg: np.ndarray,
    azimuths_deg: np.ndarray,
    slope_deg: np.ndarray | float,
    aspect_deg: np.ndarray | float,
) -> np.ndarray:
    """Sky-view factor V_d for a tilted surface (Dozier & Frew 1990).

        V_d = 1/2π ∫ [cos s · sin² H_φ + sin s · cos(φ − φ_n) · (H_φ − sin H_φ · cos H_φ)] dφ

    H_φ is the horizon ZENITH angle in direction φ: the terrain horizon (never below the
    horizontal — the far field is assumed flat), or the surface's own tangent plane where
    that is higher. `horizon_elevation_deg` has shape
    (n_directions, ...) for equally spaced `azimuths_deg`. An unobstructed slope gives
    (1 + cos s) / 2; a flat open plain gives 1.
    """
    phi = np.radians(np.asarray(azimuths_deg, dtype=float))
    phi = phi.reshape((-1,) + (1,) * (np.ndim(horizon_elevation_deg) - 1))
    s = np.radians(slope_deg)
    rel = phi - np.radians(aspect_deg)
    # Horizons below the horizontal are clipped to 0°: the far field is assumed flat.
    h_terrain = np.radians(
        90.0 - np.clip(np.asarray(horizon_elevation_deg, dtype=float), 0.0, None)
    )
    h_plane = np.pi / 2 + np.arctan(np.tan(s) * np.cos(rel))
    h = np.minimum(h_terrain, h_plane)
    integrand = np.cos(s) * np.sin(h) ** 2 + np.sin(s) * np.cos(rel) * (h - np.sin(h) * np.cos(h))
    return integrand.mean(axis=0)


@dataclass(frozen=True)
class TerrainHorizons:
    """Terrain horizons of a DEM in `n` equally spaced directions, plus slope/aspect.

    Built once per DEM (`from_dem`), then queried for sky-view factors and for cast
    shadows under any Sun position — the expensive ray marching is not repeated per draw.
    """

    azimuths_deg: np.ndarray  # (n_directions,)
    elevation_deg: np.ndarray  # (n_directions, rows, cols)
    slope_deg: np.ndarray  # (rows, cols)
    aspect_deg: np.ndarray  # (rows, cols)

    @classmethod
    def from_dem(
        cls,
        dem: np.ndarray,
        pixel_size: float,
        n_directions: int = 32,
        max_distance: float | None = None,
    ) -> "TerrainHorizons":
        """Default `max_distance`: the range beyond which the DEM relief cannot raise the
        horizon above 2°, capped at the raster diagonal."""
        z = np.asarray(dem, dtype=float)
        if max_distance is None:
            relief = float(np.nanmax(z) - np.nanmin(z))
            diagonal = float(np.hypot(*z.shape)) * pixel_size
            max_distance = min(relief / np.tan(np.radians(2.0)), diagonal) or pixel_size
        azimuths = np.arange(n_directions) * 360.0 / n_directions
        elevation = np.stack([horizon_elevation(z, pixel_size, a, max_distance) for a in azimuths])
        slope, aspect = slope_aspect_from_dem(z, pixel_size)
        return cls(azimuths, elevation, slope, aspect)

    def sky_view(self) -> np.ndarray:
        """V_d map (rows, cols)."""
        return sky_view_factor(
            self.elevation_deg, self.azimuths_deg, self.slope_deg, self.aspect_deg
        )

    def horizon_towards(self, azimuth_deg: np.ndarray, flat_index: np.ndarray) -> np.ndarray:
        """Horizon elevation (degrees) at pixels `flat_index` towards `azimuth_deg`
        (one azimuth per pixel), interpolated circularly between the stored directions."""
        n = len(self.azimuths_deg)
        step = 360.0 / n
        position = (np.asarray(azimuth_deg, dtype=float) % 360.0) / step
        lower = np.floor(position).astype(int) % n
        upper = (lower + 1) % n
        weight = position - np.floor(position)
        flat = self.elevation_deg.reshape(n, -1)
        return (1 - weight) * flat[lower, flat_index] + weight * flat[upper, flat_index]

    def cast_shadow(
        self, solar_zenith_deg: np.ndarray, solar_azimuth_deg: np.ndarray, flat_index: np.ndarray
    ) -> np.ndarray:
        """1.0 where the Sun is below the terrain horizon (cast shadow), else 0.0."""
        sun_elevation = 90.0 - np.asarray(solar_zenith_deg, dtype=float)
        return (sun_elevation < self.horizon_towards(solar_azimuth_deg, flat_index)).astype(float)


def draw_uniform(rng: np.random.Generator, spec: AngleSpec, n: int) -> np.ndarray:
    """`n` copies of a fixed value, or `n` uniform draws from a (low, high) range."""
    if np.isscalar(spec):
        return np.full(n, float(spec))
    low, high = spec
    return rng.uniform(low, high, n)


def _rejection_sample(
    rng: np.random.Generator,
    n: int,
    propose: Callable[[int], TerrainGeometry],
    min_cos_i: float,
    max_rounds: int = 100,
) -> TerrainGeometry:
    kept: list[TerrainGeometry] = []
    total = 0
    for _ in range(max_rounds):
        candidates = propose(max(2 * (n - total), 16))
        accepted = candidates.subset(candidates.cos_i > min_cos_i)
        kept.append(accepted)
        total += len(accepted)
        if total >= n:
            return TerrainGeometry.concatenate(kept).subset(slice(0, n))
    raise ValueError(
        f"Could not draw {n} geometries with cos i > {min_cos_i} after {max_rounds} rounds — "
        "the Sun/slope ranges leave (almost) no illuminated terrain."
    )


def sample_geometry_uniform(
    rng: np.random.Generator,
    n: int,
    solar_zenith_deg: AngleSpec = (20.0, 60.0),
    solar_azimuth_deg: AngleSpec = (0.0, 360.0),
    slope_deg: AngleSpec = (0.0, 35.0),
    aspect_deg: AngleSpec = (0.0, 360.0),
    min_cos_i: float = 0.0,
) -> TerrainGeometry:
    """Draw geometries with each angle fixed or uniform in a range.

    A placeholder when no DEM of the target region is available: uniform slopes do not
    reproduce a real terrain's slope distribution — prefer `sample_geometry_from_dem`.
    Draws with cos i ≤ `min_cos_i` (self-shadowed terrain) are rejected and redrawn.
    The default ranges are illustrative, not tied to any specific scene.
    """

    def propose(m: int) -> TerrainGeometry:
        return TerrainGeometry(
            draw_uniform(rng, solar_zenith_deg, m),
            draw_uniform(rng, solar_azimuth_deg, m),
            draw_uniform(rng, slope_deg, m),
            draw_uniform(rng, aspect_deg, m),
        )

    return _rejection_sample(rng, n, propose, min_cos_i)


def sample_geometry_from_dem(
    rng: np.random.Generator,
    n: int,
    slope_deg: np.ndarray,
    aspect_deg: np.ndarray,
    solar_zenith_deg: AngleSpec,
    solar_azimuth_deg: AngleSpec,
    min_cos_i: float = 0.0,
    horizons: TerrainHorizons | None = None,
) -> TerrainGeometry:
    """Draw geometries from random pixels of a real terrain (see `slope_aspect_from_dem`).

    Solar angles come from the target scenes' metadata — fixed for one acquisition, or a
    (low, high) range covering several. NaN pixels (no-data) are never drawn. With
    `horizons` (same raster as slope/aspect), each draw also gets the pixel's sky-view
    factor and its cast-shadow state under the drawn Sun position.
    """
    slope = np.asarray(slope_deg, dtype=float).ravel()
    aspect = np.asarray(aspect_deg, dtype=float).ravel()
    valid = np.flatnonzero(np.isfinite(slope) & np.isfinite(aspect))
    if valid.size == 0:
        raise ValueError("DEM contains no valid (finite) pixels")
    if horizons is not None and horizons.slope_deg.size != slope.size:
        raise ValueError("horizons must be computed on the same raster as slope/aspect")
    sky_view = None if horizons is None else horizons.sky_view().ravel()

    def propose(m: int) -> TerrainGeometry:
        idx = rng.choice(valid, m)
        sz = draw_uniform(rng, solar_zenith_deg, m)
        saz = draw_uniform(rng, solar_azimuth_deg, m)
        return TerrainGeometry(
            sz,
            saz,
            slope[idx],
            aspect[idx],
            sky_view=None if sky_view is None else sky_view[idx],
            cast_shadow=None if horizons is None else horizons.cast_shadow(sz, saz, idx),
        )

    return _rejection_sample(rng, n, propose, min_cos_i)
