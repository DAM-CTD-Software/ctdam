import importlib.metadata
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from seabirdscientific import instrument_data as sbs_id

from ctdam.conv.cast_borders import get_cast_borders
from ctdam.conv.parameter_mapping import ParameterMapping
from ctdam.parser.ctddata import CTDData
from ctdam.parser.hexfile import HexFile
from ctdam.parser.parameter import Parameters
from ctdam.parser.processing_steps import CnvProcessingSteps
from ctdam.parser.xmlfiles import XMLCONFile

logger = logging.getLogger(__name__)


def hex_reading(hex: HexFile) -> pd.DataFrame:
    """
    Converts raw data from a .hex file to structured raw data.

    These can then be converted to physical values with calibration
    coefficients.


    Parameters
    ----------
    hex: HexFile
        Input .hex file to read raw CTD data from

    Returns
    -------
    A pandas DataFrame that holds structured sensor raw data.
    """
    instrument_info = hex.xmlcon["SBE_InstrumentConfiguration"]["Instrument"]
    instrument_name = instrument_info["Name"]
    # TODO: extend this
    device_mapping = {"SBE 911plus": sbs_id.InstrumentType.SBE911Plus}
    try:
        for device in device_mapping.keys():
            if instrument_name.startswith(device):
                instrument_type = device_mapping[device]
        assert instrument_type

    except Exception:
        sys.exit(f"Unknown instrument: {instrument_name}. Aborting.")
    enabled_sensors = []

    sensor_info = hex.xmlcon.sensor_info
    sensor_names = [s["SensorName"] for s in sensor_info]
    if "Temperature" in sensor_names:
        enabled_sensors.append(sbs_id.Sensors.Temperature)
    if "Conductivity" in sensor_names:
        enabled_sensors.append(sbs_id.Sensors.Conductivity)
    if "Pressure" in sensor_names:
        enabled_sensors.append(sbs_id.Sensors.Pressure)
    if "Temperature2" in sensor_names:
        enabled_sensors.append(sbs_id.Sensors.SecondaryTemperature)
    if "Conductivity2" in sensor_names:
        enabled_sensors.append(sbs_id.Sensors.SecondaryConductivity)

    voltage_sensors = [
        sbs_id.Sensors.ExtVolt0,
        sbs_id.Sensors.ExtVolt1,
        sbs_id.Sensors.ExtVolt2,
        sbs_id.Sensors.ExtVolt3,
        sbs_id.Sensors.ExtVolt4,
        sbs_id.Sensors.ExtVolt5,
        sbs_id.Sensors.ExtVolt6,
        sbs_id.Sensors.ExtVolt7,
    ]
    enabled_sensors = [*enabled_sensors, *voltage_sensors]

    if instrument_info["SurfaceParVoltageAdded"] == "1" and [
        l for l in hex.sbe9_data if l.startswith("surface PAR")
    ]:
        enabled_sensors.append(sbs_id.Sensors.SPAR)
    if instrument_info["NmeaPositionDataAdded"] == "1":
        enabled_sensors.append(sbs_id.Sensors.nmeaLocation)
    if instrument_info["NmeaDepthDataAdded"] == "1":
        enabled_sensors.append(sbs_id.Sensors.nmeaDepth)
    if instrument_info["NmeaTimeAdded"] == "1":
        enabled_sensors.append(sbs_id.Sensors.nmeaTime)
    else:
        enabled_sensors.append(sbs_id.Sensors.SystemTime)

    # handle Scanfish data
    if not [line for line in hex.sbe9_data if line.startswith("SBE 11plus")]:
        enabled_sensors.append(sbs_id.Sensors.SystemTime)

    # use own function to read hex file
    with open(hex.path_to_file, "r") as f:
        result = f.readlines()

    array_data = []
    for line in result:
        if line.startswith("*"):
            continue
        hex_data = sbs_id.read_hex(
            instrument_type,
            line,
            enabled_sensors,
        )
        array_data.append(hex_data)

    data = pd.DataFrame(array_data)

    return data


def sorting_parameters(
    sensor_info: list,
    rule: list = [
        "Pressure",
        "Temperature",
        "Temperature2",
        "Conductivity",
        "Conductivity2",
    ],
) -> list:
    """
    Brings sensor data from an .xmlcon file in a pre-definded order.

    This ensures the correct conversion order, for parameters that depend
    on others, like salinity or oxygen. The default list is not meant to
    be changed.


    Parameters
    ----------
    sensor_info: list
        The parsed .xmlcon info
    rule: list
        A list defining the initial conversion order of certain parameters

    Returns
    -------
    The complete .xmlcon info in correct conversion order.
    """
    out_list = []
    for name in rule:
        for param in sensor_info:
            if name == param["SensorName"]:
                out_list.append(param)

    for param in sensor_info:
        if param["SensorName"] not in rule:
            out_list.append(param)

    return out_list


def get_time_gaps(raw_data: pd.DataFrame) -> dict:
    """
    Detect missing data points in the raw CTD data.

    Parameters
    ----------
    raw_data: pd.DataFrame
        Pandas DataFrame holding the structured CTD raw data

    Returns
    -------
    A dictionary with the indices and sizes of data gaps.
    """
    data_integrity = raw_data["data integrity"].values.astype(int)
    diff = np.diff(data_integrity) % 256
    gaps = np.where(diff != 1)[0]
    gap_sizes = {a: diff[a] - 1 for a in gaps}
    return gap_sizes


