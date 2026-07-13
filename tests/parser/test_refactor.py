import pytest
from conftest import (
    cnv_path,
)
from ctdam.parser.read_ctd_data import read_cnv


@pytest.mark.parametrize(
    "file",
    [file for file in cnv_path.glob("*.cnv")],
)
def test_cnv_xarray_parsing(file):
    ds = read_cnv(file)
    for var in ds.data_vars:
        assert "standard_name" in ds[var].attrs
        if "qc" in var:
            assert "flag_values" in ds[var].attrs
        else:
            assert "units" in ds[var].attrs
