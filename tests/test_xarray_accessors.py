import logging
from pathlib import Path

import gsw_xarray
import pytest
from conftest import btl_path, cnv_path
from numpy.testing import assert_equal

from ctdam.exceptions import MissingParameterError
from ctdam.parser.read_ctd_data import read_cnv
from ctdam.proc.workflow import Workflow

logger = logging.getLogger(__name__)


def test_cnv_xarray_parsing(ds, create_files):
    for var in ds.data_vars:
        assert "standard_name" in ds[var].attrs
        if "qc" in var:
            assert "flag_values" in ds[var].attrs
        else:
            assert "units" in ds[var].attrs
    file_path = (
        cnv_path / f"out_test_{Path(ds.attrs['path_to_source_file']).name}"
    )
    ds.export.to_cnv(file_path)
    assert read_cnv(file_path) == ds
    if not create_files:
        file_path.unlink()


def test_workflow_processing(ds, create_files):
    proc_settings = {
        "modules": {
            "airpressure": {},
            "loop_removal": {},
            "wildedit_geomar": {},
            "wfilter": {},
            "celltm": {},
            "binavg": {},
        }
    }
    try:
        wf = Workflow(
            ds,
            proc_settings,
        )
        ds = wf.output
    except MissingParameterError:
        pytest.skip("Missing a mandatory parameter.")
    for module in list(proc_settings["modules"].keys()):
        if module == "airpressure":
            if not "Air_Pressure" in ds.meta.custom.keys():
                continue
        assert module.replace("_", "") in list(ds.meta.provenance.keys())
    if create_files:
        ds.export.to_cnv(
            cnv_path / f"binavg_{Path(ds.attrs['path_to_source_file']).name}"
        )


def test_accessor_processing(ds):
    try:
        ds.proc.module("loop_removal")
    except MissingParameterError:
        pytest.skip("Missing pressure.")
    assert ds.proc.last == "loopremoval"
    assert ds.flag.sum() == int(
        ds.meta.provenance["loopremoval"]["bad_rows"].split()[0]
    )

    con = ds.conductivity.copy(deep=True)
    ds.proc.workflow(["celltm"])
    assert ds.proc.last == "celltm"
    try:
        assert_equal(con, ds.conductivity.data)
    except AssertionError:
        assert True
    else:
        assert False

    if "longitude" in ds.data_vars and "latitude" in ds.data_vars:
        ds["SA"] = ds.gsw.SA_from_SP()
        assert "SA" in ds.data_vars


@pytest.mark.xfail(reason="Debug module calling")
def test_wfilter(ds):
    t = ds.salinity.copy(deep=True)
    ds.proc.module("wfilter")
    try:
        assert_equal(t, ds.salinity.data)
    except AssertionError:
        assert True
    else:
        assert False


def test_bottle_info_parsing():
    test_file = "EMB295_14-1.cnv"
    cnv = cnv_path / test_file
    bl = (btl_path / test_file).with_suffix(".bl")
    ds = read_cnv(cnv)
    ds.add.bottles(bl)
    btl_info = ds.access.btl_info
    assert btl_info.bottle_info.size == 7
