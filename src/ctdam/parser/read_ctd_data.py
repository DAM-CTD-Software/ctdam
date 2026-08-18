import importlib.metadata
from datetime import datetime, timezone
from inspect import getmembers, isfunction
from pathlib import Path
from venv import logger

import numpy as np
import pandas as pd
import xarray as xr

from ctdam import PARAMETER_MAPPING, SBS_NAME_MAPPING
from ctdam.conv import raw_conversion
from ctdam.conv.unit_conversion import (
    get_potential_density,
    oxygen_mlperl_to_umolperkg,
    oxygen_umolperl_to_umolperkg,
)
from ctdam.parser.seabird_data_files import CnvFile, HexFile, SeabirdDataFile
from ctdam.parser.sst_ctd_file_parser import sst2xarray


def create_array_coords(raw_file_data: SeabirdDataFile) -> dict:
    """
    Sets the datasets coordinates.

    Parameters
    ----------
    raw_file_data: SeabirdDataFile :
        The raw data source

    Returns
    -------
    A dictionary format for xarray
    """
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
    """
    Sets the datasets attributes.

    Parameters
    ----------
    raw_file_data: SeabirdDataFile :
        The raw data source

    Returns
    -------
    A dictionary format for xarray
    """
    attrs = {}
    # parse to xarray attrs (holds metadata)
    # general metadata
    attrs["start_time"] = str(raw_file_data.start_time)
    attrs["position"] = raw_file_data.start_position
    attrs["cruise"] = raw_file_data.cruise
    attrs["station"] = raw_file_data.event_name
    attrs["path_to_source_file"] = str(raw_file_data.path_to_file.absolute())
    attrs["sample_rate"] = ""
    for line in raw_file_data.data_table_description:
        if line.startswith("interval"):
            unit, value = line.split("=", 1)[1].split(":", 1)
            unit = unit.strip()
            value = float(value.strip())

            if unit == "seconds":
                sample_rate = float(np.round(1 / value))
                if sample_rate == 1:
                    attrs["sample_rate"] = f"{value:g} second"
                else:
                    attrs["sample_rate"] = sample_rate
            elif unit in ("decibars", "db"):
                attrs["sample_rate"] = f"{value:g} dbar"
            break

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


def sorting_parameters(
    sensor_pairs,
    rule=None,
):
    """Returns sorted parameter for conversion."""
    if rule is None:
        rule = [
            "PressureSensor",
            "TemperatureSensor1",
            "TemperatureSensor2",
            "ConductivitySensor1",
            "ConductivitySensor2",
        ]

    out = []

    for name in rule:
        for sensor, raw_data in sensor_pairs:
            if sensor == name:
                out.append((sensor, raw_data))

    for sensor, raw_data in sensor_pairs:
        if sensor not in rule:
            out.append((sensor, raw_data))

    return out


def parse_oxygen_data(
    name: str,
    data: np.ndarray,
    cnv: CnvFile,
) -> np.ndarray:
    """Returns oxygen data in umol/kg"""
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
    """
    Parse Seabird .cnv data to cf-compliant xarray Dataset.

    Parameters
    ----------
    path_to_cnv_file: Path | str :
        The path to the .cnv file
    only_header: bool :
        Whether to only parse the header information

    Returns
    -------
    A cf-compliant xarray Dataset.
    """
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


def build_sensor_pairs(
    hex_file: HexFile,
    coefficients: pd.DataFrame,
) -> list[tuple[str, np.ndarray]]:
    """
    Match XMLCON sensors to their raw HEX channels.

    Channels 1-5 correspond to f0-f4.
    Channels 6-13 correspond to v0-v7.
    """

    sensor_pairs = []

    for sensor_name in coefficients.columns:
        channel_number = int(coefficients[sensor_name]["channel"])

        if 1 <= channel_number <= 5:
            raw_channel = f"f{channel_number - 1}"

        elif 6 <= channel_number <= 13:
            raw_channel = f"v{channel_number - 6}"

        else:
            logger.warning(
                "Unsupported XMLCON channel %s for sensor %s.",
                channel_number,
                sensor_name,
            )
            continue

        if raw_channel not in hex_file.raw_ds:
            logger.warning(
                "Raw channel %s for sensor %s is missing.",
                raw_channel,
                sensor_name,
            )
            continue

        sensor_pairs.append(
            (
                sensor_name,
                hex_file.raw_ds[raw_channel].data.astype(float),
            )
        )

    return sensor_pairs


