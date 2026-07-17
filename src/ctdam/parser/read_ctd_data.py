import logging
from pathlib import Path

import numpy as np
import xarray as xr

import ctdam.parser.custom_xarray_accessors
from ctdam import PARAMETER_MAPPING, SBS_NAME_MAPPING
from ctdam.parser.seabird_data_files import CnvFile

logger = logging.getLogger(__name__)


def read_cnv(
    path_to_cnv_file: Path | str,
    only_header: bool = False,
) -> xr.Dataset:
    raw_file_data = CnvFile(path_to_cnv_file, only_header)

    # parse to xarray data_vars
    cf_xarray_data = {}

    for name, data in raw_file_data.data.items():
        try:
            basic_name = SBS_NAME_MAPPING[name]["base"]
        except KeyError:
            continue
        if basic_name == "oxygen":
            continue
        cf_name = SBS_NAME_MAPPING[name]["cf"]
        ancillary_variable_name = f"{basic_name}_qc"
        if basic_name in cf_xarray_data.keys():
            try:
                data = np.stack([cf_xarray_data[basic_name][1], data], axis=-1)
                dims = ("scan", "sensor")
                ancillary_variable = np.zeros((len(data), 2), dtype="i1")
            except (ValueError, IndexError):
                logger.error(
                    f"Could not combine {basic_name} data: {cf_xarray_data[basic_name][1]} and {data}"
                )
                print(cf_xarray_data[basic_name])
                dims = ("scan",)
                ancillary_variable = np.zeros((len(data)), dtype="i1")
        else:
            dims = ("scan",)
            ancillary_variable = np.zeros((len(data)), dtype="i1")

        cf_xarray_data[basic_name] = (
            dims,
            data,
            {
                "standard_name": cf_name,
                "units": PARAMETER_MAPPING[basic_name]["cf"]["unit"],
                "ancillary_variables": ancillary_variable_name,
            },
        )

        cf_xarray_data[ancillary_variable_name] = (
            dims,
            ancillary_variable,
            {
                "standard_name": "status_flag",
                "flag_values": np.array([0, 1, 2, 3, 4, 9], dtype="i1"),
                "flag_meanings": "no_qc good_data probably_good_data probably_bad_data bad_data missing_value",
            },
        )

    # parse to xarray coords
    coords = {
        "sensor": ("sensor", ["primary", "secondary"]),
    }
    if raw_file_data.unixtime.size > 1:
        coords["time"] = (
            ("scan",),
            raw_file_data.unixtime,
            {
                "units": "seconds since 1970-01-01 00:00:00",
                "calendar": "standard",
                "standard_name": "time",
            },
        )
    logger.error(raw_file_data.unixtime)

    attrs = {}
    # parse to xarray attrs (holds metadata)
    # general metadata
    attrs["start_time"] = raw_file_data.start_time
    attrs["position"] = raw_file_data.start_position
    attrs["cruise"] = raw_file_data.cruise
    attrs["station"] = raw_file_data.event_name
    attrs["path_to_source_file"] = raw_file_data.path_to_file
    attrs["sample_rate"] = ""

    # instrument metadata
    attrs["instrument_metadata"] = "".join(raw_file_data.instrument_metadata)
    # custom metadata
    # for key, value in raw_file_data.metadata.items():
    #     attrs[f"custom_{key.strip()}"] = value.strip()
    attrs["custom_metadata"] = "".join(raw_file_data.custom_metadata)
    # sensor metadata
    attrs["sensor_metadata"] = "".join(raw_file_data.sensor_metadata)
    # data provenance metadata
    attrs["provenance_metadata"] = "".join(raw_file_data.processing_history)

    ds = xr.Dataset(
        cf_xarray_data,
        coords=coords,
        attrs=attrs,
    )

    return ds


def read_ctd_data(path_to_ctd_data_file: Path | str) -> xr.Dataset:
    data_path = Path(path_to_ctd_data_file)
    suffix = data_path.suffix.lower().lstrip(".")

    if suffix == "cnv":
        return read_cnv(path_to_ctd_data_file)
    # TODO: implement these
    # elif suffix == "hex":
    #     pass
    # elif suffix == "tob":
    #     pass
    # elif suffix == "ctd":
    #     pass
    else:
        raise IOError(
            f"Unknown file type: '{data_path.suffix}', aborting input parsing."
        )
