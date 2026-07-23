import logging
from pathlib import Path

import pytest
from conftest import (
    cnv_path,
)
from numpy.testing import assert_array_equal, assert_equal
import numpy as np
import gsw_xarray

from ctdam.exceptions import MissingParameterError
from ctdam.parser.read_ctd_data import read_cnv
from ctdam.proc.workflow import Workflow

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "file",
    [file for file in cnv_path.glob("*.cnv")],
)
class TestXarrayStructure:
    @pytest.fixture
    def ds(self, file: Path, run_long_tests: bool):
        if (not run_long_tests) and (file.stat().st_size > 5 * 1000000):
            pytest.skip(f"Skipping long cnv: {file}")
        try:
            ds = read_cnv(file)
        except FileNotFoundError as error:
            pytest.skip(str(error))
        else:
            return ds

    def test_cnv_xarray_parsing(self, ds):
        for var in ds.data_vars:
            assert "standard_name" in ds[var].attrs
            if "qc" in var:
                assert "flag_values" in ds[var].attrs
            else:
                assert "units" in ds[var].attrs
        ds.export.to_cnv(
            Path(__file__).parents[2]
            / f"out_test_{Path(ds.attrs['path_to_source_file']).name}"
        )

    def test_workflow_processing(self, ds):
        proc_settings = {
            "modules": {
                "airpressure": {},
                "loop_removal": {},
                "wildedit_geomar": {},
                # "wfilter": {},
                "celltm": {},
                "binavg": {},
            }
        }
        try:
            Workflow(
                ds,
                proc_settings,
            )
        except MissingParameterError:
            pytest.skip()
        for module in list(proc_settings["modules"].keys()):
            if not (
                module == "airpressure"
                and "Air_Pressure" in ds.meta.custom().keys()
            ):
                continue
            logger.error(module)
            assert module.replace("_", "") in list(ds.meta.provenance().keys())
        ds.export.to_cnv(
            Path(__file__).parents[2]
            / f"binavg_{Path(ds.attrs['path_to_source_file']).name}"
        )

    def test_gsw_xarray_workflow_processing(self, ds):
        if not (
            "pressure" in ds.data_vars
            and "conductivity" in ds.data_vars
            and "temperature" in ds.data_vars
            and "longitude" in ds.data_vars
            and "latitude" in ds.data_vars
            and "density" not in ds.data_vars
        ):
            pytest.skip()
        proc_settings = {
            "modules": {
                "SA_from_SP": {},
                "CT_from_t": {},
                "sigma0": {},
            }
        }
        Workflow(
            ds,
            proc_settings,
        )
        assert "sea_water_sigma_t" in ds.data_vars
        try:
            assert_array_equal(
                ds.sea_water_sigma_t.sel(sensor="primary"),
                ds.sea_water_sigma_t.sel(sensor="secondary"),
            )
        except AssertionError:
            assert True
        else:
            assert False

    def test_accessor_processing(self, ds):
        try:
            ds.proc.module("loop_removal")
        except MissingParameterError:
            pytest.skip()
        assert ds.proc.last() == "loopremoval"
        assert ds.flag.sum() == int(
            ds.meta.provenance()["loopremoval"]["bad_rows"].split()[0]
        )

        con = ds.conductivity.copy(deep=True)
        ds.proc.workflow(["celltm"])
        assert ds.proc.last() == "celltm"
        try:
            assert_equal(con, ds.conductivity.data)
        except AssertionError:
            assert True
        else:
            assert False

        if "longitude" in ds.data_vars and "latitude" in ds.data_vars:
            ds["SA"] = ds.gsw.SA_from_SP()
            assert "SA" in ds.data_vars

        oxy = ds.oxygen.copy(deep=True)
        ds.proc.module("alignctd")
        try:
            assert_equal(oxy, ds.oxygen.data)
        except AssertionError:
            assert True
        else:
            assert False

    def test_wfilter(self, ds):
        t = ds.salinity.copy(deep=True)
        ds.proc.module("wfilter")
        try:
            assert_equal(t, ds.salinity.data)
        except AssertionError:
            assert True
        else:
            assert False

        # max_pressure = np.nanmax(ds.pressure)
        # ds.proc.module("binavg")
        # assert len(ds.time) == int(max_pressure) + 1
