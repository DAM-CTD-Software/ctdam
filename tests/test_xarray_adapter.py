from pathlib import Path

import numpy as np
import xarray as xr

from ctdam.parser.cnvfile import CnvFile
from ctdam.parser.ctddata import CTDData
from ctdam.parser.quality_flags import SeaDataNetFlag
from ctdam.parser.xarray_adapter import ctddata_to_xarray


FIXTURE_CNV = Path("sbs_data/cnv/EMB295_14-1.cnv")


def load_ctddata() -> CTDData:
    cnv = CnvFile(FIXTURE_CNV)
    return CTDData(cnv.parameters, cnv)


def test_ctddata_to_xarray_returns_dataset():
    ctd_data = load_ctddata()

    ds = ctddata_to_xarray(ctd_data)

    assert isinstance(ds, xr.Dataset)
    assert "scan" in ds.dims
    assert ds.sizes["scan"] == 7195


def test_ctddata_to_xarray_contains_existing_ctdam_parameters():
    ctd_data = load_ctddata()

    ds = ctddata_to_xarray(ctd_data)

    assert "prDM" in ds
    assert "t090C" in ds
    assert "t190C" in ds
    assert "sal00" in ds
    assert "sal11" in ds
    assert "depSM" in ds
    assert "flag" in ds


def test_ctddata_to_xarray_preserves_metadata_attrs():
    ctd_data = load_ctddata()

    ds = ctddata_to_xarray(ctd_data)

    assert ds["t090C"].attrs["shortname"] == "t090C"
    assert "unit" in ds["t090C"].attrs
    assert "source_name" in ds["t090C"].attrs


def test_ctddata_to_xarray_does_not_add_flags_when_missing():
    ctd_data = load_ctddata()

    ds = ctddata_to_xarray(ctd_data)

    assert "t090C_flag" not in ds
    assert "t090C_flag_history" not in ds


def test_ctddata_to_xarray_exports_flags_when_present():
    ctd_data = load_ctddata()

    ctd_data["t090C"].initialize_flags()

    mask = np.zeros_like(ctd_data["t090C"].data, dtype=bool)
    mask[0] = True

    ctd_data["t090C"].update_flags(
        mask=mask,
        new_flag=SeaDataNetFlag.BAD,
        test_name="manual_test",
        reason="first value test",
    )

    ds = ctddata_to_xarray(ctd_data)

    assert "t090C_flag" in ds
    assert "t090C_flag_history" in ds

    assert ds["t090C_flag"].dims == ("scan",)
    assert ds["t090C_flag_history"].dims == ("scan",)

    assert ds["t090C_flag"].values[0] == int(SeaDataNetFlag.BAD)
    assert np.all(ds["t090C_flag"].values[1:] == int(SeaDataNetFlag.NO_QC))

    assert "test=manual_test" in ds["t090C_flag_history"].values[0]
    assert "reason=first value test" in ds["t090C_flag_history"].values[0]


def test_ctddata_to_xarray_can_exclude_flags():
    ctd_data = load_ctddata()

    ctd_data["t090C"].initialize_flags()

    ds = ctddata_to_xarray(ctd_data, include_flags=False)

    assert "t090C" in ds
    assert "t090C_flag" not in ds
    assert "t090C_flag_history" not in ds