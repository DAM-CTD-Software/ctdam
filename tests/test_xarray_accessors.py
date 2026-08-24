import logging
from pathlib import Path

import pytest
import xarray as xr
import numpy as np
from conftest import assert_different_np_array, btl_path, cnv_path
from xarray.testing import assert_identical

from ctdam.exceptions import BinnedDataError, MissingParameterError
from ctdam.parser.read_ctd_data import read_cnv
from ctdam.parser.seabird_data_files import CnvFile
from ctdam.proc.workflow import Workflow
from ctdam.qc.range_checks import apply_range_check_to_parameter
from ctdam.qc.spike_checks import apply_spike_check_to_parameter

logger = logging.getLogger(__name__)


def test_cnv_to_xarray_method(tmp_path):
    path = tmp_path / "EMB356_11-1.cnv"
    path.write_bytes((cnv_path / path.name).read_bytes())

    cnv = CnvFile(path)
    expected = read_cnv(path)

    path.unlink()
    actual = cnv.xarray()

    assert_identical(actual, expected)


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


def test_range_check_xarray():
    temperature = xr.DataArray(
        [
            [10.0, 11.0],
            [60.0, float("nan")],
            [-3.0, 15.0],
        ],
        dims=("scan", "sensor"),
        coords={"sensor": ["primary", "secondary"]},
        name="temperature",
    )

    flags = apply_range_check_to_parameter(temperature)

    assert flags.values.tolist() == [
        [2, 2],
        [4, 9],
        [4, 2],
    ]


def test_range_check_accessor():
    ds = xr.Dataset(
        {
            "temperature": xr.DataArray(
                [
                    [10.0, 11.0],
                    [60.0, float("nan")],
                    [-3.0, 15.0],
                ],
                dims=("scan", "sensor"),
                coords={"sensor": ["primary", "secondary"]},
                attrs={"ancillary_variables": "temperature_qc"},
            ),
            "temperature_qc": xr.DataArray(
                [[0, 0], [0, 0], [0, 0]],
                dims=("scan", "sensor"),
                coords={"sensor": ["primary", "secondary"]},
                attrs={"standard_name": "status_flag"},
            ),
        }
    )

    ds.qc.range_check("temperature")

    assert ds.temperature_qc.values.tolist() == [
        [2, 2],
        [4, 9],
        [4, 2],
    ]

    assert ds.temperature_qc.attrs["standard_name"] == "status_flag"


def test_spike_check_xarray():
    temperature = xr.DataArray(
        [
            [10.0, 10.0],
            [20.0, 10.1],
            [10.0, 10.2],
        ],
        dims=("scan", "sensor"),
        coords={"sensor": ["primary", "secondary"]},
        name="temperature",
    )

    flags = apply_spike_check_to_parameter(temperature)

    assert flags.values.tolist() == [
        [0, 0],
        [3, 2],
        [0, 0],
    ]


def test_spike_check_accessor():
    ds = xr.Dataset(
        {
            "temperature": xr.DataArray(
                [
                    [10.0, 10.0],
                    [20.0, 10.1],
                    [10.0, 10.2],
                ],
                dims=("scan", "sensor"),
                coords={"sensor": ["primary", "secondary"]},
                attrs={"ancillary_variables": "temperature_qc"},
            ),
            "temperature_qc": xr.DataArray(
                [
                    [0, 0],
                    [4, 0],
                    [0, 0],
                ],
                dims=("scan", "sensor"),
                coords={"sensor": ["primary", "secondary"]},
                attrs={"standard_name": "status_flag"},
            ),
        }
    )

    ds.qc.spike_check("temperature")

    assert ds.temperature_qc.values.tolist() == [
        [0, 0],
        [4, 2],
        [0, 0],
    ]


def test_qc_checks_run_on_parameter_creation():
    ds = xr.Dataset()

    ds.add.parameter(
        "temperature",
        np.array([10.0, 60.0, 10.0]),
    )

    assert ds.temperature_qc.values.tolist() == [2, 4, 2]
