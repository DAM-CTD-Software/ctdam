import logging

import numpy as np
import pytest
import xarray as xr
from conftest import (
    assert_different_np_array,
    btl_path,
    cnv_path,
    test_cnv,
)

from ctdam.exceptions import BinnedDataError
from ctdam.parser.read_ctd_data import parse
from ctdam.parser.seabird_data_files import BottleFile
from ctdam.proc.modules import (
    AirPressureCorrection,
    AlignCTD,
    BinAvg,
    CastBorders,
    LoopRemoval,
    WFilter,
)
from ctdam.proc.modules.geomar_wildedit import wildedit_geomar
from ctdam.proc.modules.seabird_functions import CellTM
from ctdam.parser.seabird_data_files import BottleLogFile

logger = logging.getLogger(__name__)


@pytest.fixture
def ds():
    return parse(test_cnv)


def test_alignctd(ds):
    oxy = ds.oxygen.copy(deep=True)
    ds.proc.module("alignctd")
    assert_different_np_array(oxy, ds.oxygen.values, ds)


def test_wildedit_geomar_logic(ds):
    salinity = ds.salinity.sel(sensor="primary")
    new_data, _ = wildedit_geomar(
        data=salinity,
        flag=ds.flag,
        std1=3.0,
        std2=10,
        window_size=50,
    )
    assert_different_np_array(salinity, new_data, ds)


def test_air_pressure_correction(ds):
    old_data = ds.pressure.copy(deep=True)
    new_ds = AirPressureCorrection()(ds=ds)
    pressure_diff = new_ds.meta.provenance["airpressure"][
        "pressure_diff"
    ].split()[0]
    assert float(old_data[0]) + float(pressure_diff) == float(
        new_ds.pressure[0]
    )


def test_airpressure_with_bugged_metadata(ds):
    ds.meta.custom["Air_Pressure"] = "definitely_not_a_number"
    new_ds = AirPressureCorrection()(ds=ds)
    assert isinstance(new_ds, xr.Dataset)


def test_binned_data_error():
    ds = parse(cnv_path / "MSM140_1.cnv")
    with pytest.raises(BinnedDataError):
        AlignCTD()(ds=ds)


def test_bin_avg(ds, create_files):
    bin_variable = "pressure"
    if bin_variable not in ds:
        pytest.skip()
    new_ds = BinAvg()(
        ds=ds,
        arguments={
            "bin_variable": bin_variable,
            "bin_size": 0.1,
        },
    )
    if create_files:
        new_ds.export.to_cnv(f"binavg_{new_ds.attrs['path_to_source_file']}")
    diff = np.diff(new_ds[f"{bin_variable}_bins"].data)
    assert len(diff[np.isclose(diff, 0.1)]) > len(diff) * 0.95
    assert new_ds.access.binned


def test_binavg_linear_interpolation():
    ds = parse(cnv_path / "EMB295_14-1.cnv")
    sparse = BinAvg()(ds)
    dense = BinAvg()(ds, arguments={"linear_interpolation": True})

    assert len(dense.pressure_bins) >= len(sparse.pressure_bins)
    gaps = np.diff(dense.pressure_bins)
    assert np.allclose(gaps, gaps[0])


def test_wfilter(ds, create_files: bool):
    pre_ds = ds.copy(deep=True)
    new_ds = WFilter()(
        ds=ds,
        arguments={
            "tUrB iDIty": {"window_type": "median", "window_width": 10},
            "Temperature": {"window_width": 50},
            "Oxygen": {"half_width": 2, "offset": 5},
            "Conductivity": {
                "window_type": "triangle",
                "window_width": 200,
                "half_width": 3,
                "offset": 3,
            },
        },
    )
    # check for boundary effects
    assert new_ds.pressure[0] > 0.2
    assert ds.access.size == new_ds.access.size
    for param in pre_ds:
        if param not in [
            "pressure",
            "temperature",
            "conductivity",
            "salinity",
            "oxygen",
            "fluorometer",
            "turbidity meter",
            "par",
            "spar",
        ]:
            continue
        if create_files:
            new_ds.export.to_cnv(
                f"wfilter_{new_ds.attrs['path_to_source_file']}"
            )
        assert_different_np_array(
            pre_ds[param].data, new_ds[param].data, new_ds
        )


def test_cell_tm(ds, create_files):
    if not "conductivity" in ds:
        pytest.skip()
    pre_ds = ds.copy(deep=True)
    new_ds = CellTM()(
        ds=ds,
        arguments={},
    )
    if create_files:
        new_ds.export.to_cnv(f"celltm_{new_ds.attrs['path_to_source_file']}")
    assert_different_np_array(
        pre_ds.conductivity.data,
        new_ds.conductivity.data,
        new_ds,
    )


def test_new_loop_flags(ds, create_files):
    pre_ds = ds.copy(deep=True)
    new_ds = LoopRemoval()(
        ds=ds,
        arguments={},
    )
    if create_files:
        new_ds.export.to_cnv(
            f"loopremoval_{new_ds.attrs['path_to_source_file']}"
        )
    assert_different_np_array(pre_ds.flag.data, new_ds.flag.data, new_ds)


def test_time_dependent_loop_removal():

    module = LoopRemoval()
    # strictly increasing — nothing should be flagged
    pressure = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 4.01])
    flags = module.time_dependent_loop_removal(pressure=pressure, delta=0.0)
    assert not flags.any()

    # loop at index 3: should be flagged
    pressure = np.array([0.0, 1.0, 3.0, 2.0, 4.0])
    flags = module.time_dependent_loop_removal(pressure=pressure, delta=0.0)
    assert flags[3]
    assert not flags[[0, 1, 2, 4]].any()


def test_bottle_output_parsing(tmp_path, create_files):
    file_name = "EMB295_14-1.cnv"
    ds = parse(cnv_path / file_name)
    if create_files:
        output_path = btl_path
    else:
        output_path = tmp_path
    ds.export.to_btl(output_path, (btl_path / file_name).with_suffix(".bl"))
    btl = BottleFile((output_path / file_name).with_suffix(".btl"))
    assert btl.start_time
    assert btl.start_position
    assert btl.df.shape[0] == 4 * 7


def test_cast_borders_module(ds):

    result = CastBorders()(ds=ds, arguments={})

    assert "castborders" in result.meta.provenance.keys()
    assert "down_start" in result.meta.provenance["castborders"]
    assert "down_end" in result.meta.provenance["castborders"]
    assert (
        result.meta.provenance["castborders"]["down_start"]
        < result.meta.provenance["castborders"]["down_end"]
    )


def test_bottles_after_cast_border_crop():
    file_name = "EMB295_14-1.cnv"
    bl_file = (btl_path / file_name).with_suffix(".bl")

    ds = read_ctd_data(cnv_path / file_name)

    ds.add.bottles(bl_file=BottleLogFile(bl_file))

    cropped = CastBorders()(
        ds=ds.drop_vars("bottle_info"), arguments={"crop": True}
    )

    cropped.add.bottles(bl_file=BottleLogFile(bl_file))

    for bottle in np.unique(
        cropped.bottle_info.values[cropped.bottle_info.values != 0]
    ):
        original_scans = ds.scan.values[ds.bottle_info.values == bottle]

        cropped_scans = cropped.scan.values[
            cropped.bottle_info.values == bottle
        ]

        assert np.array_equal(
            cropped_scans,
            original_scans[
                np.isin(
                    original_scans,
                    cropped.scan.values,
                )
            ],
        )
