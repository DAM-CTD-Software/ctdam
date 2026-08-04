import importlib.metadata
import logging
from datetime import datetime, timezone
from inspect import getmembers, isfunction
from pathlib import Path

import numpy as np
import xarray as xr

import ctdam.parser.custom_xarray_accessors
from ctdam import PARAMETER_MAPPING, SBS_NAME_MAPPING
from ctdam.conv import raw_conversion
from ctdam.conv.unit_conversion import (
    get_potential_density,
    oxygen_mlperl_to_umolperkg,
    oxygen_umolperl_to_umolperkg,
)
from ctdam.parser.seabird_data_files import CnvFile, HexFile, SeabirdDataFile

logger = logging.getLogger(__name__)


def create_array_coords(raw_file_data: SeabirdDataFile) -> dict:
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

    return coords


def create_array_attrs(raw_file_data: SeabirdDataFile) -> dict:
    attrs = {}
    # parse to xarray attrs (holds metadata)
    # general metadata
    attrs["start_time"] = raw_file_data.start_time
    attrs["position"] = raw_file_data.start_position
    attrs["cruise"] = raw_file_data.cruise
    attrs["station"] = raw_file_data.event_name
    attrs["path_to_source_file"] = raw_file_data.path_to_file.absolute()
    attrs["sample_rate"] = ""

    # instrument metadata
    attrs["instrument_metadata"] = "".join(raw_file_data.instrument_metadata)
    # custom metadata
    attrs["custom_metadata"] = "".join(raw_file_data.custom_metadata)
    # sensor metadata
    attrs["sensor_metadata"] = "".join(raw_file_data.sensor_metadata)
    # data provenance metadata
    try:
        attrs["provenance_metadata"] = "".join(
            raw_file_data.processing_history[:-1]
        )
    except KeyError:
        attrs["provenance_metadata"] = ""

    return attrs


def parse_oxygen_data(
    name: str,
    data: np.ndarray,
    cnv: CnvFile,
) -> np.ndarray:
    if "0" in name:
        practical_salinity = "sal00"
        temperature = "t090C"
    else:
        practical_salinity = "sal11"
        temperature = "t190C"
    pressure = "prDM"

    try:
        potential_density = get_potential_density(
            practical_salinity=cnv.data[practical_salinity],
            temperature=cnv.data[temperature],
            pressure=cnv.data[pressure],
            longitude=cnv.start_position[1],
            latitude=cnv.start_position[0],
        )
    except KeyError:
        return np.ndarray([])

    if name in ["sbeox0Mm/L", "sbeox1Mm/L"]:
        umolperkg_oxygen = oxygen_umolperl_to_umolperkg(
            data, potential_density
        )
    elif name in ["sbeox0ML/L", "sbeox1ML/L"]:
        umolperkg_oxygen = oxygen_mlperl_to_umolperkg(data, potential_density)

    else:
        umolperkg_oxygen = np.ndarray([])

    return umolperkg_oxygen


def read_cnv(
    path_to_cnv_file: Path | str,
    only_header: bool = False,
) -> xr.Dataset:
    raw_file_data = CnvFile(path_to_cnv_file, only_header)

    coords = create_array_coords(raw_file_data)
    attrs = create_array_attrs(raw_file_data)
    ds = xr.Dataset(
        {},
        coords=coords,
        attrs=attrs,
    )

    for name, data in raw_file_data.data.items():
        try:
            basic_name = SBS_NAME_MAPPING[name]["base"]
        except KeyError:
            continue
        # handle heterogenous oxygen units
        if basic_name == "oxygen":
            # check whether not in cf output format
            if not name in ["sbox0Mm/Kg", "sbox1Mm/Kg"]:
                # differentiate primary and secondary sensor
                target = "sbox0Mm/Kg" if "0" in name else "sbox1Mm/Kg"
                if not target in raw_file_data.data.keys():
                    data = parse_oxygen_data(name, data, raw_file_data)
                    if data.size == 1:
                        continue
                else:
                    continue
        ds.add.parameter(basic_name, data)
    return ds


def read_hex(
    path_to_hex_file: Path | str,
) -> xr.Dataset:
    hex_file = HexFile(path_to_hex_file)

    coords = create_array_coords(hex_file)
    attrs = create_array_attrs(hex_file)
    # raw data version as fall back
    ds = xr.Dataset(
        hex_file.raw_ds.data_vars,
        coords=coords,
        attrs=attrs,
    )

    if hex_file.xmlcon:
        df = hex_file.xmlcon.coefficients
        sensor_data = [
            hex_file.raw_ds[v].data.astype(float)
            for v in hex_file.raw_ds.data_vars
            if v.startswith(("f", "v"))
        ]
        if len(df.columns) == len(sensor_data):
            # drop placeholder raw data
            ds = ds.drop_vars(lambda x: x.data_vars)
            for sensor, raw_data in zip(df.columns, sensor_data):
                name = (
                    sensor.replace("_Sensor", "").replace("Sensor", "").lower()
                )
                name = name[:-1] if name[-1] in ["1", "2"] else name
                if not name in PARAMETER_MAPPING:
                    continue
                conv_functions = {
                    n: f for n, f in getmembers(raw_conversion, isfunction)
                }
                if not name in conv_functions:
                    continue
                converted_data = conv_functions[name](raw_data, df[sensor])
                ds.add.parameter(name, converted_data)
            # add provenance information
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y.%m.%d %H:%M:%S"
            )
            try:
                version = f", v{importlib.metadata.version('ctdam')}"
            except Exception:
                version = ""
            ds.add.processing_metadata(
                module="hex2py",
                key="metainfo",
                value=f"{timestamp}, ctdam python package{version}",
            )
            if hex_file.gaps:
                ds.add.processing_metadata(
                    module="hex2py",
                    key="time_correction",
                    value=", ".join(
                        [
                            f"{str(key)}: {str(value)}"
                            for key, value in hex_file.gaps.items()
                        ]
                    ),
                )

    return ds


def read_ctd_data(path_to_ctd_data_file: Path | str) -> xr.Dataset:
    data_path = Path(path_to_ctd_data_file)
    suffix = data_path.suffix.lower().lstrip(".")

    if suffix == "cnv":
        return read_cnv(path_to_ctd_data_file)
    elif suffix == "hex":
        return read_hex(path_to_ctd_data_file)
    # TODO: implement these
    # elif suffix == "tob":
    #     pass
    # elif suffix == "ctd":
    #     pass
    else:
        raise IOError(
            f"Unknown file type: '{data_path.suffix}', aborting input parsing."
        )
