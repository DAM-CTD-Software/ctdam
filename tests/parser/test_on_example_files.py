import logging
from datetime import datetime
from pathlib import Path

import netCDF4 as nc
import pandas as pd
import pytest
from conftest import (
    base_path,
    btl_path,
    check_and_remove_file,
    cnv_path,
    hex_path,
)

from ctdam.parser import BottleFile, CnvFile, GEOMARCTDFile, HexFile

logger = logging.getLogger()


@pytest.mark.parametrize(
    "file",
    [file for file in cnv_path.glob("*.cnv")],
)
class TestExampleFiles:
    @pytest.fixture
    def cnv(self, file: Path, run_long_tests: bool):
        if (not run_long_tests) and (file.stat().st_size > 5 * 1000000):
            pytest.skip(f"Skipping long cnv: {file}")
        try:
            cnv = CnvFile(
                file,
                create_dataframe=True,
                absolute_time_calculation=True,
            )
        except FileNotFoundError as error:
            pytest.skip(str(error))
        else:
            return cnv

    def test_found_start_time(self, cnv: CnvFile):
        assert isinstance(cnv.start_time, datetime)

    def test_calculate_full_time(self, cnv):
        assert (cnv.absolute_time_calculation()) == (
            len([p for p in cnv.parameters.keys() if p.startswith("time")]) > 0
        )

    def test_ctd_cnv2netCDF_conversion(self, cnv):
        if cnv.file_name == "SO300-2_063":
            pytest.skip()
        ctd_data = cnv.to_ctd_data()
        expected_nc_path = cnv.path_to_file.with_suffix(".nc")
        if expected_nc_path.exists():
            expected_nc_path.unlink()

        try:
            ctd_data.to_netCDF(file_path=cnv.path_to_file)

            assert expected_nc_path.exists(), "netCDF file not created"

            with nc.Dataset(expected_nc_path, "r") as ds:
                expected_vars = ["latitude", "longitude", "timeS", "depth"]
                for var in expected_vars:
                    assert var in ds.variables, (
                        f"variable '{var}' missing in NetCDF."
                    )
                    assert len(ds.variables[var][:]) > 0, (
                        f"variable '{var}' has no data"
                    )

                assert ds.variables["depth"].units == "m"
                assert ds.variables["latitude"].units == "deg"
                assert ds.variables["longitude"].units == "deg"
                assert ds.variables["timeS"].units == "seconds"
        except KeyError as error:
            pytest.fail(f"{error}")
        finally:
            if expected_nc_path.exists():
                try:
                    expected_nc_path.unlink()
                except PermissionError:
                    pass

    def test_ctd_data2cnv_conversion(self, cnv):
        ctd_data = cnv.to_ctd_data()
        test_cnv = cnv.path_to_file.with_stem(
            f"conversion_test_{cnv.path_to_file.stem}"
        )
        ctd_data.to_cnv(test_cnv)
        # test seabird metadata
        assert cnv.sbe9_data == CnvFile(test_cnv).sbe9_data
        # test custom metadata
        assert cnv.metadata == CnvFile(test_cnv).metadata
        # test sensor xml
        assert cnv.sensor_data == CnvFile(test_cnv).sensor_data
        # test processing_steps
        assert cnv.processing_steps == CnvFile(test_cnv).processing_steps
        test_cnv.unlink()

    def test_export_to_file(self, cnv, tmp_path):
        output_path = tmp_path.joinpath(cnv.file_name).with_suffix(".cnv")
        cnv.to_cnv(output_path)
        check_and_remove_file(output_path)

    def test_processing_step_extraction(self, cnv: CnvFile):
        assert cnv.processing_steps

    def test_sample_rate_retrieval(self, cnv):
        if cnv.file_name == "MSM140_1":
            target_rate = 1
        else:
            target_rate = 24
        assert cnv.parameters.sample_rate == target_rate

    def test_presence_of_default_parameters(self, cnv):
        for param in ["timeS", "latitude", "longitude"]:
            assert param in cnv.parameters


@pytest.mark.parametrize(
    "filename",
    [filename for filename in hex_path.glob("*.hex")],
)
class TestHexFiles:
    @pytest.fixture
    def hex(self, filename: str) -> HexFile:
        return HexFile(filename)

    def test_read_only_metadata(self, hex: HexFile):
        assert len(hex.data) == 0


@pytest.mark.parametrize(
    "filename",
    [filename for filename in btl_path.rglob("*.btl")],
)
def test_btl_reading(filename):
    btl = BottleFile(filename)
    assert "Timestamp" in btl.df.columns


def test_geomar_ctd_file():
    file_path = base_path.joinpath("other", "son_308_1_007.ctd")
    ctd = GEOMARCTDFile(file_path)
    assert isinstance(ctd.df, pd.DataFrame)
