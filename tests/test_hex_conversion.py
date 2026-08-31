from pathlib import Path

import pytest
import xarray as xr
from conftest import cnv_path, hex_path
from numpy.testing import assert_allclose

from ctdam.parser.read_ctd_data import parse, read_cnv, read_hex


@pytest.fixture(params=hex_path.glob("*.hex"), scope="class")
def ds(request):
    if request.param.stem == "EMB379_000-00_SF_0001":
        pytest.skip("PyroScience Oxygen Sensor not supported yet.")
    return read_hex(request.param)


class TestHexConversion:
    def test_datcnv_comparison(self, ds):
        assert "conductivity" in ds.data_vars
        file_name = Path(ds.attrs["path_to_source_file"]).name
        try:
            comp_ds = read_cnv((cnv_path / file_name).with_suffix(".cnv"))
        except FileNotFoundError:
            pytest.skip(f"No comparison file for {file_name}")
        comparison_file_length = comp_ds.access.size
        for parameter in ds.data_vars:
            if "qc" in parameter:
                continue
            try:
                comparison = comp_ds[parameter].data
            except KeyError:
                continue
            if parameter in [
                # "oxygen",
                "par_biosphericallicorchelsea",
            ]:
                continue

            actual = ds[parameter].data[:comparison_file_length]

            # HEX can contain two sensors while
            # the comparison CNV contains only one.
            # In that case compare the primary sensor.
            if actual.ndim == 2 and comparison.ndim == 1:
                actual = actual[:, 0]

            assert_allclose(
                actual,
                comparison,
                rtol=1,
                atol=0,
                err_msg=f"{file_name}: mismatch for parameter {parameter}",
            )

    @pytest.mark.skip(reason="Not implemented")
    def test_cnv_export(self, ds, create_files):
        if not isinstance(ds, xr.Dataset):
            pytest.skip()
        file_path = (
            hex_path / f"out_test_{Path(ds.attrs['path_to_source_file']).name}"
        )
        ds.export.to_cnv(file_path)
        if not create_files:
            file_path.unlink()

    def test_downcast_only(self, ds):
        file_path = Path(ds.attrs["path_to_source_file"])

        downcast = parse(
            file_path,
            downcast_only=True,
        )

        assert downcast.sizes["scan"] < ds.sizes["scan"]
        assert "castborders" in downcast.meta.provenance
