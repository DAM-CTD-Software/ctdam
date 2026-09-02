import logging
from pathlib import Path

import pytest
from conftest import assert_different_np_array, btl_path, cnv_path

from ctdam.exceptions import BinnedDataError, MissingParameterError
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


def test_temperature_uncertainty(ds):
    if "temperature" not in ds:
        pytest.skip("Dataset has no temperature parameter.")

    assert ds.uncertainty.get("temperature") == 0.001

    ds.uncertainty.set("temperature", 0.002)
    assert ds["temperature"].attrs["uncertainty"] == 0.002

def test_conductivity_uncertainty(ds):
    if "conductivity" not in ds:
        pytest.skip("Dataset has no conductivity parameter.")

    assert ds.uncertainty.get("conductivity") == 0.003


def test_workflow_processing(ds, create_files, tmp_path):
    proc_settings = {
        "modules": {
            "cast_borders": {},
            "airpressure": {},
            "loopremoval": {},
            "wildedit": {},
            "wfilter": {},
            "celltm": {},
            "bottlefile": {"bl_path": btl_path, "output_path": tmp_path},
            "binavg": {},
        }
    }
    try:
        wf = Workflow(
            ds,
            proc_settings,
        )
        ds = wf.output
    except (MissingParameterError, BinnedDataError):
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
        ds.proc.module("loopremoval")
    except (MissingParameterError, BinnedDataError):
        pytest.skip("Missing pressure.")
    assert ds.proc.last == "loopremoval"
    assert ds.flag.sum() == int(
        ds.meta.provenance["loopremoval"]["bad_rows"].split()[0]
    )

    con = ds.conductivity.copy(deep=True)
    ds.proc.workflow(["celltm"])
    assert ds.proc.last == "celltm"
    assert_different_np_array(con, ds.conductivity.data, ds)

    if "longitude" in ds.data_vars and "latitude" in ds.data_vars:
        ds["SA"] = ds.gsw.SA_from_SP()
        assert "SA" in ds.data_vars


def test_wfilter(ds):
    try:
        t = ds.salinity.copy(deep=True)
    except AttributeError:
        pytest.skip(f"No salinity in {ds.attrs['path_to_source_file']}")
    ds.proc.module("wfilter")
    assert_different_np_array(t, ds.salinity.data, ds)


def test_bottle_info_parsing():
    test_file = "EMB295_14-1.cnv"
    cnv = cnv_path / test_file
    bl = (btl_path / test_file).with_suffix(".bl")
    ds = read_cnv(cnv)
    ds.add.bottles(bl)
    btl_info = ds.access.btl_info
    assert btl_info.bottle_info.size == 7


def test_sample_rate_accessor():
    ds = read_cnv(cnv_path / "EMB295_14-1.cnv")
    assert ds.access.sample_rate == 24

    binned_ds = read_cnv(cnv_path / "EMB394_006-01_CTD_0006_1m.cnv")
    assert binned_ds.access.sample_rate == 1
    assert binned_ds.access.bin_unit == "dbar"

    ds.attrs["sample_rate"] = "1 second"
    assert ds.access.sample_rate == 1
    assert ds.access.bin_unit == "second"
