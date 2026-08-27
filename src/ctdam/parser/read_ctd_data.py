import logging
import re
import warnings
from datetime import datetime
from inspect import getmembers, isfunction
from pathlib import Path

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
from ctdam.utils import coordinates_to_float

logger = logging.getLogger(__name__)


def create_array_coords(
    raw_file_data: SeabirdDataFile,
    data_length: int = 0,
) -> dict:
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
    if data_length:
        coords["scan"] = (("scan",), np.arange(data_length))
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
        if not data_length:
            coords["scan"] = (
                ("scan",),
                np.arange(len(raw_file_data.unixtime)),
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
    downcast_only: bool = True,
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
        ds.add.processing_metadata(module="hex2py")
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

    if downcast_only:
        from ctdam.proc.modules.detect_cast_borders import CastBorders

        ds = CastBorders()(
            ds=ds,
            arguments={
                "crop": True,
            },
        )

    return ds


def sst2xarray(input_path: Path | str, delimiter: str = " ") -> xr.Dataset:
    """
    Read CTD data from an SST .TOB data file and create an Xarray Dataset.

    Parses SST .TOB files directly into a common Xarray structure with:
    - "scan" dimension for each measurement row
    - Data variables incl. metadata
    - Provenance and common metadata tracking

    Based on a MATLAB script written by Johanna Grote and Jens Faber.

    Parameters
    ----------
    input_path : Path | str
        The path to the .TOB file
    delimiter : str, optional
        The data file delimiter (default: " ")

    Returns
    -------
    A cf-compliant xarray Dataset
    """

    mapping = {
        "press": "pressure",
        "temp": "temperature",
        "cond": "conductivity",
        "do_ml": "oxygen",
        "salin": "salinity",
        "intd": "timeU",
        "long": "longitude",
        "lat": "latitude",
    }

    nr_hl = 0  # total header lines
    nr_simi = 0  # semicolon-only line counter
    nr_dl = 0  # number of data lines
    sst_ids = []

    with Path(input_path).open("r", encoding="latin-1") as fileID:
        while nr_simi < 4:
            rline = fileID.readline()
            if not rline:
                break
            rline = rline.rstrip("\n").rstrip("\r")

            if rline and rline[0] == ";":
                nr_simi += 1

            if "Lines :" in rline:
                colon_pos = rline.index(":")
                nr_dl = int(float(rline[colon_pos + 1 :].strip()))

            elif nr_simi == 2:
                parts = rline.split(delimiter)
                sst_ids = [p for p in parts if p not in (";", " ", "", "\t")]
                output_data = np.full((nr_dl, len(sst_ids)), np.nan)

            nr_hl += 1

        # Read raw data (after header)
        fileID.seek(0)
        for _ in range(nr_hl):
            fileID.readline()

        raw_rows = []
        for line in fileID:
            line = line.rstrip("\n").rstrip("\r")
            tokens = [t for t in line.split(delimiter) if t != ""]
            if tokens:
                raw_rows.append(tokens)

    # Build raw_data as list-of-lists indexed [row][col]
    # Pad / trim rows to n_vars
    raw_data = []
    for row in raw_rows:
        if len(row) >= len(sst_ids):
            raw_data.append(row[: len(sst_ids)])

    n_vars = len(sst_ids)

    # Detect date / time columns and fill data array
    time_ind = None
    date_ind = None
    date_format = None

    last_row = raw_data[-1] if raw_data else [""] * n_vars

    for ind in range(n_vars):
        cell = last_row[ind] if ind < len(last_row) else ""

        if re.search(r"\d{2}:\d{2}:\d{2}", cell):
            time_ind = ind
        elif re.search(r"\d{2}/\d{2}/\d{4}", cell):
            date_ind = ind
            date_format = "Typ_1"
        elif re.search(r"\d{2}\.\d{2}\.\d{4}", cell):
            date_ind = ind
            date_format = "Typ_2"
        elif re.search(r"\d{2}-\d{2}-\d{4}", cell):
            date_ind = ind
            date_format = "Typ_3"
        elif re.search(r"\d{4}-\d{2}-\d{2}", cell):
            date_ind = ind
            date_format = "Typ_4"
        elif cell[-1] in ("N", "S", "E", "W"):
            try:
                output_data[:, ind] = np.full(
                    nr_dl, coordinates_to_float(cell)
                )
            except ValueError:
                pass

        else:
            col_vals = []
            for row in raw_data:
                try:
                    col_vals.append(
                        float(row[ind]) if ind < len(row) else np.nan
                    )
                except (ValueError, IndexError):
                    col_vals.append(np.nan)
            output_data[: len(col_vals), ind] = col_vals

    # Combine date + time into a unix timestamp
    fmt_map = {
        "Typ_1": ("%d/%m/%Y", "%H:%M:%S"),
        "Typ_2": ("%d.%m.%Y", "%H:%M:%S"),
        "Typ_3": ("%d-%m-%Y", "%H:%M:%S"),
        "Typ_4": ("%Y-%m-%d", "%H:%M:%S"),
    }

    if date_ind is not None:
        dates = [
            row[date_ind] if date_ind < len(row) else "00/00/0000"
            for row in raw_data
        ]
    else:
        dates = ["00/00/0000"] * nr_dl
        warnings.warn("No date in exported data, times will be corrupt")

    if time_ind is not None:
        date_fmt, time_fmt = fmt_map[date_format]
        combined_fmt = date_fmt + time_fmt

        serial_times = []
        for i, row in enumerate(raw_data):
            date_str = dates[i]
            time_str = row[time_ind] if time_ind < len(row) else "00:00:00"
            try:
                dt = datetime.strptime(date_str + time_str, combined_fmt)
                serial_times.append(dt.timestamp())
            except ValueError:
                serial_times.append(np.nan)

        output_data[: len(serial_times), time_ind] = serial_times
    else:
        warnings.warn("No time given in data set")

    # Drop the separate date column (its info is merged into the time column)
    if date_ind is not None and time_ind is not None:
        output_data = np.delete(output_data, date_ind, axis=1)
        del sst_ids[date_ind]

    output_data = np.array(output_data).T
    data_vars = {}

    scan_index = np.arange(len(output_data[0]))

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "scan": scan_index,
        },
    )

    _add_parameters(output_data, sst_ids, mapping, ds, logger)
    _add_metadata(ds, input_path, date_format)
    return ds


