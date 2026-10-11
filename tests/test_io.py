import numpy as np
import pytest

from spectralforge.io import load_splib_csv

HEADER = (
    "splib07b Record=1238: Alunite HS295.1B             ASDFRa AREF,"
    "splib07b Record=4195: Chlorite SMR-13.a 104-150um BECKa AREF\n"
)


def test_load_splib_csv_parses_headers_and_bands(tmp_path):
    path = tmp_path / "lib.csv"
    path.write_text(HEADER + "0.1,0.5\n0.2,0.6\n0.3,0.7\n")

    lib = load_splib_csv(path, wavelengths_nm=[400, 500, 600])

    assert lib.reflectance.shape == (2, 3)
    np.testing.assert_allclose(lib.reflectance[1], [0.5, 0.6, 0.7])
    assert lib.names == ["Alunite HS295.1B", "Chlorite SMR-13.a 104-150um"]
    assert lib.minerals == ["Alunite", "Chlorite"]
    assert lib.records == [1238, 4195]
    assert lib.select("chlorite").names == ["Chlorite SMR-13.a 104-150um"]


def test_load_splib_csv_requires_wavelengths_for_non_asd_grid(tmp_path):
    path = tmp_path / "lib.csv"
    path.write_text(HEADER + "0.1,0.5\n")
    with pytest.raises(ValueError, match="wavelengths_nm"):
        load_splib_csv(path)
