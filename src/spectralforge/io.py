"""Loading reference spectral libraries from local files.

Supported format — the USGS splib07b export used in data/signatures/*.csv:
one column per spectrum, header like
    "splib07b Record=1238: Alunite HS295.1B             ASDFRa AREF"
one row per band, no wavelength column.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# splib07b oversampled spectra share the 2151-channel ASD grid, 350–2500 nm at 1 nm.
# TODO: verify this against the source export — the CSV itself carries no wavelengths.
SPLIB07B_WAVELENGTHS_NM = np.arange(350.0, 2501.0)

_HEADER_RE = re.compile(r"Record=(?P<record>\d+):\s*(?P<name>.+?)\s+(?P<instrument>\S+)\s+AREF\s*$")


@dataclass(frozen=True)
class SpectralLibrary:
    wavelengths_nm: np.ndarray  # (n_bands,)
    reflectance: np.ndarray  # (n_spectra, n_bands)
    names: list[str]  # full sample name, e.g. "Alunite HS295.1B"
    minerals: list[str]  # first token of the name, e.g. "Alunite"
    records: list[int | None]  # USGS record number

    def select(self, mineral: str) -> "SpectralLibrary":
        """Spectra of one mineral (exact, case-insensitive match on `minerals`)."""
        idx = [k for k, m in enumerate(self.minerals) if m.lower() == mineral.lower()]
        return SpectralLibrary(
            self.wavelengths_nm,
            self.reflectance[idx],
            [self.names[k] for k in idx],
            [self.minerals[k] for k in idx],
            [self.records[k] for k in idx],
        )


def load_splib_csv(path: str | Path, wavelengths_nm: np.ndarray | None = None) -> SpectralLibrary:
    """Load a column-per-spectrum USGS CSV export.

    Without `wavelengths_nm`, the splib07b ASD grid is assumed (requires 2151 rows).
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    reflectance = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2).T

    if wavelengths_nm is None:
        if reflectance.shape[1] != len(SPLIB07B_WAVELENGTHS_NM):
            raise ValueError(
                f"{path.name}: {reflectance.shape[1]} bands — pass wavelengths_nm explicitly "
                f"(default grid assumes {len(SPLIB07B_WAVELENGTHS_NM)})"
            )
        wavelengths_nm = SPLIB07B_WAVELENGTHS_NM
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float)
    if len(wavelengths_nm) != reflectance.shape[1]:
        raise ValueError(f"{len(wavelengths_nm)} wavelengths for {reflectance.shape[1]} bands")

    names, records = [], []
    for column in header:
        match = _HEADER_RE.search(column)
        names.append(" ".join(match["name"].split()) if match else column.strip())
        records.append(int(match["record"]) if match else None)

    return SpectralLibrary(
        wavelengths_nm=wavelengths_nm,
        reflectance=reflectance,
        names=names,
        minerals=[n.split()[0] if n else n for n in names],
        records=records,
    )