def read_hex(
    path_to_hex_file: Path | str,
) -> xr.Dataset:
    """
    Parse Seabird .hex data to cf-compliant xarray Dataset.

    Parameters
    ----------
    path_to_cnv_file: Path | str :
        The path to the .hex file

    Returns
    -------
    A cf-compliant xarray Dataset.
    """
    hex_file = HexFile(path_to_hex_file)

    coords = create_array_coords(hex_file)
    attrs = create_array_attrs(hex_file)
    ds = xr.Dataset(
        {},
        coords=coords,
        attrs=attrs,
    )

    if hex_file.xmlcon:
        df = hex_file.xmlcon.coefficients.drop(
            columns=["SPAR_Sensor"], errors="ignore"
        )

        sensor_pairs = build_sensor_pairs(
            hex_file,
            df,
        )

        sensor_pairs = sorting_parameters(sensor_pairs)

        converted = {}
        conv_functions = {
            n: f for n, f in getmembers(raw_conversion, isfunction)
        }

        for sensor, raw_data in sensor_pairs:
            name = sensor.replace("_Sensor", "").replace("Sensor", "").lower()
            name = name[:-1] if name[-1] in ["1", "2"] else name

            # some sensors require name mapping
            name_aliases = {
                "fluorowetlabeco_afl_fl": "fluorescence",
                "turbiditymeter": "turbidity",
            }

            name = name_aliases.get(name, name)

            if name not in PARAMETER_MAPPING:
                continue

            if name not in conv_functions:
                continue

            if name == "temperature":
                converted_data = conv_functions[name](
                    raw_data,
                    df[sensor],
                )

            elif name == "pressure":
                converted_data = conv_functions[name](
                    raw_data,
                    df[sensor],
                    hex_file.raw_ds["ptempC"].data.astype(float),
                )

            elif name == "conductivity":
                if sensor.endswith("1"):
                    temperature = converted["TemperatureSensor1"]
                    salinity_name = "Salinity1"

                else:
                    temperature = converted["TemperatureSensor2"]
                    salinity_name = "Salinity2"

                pressure = converted["PressureSensor"]

                converted_data = conv_functions[name](
                    raw_data,
                    df[sensor],
                    temperature,
                    pressure,
                )

                # saving conductivity
                converted[sensor] = converted_data

                ds.add.parameter(
                    name,
                    converted_data,
                )

                # calculating salinity
                salinity_data = raw_conversion.salinity(
                    converted_data,
                    temperature,
                    pressure,
                )

                converted[salinity_name] = salinity_data

                ds.add.parameter(
                    "salinity",
                    salinity_data,
                )

                continue

            elif name == "oxygen":
                if sensor.endswith("1"):
                    temperature = converted["TemperatureSensor1"]
                    salinity = converted["Salinity1"]

                else:
                    temperature = converted["TemperatureSensor2"]
                    salinity = converted["Salinity2"]

                pressure = converted["PressureSensor"]

                if "time" in hex_file.raw_ds:
                    time = hex_file.raw_ds["time"].data
                else:
                    time = np.arange(len(raw_data), dtype=float)

                converted_data = conv_functions[name](
                    raw_data,
                    df[sensor],
                    temperature,
                    salinity,
                    pressure,
                    time,
                    use_tau_correction=True,
                    use_hysteresis_correction=True,
                )

            else:
                converted_data = conv_functions[name](
                    raw_data,
                    df[sensor],
                )

            # all parameters except for conductivity
            converted[sensor] = converted_data

            ds.add.parameter(
                name,
                converted_data,
            )
        # add provenance information
        timestamp = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
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
    """
    Parse different file types to a cf-compliant xarray Dataset

    Parameters
    ----------
    path_to_ctd_data_file: Path | str :
        The path to the ctd data file

    Returns
    -------
    A cf-compliant xarray Dataset
    """
    data_path = Path(path_to_ctd_data_file)
    suffix = data_path.suffix.lower().lstrip(".")

    if suffix == "cnv":
        return read_cnv(path_to_ctd_data_file)
    elif suffix == "hex":
        return read_hex(path_to_ctd_data_file)
    elif suffix == "tob":
        return sst2xarray(path_to_ctd_data_file)
    else:
        raise IOError(
            f"Unknown file type: '{data_path.suffix}', aborting input parsing."
        )
