import re
import warnings
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pytest
from conftest import hex_path
from numpy.testing import assert_allclose, assert_equal

from ctdam.conv.hexdecoder import (
    decode_hex,
    get_time_gaps,
    handle_time,
    hex_reading,
)
from ctdam.parser import CnvFile
from ctdam.parser.ctddata import CTDData
from ctdam.parser.hexfile import HexFile
from ctdam.parser.parameter import Parameters
from ctdam.utils import create_event_string, read_event_name


@pytest.fixture(params=hex_path.glob("*.hex"), scope="class")
def ctd_data(request):
    return decode_hex(request.param)


class TestDecoding:
    def test_cnv_export(self, ctd_data: CTDData, tmp_path):
        file_name = ctd_data.file_name
        test_path = tmp_path.joinpath(f"test_decoded_{file_name}.cnv")
        _, cnv = ctd_data.to_cnv(test_path, remove_flags=False)
        assert [line.strip() for line in cnv] == [
            line.strip() for line in CnvFile(test_path).raw_file_data
        ]

    def test_datcnv_comparison(self, ctd_data: CTDData):
        cast_borders_dict = ctd_data.cast_borders
        try:
            datcnv_cnv = CnvFile(
                hex_path.joinpath(ctd_data.file_name + "_down").with_suffix(
                    ".cnv"
                )
            )
        except FileNotFoundError:
            with pytest.warns(UserWarning):
                warnings.warn(
                    f"No comparison file for {ctd_data.metadata_source.file_name}",
                    UserWarning,
                )
        else:
            for parameter in ["t090C", "prDM", "sal11"]:
                try:
                    hex2py_data = ctd_data[parameter].data
                    datcnv_data = datcnv_cnv.parameters[parameter].data
                except KeyError:
                    with pytest.warns(UserWarning):
                        warnings.warn(
                            f"Could not compare {parameter}. Not present in file.",
                            UserWarning,
                        )
                    continue

                ds = cast_borders_dict["down_start"]
                de = cast_borders_dict["down_end"] + 1
                de = (
                    de
                    if datcnv_cnv.parameters.full_data_array.shape[1]
                    else -1
                )
                datcnv_data = datcnv_data[ds:de]
                try:
                    if len(hex2py_data) == len(datcnv_data):
                        assert_allclose(
                            hex2py_data,
                            datcnv_data,
                            rtol=0.002,
                        )
                    else:
                        de = len(datcnv_data)
                        assert_allclose(
                            hex2py_data[:de],
                            datcnv_data,
                            rtol=0.002,
                        )
                except AssertionError as error:
                    raise AssertionError(
                        f"Parameter {parameter} in {ctd_data.file_name} failed: {error}"
                    )
        assert True

    def test_cast_borders(self, ctd_data: CTDData):
        cast_borders_dict = ctd_data.cast_borders
        assert (
            ctd_data["prDM"].data.shape[0]
            == cast_borders_dict["down_end"]
            - cast_borders_dict["down_start"]
            + 1
        )

    def test_salinity_update(self, ctd_data):
        try:
            pre_update = ctd_data["sal11"].data
        except KeyError:
            pytest.skip()
        ctd_data["c1mS/cm"].data = np.zeros_like(ctd_data["flag"].data)
        ctd_data.update_salinity()
        try:
            assert_equal(pre_update, ctd_data["sal11"].data)
        except AssertionError:
            assert True
        else:
            assert False

    def test_drop_bad_flags(self, ctd_data):
        flags = ctd_data["flag"]
        original_data_length = flags.data.shape[0]
        random_flags = np.random.choice([False, True], size=flags.data.shape)
        flags.data = random_flags
        ctd_data.drop_flagged_rows()
        assert (
            ctd_data.get_data_length()
            == original_data_length - random_flags.sum()
        )
        assert "flag" not in ctd_data.parameters

    def test_output_column_picking(self, ctd_data):
        test_path = Path(f"column_picking_{ctd_data.file_name}.cnv")
        params, _ = ctd_data.to_cnv(
            test_path,
            output_parameters=[
                "pressure",
                "Density",
                "something_nonexistent",
            ],
        )
        assert len(params) <= 3
        assert len(ctd_data.parameters) > 3
        test_path.unlink()

    def test_reduced_header(self, ctd_data):
        test_path = Path(f"reduced_header_{ctd_data.file_name}.cnv")
        _, file_lines = ctd_data.to_cnv(
            test_path,
            reduced_header=True,
            output_parameters="default",
        )
        assert (
            len([line for line in file_lines if line.startswith(("#", "*"))])
            < 50
        )
        assert len(
            [line for line in file_lines if line.startswith("# name")]
        ) < len(ctd_data.parameters)
        test_path.unlink()

    def test_event_name(self, ctd_data):
        regex_string = r"^([a-z]{1,3}\d{1,3})(_1|-1|_2|-2)?(_\d{1,4}|-\d{1,4})(_\d{1,2}|-\d{1,2})$"
        if ctd_data.event_name:
            assert re.match(regex_string, ctd_data.event_name, flags=re.I)

    @pytest.mark.order(1)
    def test_ctd_hex2netCDF_conversion(self, ctd_data):
        expected_nc_path = ctd_data.path_to_file.with_suffix(".nc")
        if expected_nc_path.exists():
            expected_nc_path.unlink()

        try:
            ctd_data.to_netCDF(file_path=ctd_data.path_to_file)

            assert expected_nc_path.exists(), "netCDF file not created"

            with nc.Dataset(expected_nc_path, "r") as ds:
                expected_vars = ["latitude", "longitude", "timeS", "depth"]
                for var in expected_vars:
                    assert var in ds.variables, (
                        f"variable '{var}' missing in NetCDF."
                    )
                    assert len(ds.variables[var]) > 0, (
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


def test_broken_time_vector():
    # use file with known time gaps
    test_cnv = "M211_A1_2-18.hex"
    test_path = Path(f"broken_time_{test_cnv}").with_suffix(".cnv")
    hex = HexFile(hex_path.joinpath(test_cnv))
    raw_data = hex_reading(hex)
    parameters = Parameters([], [], True)
    gaps = get_time_gaps(raw_data)
    assert len(gaps) > 0
    handle_time(gaps, hex, raw_data.shape[0], parameters)
    gap_sum = sum(gaps.values())
    assert parameters.get_data_length() - gap_sum == raw_data.shape[0]
    CTDData(parameters, hex).to_cnv(test_path)
    test_path.unlink()


@pytest.mark.parametrize(
    ("input_name", "expected_output"),
    [
        ("EMB346_082-01", "EMB346_082-01"),
        ("msm123-011_02", "MSM123_011-02"),
        ("M42-52-1", "M42_052-01"),
        ("So308-2_008_3", "SO308_2_008-03"),
    ],
)
def test_event_name_parsing(input_name, expected_output):
    cruise, station = read_event_name(input_name)
    assert create_event_string(cruise, station) == expected_output