def handle_time(
    gap_sizes: dict,
    hex: HexFile,
    data_size: int,
    parameters: Parameters = Parameters([], [], True),
):
    """
    Fills data gaps and creates correct time arrays.

    Data gaps are filled with NaNs.
    Time array created are
        1) a time elapsed one, counting the seconds from the cast start,
        2) a unix timestamp.

    Parameters
    ----------
    gap_sizes: dict
        A dictionary with the indices and sizes of time gaps
    hex: HexFile
        A .hex file to get the cast start time
    data_size: int
        The size of the data, to enable skipping of upcast time gaps
    parameters: Parameters
        Parameters object to create the time arrays in
    """
    for index, gap_size in sorted(gap_sizes.items(), reverse=True):
        if index > data_size:
            continue
        for param in parameters.values():
            param.data = np.insert(param.data, index, [np.nan] * (gap_size))

    seconds_since_start = np.cumsum(
        np.concatenate(
            [
                [0.0],
                np.ones((data_size + sum(gap_sizes.values())) - 1) * (1 / 24),
            ]
        )
    )

    parameters.create_parameter(
        np.round(seconds_since_start, 3),
        name="timeS",
    )

    start_time_posix = hex.start_time.timestamp()
    corrected_time_array = seconds_since_start + start_time_posix

    parameters.create_parameter(
        corrected_time_array.astype("float"),
        name="timeU",
    )


def decode_hex(
    hex: HexFile | Path | str,
    xmlcon: XMLCONFile | Path | str = "",
    downcast_only: bool = True,
    **kwargs,
) -> CTDData:
    """
    Orchestrates the conversion of CTD data from a .hex file.

    Runs the following steps:
        1) Reads raw data from .hex file
        2) Converts that using calibration information from a corresponding
            .xmlcon file
        3) Fixes the time array (filling time gaps)
        4) Determines cast start and end points
        5) Adds Location and Flag columns
        6) Writes conversion metadata to a structure that resembles .cnv
            file format

    Parameters
    ----------
    hex: HexFile | Path | str
        The .hex file to convert
    xmlcon: XMLCONFile | Path | str
        The corresponding .xmlcon file, if blank, the HexFile will try to it itself
    downcast_only: bool
        Whether to only convert downcast data (Default value = True)
    **kwargs :
        These options will be parsed to the cast border detection logic

    Returns
    -------
    A CTDData object that holds all data and metadata and can be exported different formats.
    """
    # input check
    if not isinstance(hex, HexFile):
        try:
            hex = HexFile(hex)
        except Exception as error:
            message = f"Could not open hex file {hex}: {error}"
            logger.error(message)
            sys.exit(message)

    if xmlcon:
        if not isinstance(xmlcon, XMLCONFile):
            try:
                xmlcon = XMLCONFile(xmlcon)
            except Exception as error:
                message = f"Could not open xmlcon file {xmlcon}: {error}"
                logger.warning(message)
        hex.xmlcon = xmlcon

    if not hex.xmlcon:
        sys.exit(
            f"No corresponding xmlcon for hex file {hex} found. Aborting."
        )
    parameters = Parameters([], [], True)
    cast_borders = {}
    raw_data = hex_reading(hex)
    for sensor in sorting_parameters(hex.xmlcon.sensor_info):
        sensor_name = sensor["SensorName"]
        if sensor_name in ["FluoroWetlabCDOM"]:
            continue
        mapping = ParameterMapping(sensor, raw_data, parameters)
        try:
            parameters.create_parameter(
                data=mapping.converted_data,
                metadata=mapping.metadata,
                name=sensor_name,
            )
        except AttributeError:
            logger.debug(f"{sensor_name} had no succesfull mapping.")

    # add lat and lon column, as well as depth
    if "NMEA Latitude" in raw_data.columns:
        lat = raw_data["NMEA Latitude"]
        lon = raw_data["NMEA Longitude"]
    else:
        lat, lon = hex.start_position

    parameters.create_parameter(lat, name="latitude")
    parameters.create_parameter(lon, name="longitude")
    parameters.calculate_depth()

    # add flag column
    data_length = raw_data.shape[0]
    parameters.create_parameter(data=np.zeros(data_length), name="flag")
    # correct time
    gap_sizes = get_time_gaps(raw_data)
    handle_time(gap_sizes, hex, data_length, parameters)
    # cast borders
    if downcast_only:
        cast_borders = get_cast_borders(
            parameters["prDM"].data,
            downcast_only,
            **kwargs,
        )
        cast_borders["input_size"] = raw_data.shape[0]
        for param in parameters.values():
            param.data = param.data[
                cast_borders["down_start"] : cast_borders["down_end"] + 1
            ]
    # create processing_steps
    timestamp = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
    try:
        version = f", v{importlib.metadata.version('ctdam.parser')}"
    except Exception:
        version = ""
    processing_steps = CnvProcessingSteps([])
    processing_steps.add_info(
        module="hex2py",
        key="metainfo",
        value=f"{timestamp}, ctdam.parser python package{version}",
    )
    if gap_sizes:
        processing_steps.add_info(
            module="hex2py",
            key="time_correction",
            value=", ".join(
                [
                    f"{str(key)}: {str(value)}"
                    for key, value in gap_sizes.items()
                ]
            ),
        )
    if cast_borders:
        processing_steps.add_info(
            module="hex2py",
            key="cast_borders",
            value=", ".join(
                [
                    f"{str(key)}: {str(value)}"
                    for key, value in cast_borders.items()
                    if key.strip().startswith(("down", "up", "input_size"))
                ]
            ),
        )

    # CTDData instance to collect all info
    return CTDData(
        parameters=parameters,
        metadata_source=hex,
        processing_steps=processing_steps,
    )