def _add_parameters(output_data, sst_ids, mapping, ds, logger):
    """Add parameters, coordinates, and position attributes to dataset."""
    position = [None, None]

    for array, sst_name in zip(output_data, sst_ids):
        try:
            parameter_name = mapping[sst_name.lower()]

            # Add parameter (skip latitude/longitude)
            if parameter_name not in ("latitude", "longitude"):
                ds.add.parameter(parameter_name, array)

            # Handle time coordinate
            if parameter_name == "timeU":
                ds.coords["time"] = array
                ds.attrs["start_time"] = array[0]

            # Extract position
            if parameter_name == "latitude":
                position[0] = float(array[0])
            elif parameter_name == "longitude":
                position[1] = float(array[0])

        except KeyError:
            logger.debug(f"{sst_name} had no successful mapping.")

    ds.attrs["position"] = tuple(position)
    ds.add.parameter("flag", np.zeros(len(output_data[0])))


def _add_metadata(ds, input_path, date_format):
    """Add metadata to dataset."""
    ds.attrs["provenance_metadata"] = ""

    ds.add.processing_metadata(
        module="sst_parser",
        key="source_file",
        value=str(input_path),
    )

    if date_format is not None:
        ds.add.processing_metadata(
            module="sst_parser",
            key="date_format_detected",
            value=date_format,
        )

    # Initialize mostly empty metadata fields
    metadata_fields = {
        "cruise": "",
        "station": "",
        "path_to_source_file": str(input_path),
        "sample_rate": "",
        "instrument_metadata": "",
        "custom_metadata": "",
        "sensor_metadata": "",
    }

    for key, value in metadata_fields.items():
        ds.attrs[key] = value


def parse(file_path: Path | str) -> xr.Dataset:
    """
    Parse different file types to a cf-compliant xarray Dataset.

    Can handle Seabirds .cnv and .hex file formats and Sea&Suns
    .TOB file format.

    Parameters
    ----------
    file_path: Path | str :
        The path to the ctd data file

    Returns
    -------
    A cf-compliant xarray Dataset
    """
    data_path = Path(file_path)
    suffix = data_path.suffix.lower().lstrip(".")

    if suffix == "cnv":
        return read_cnv(file_path)
    elif suffix == "hex":
        return read_hex(file_path)
    elif suffix == "tob":
        return sst2xarray(file_path)
    else:
        raise IOError(
            f"Unknown file type: '{data_path.suffix}', aborting input parsing."
        )
