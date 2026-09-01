import logging
import re
from itertools import zip_longest
from typing import Optional, Tuple

from ctdam import PARAMETER_MAPPING

logger = logging.getLogger(__name__)


def read_event_name(
    station_string: str,
    regex_string: str = r"(?P<c>[a-z]{1,3}\d{1,3})(-|_|\/)?(?P<cn>1|2)?(-|_)(?P<s>\d{1,4})(-|_)(?P<e>\d{1,2})",
) -> Tuple[str, str]:
    """
    Parse event name information.

    Parameters
    ----------
    station_string: str
        The input string to parse
    regex_string: str
        The regex to use for parsing

    Returns
    -------
    A tuple of cruise name and event string.
    """
    match = re.match(regex_string, station_string, flags=re.I)
    if match:
        match_dict = dict(match.groupdict())
        cruise_name = match_dict["c"]
        if "cn" in match_dict:
            if match_dict["cn"]:
                cruise_name = f"{match_dict['c']}_{match_dict['cn']}"

        if "s" in match_dict:
            station = match_dict["s"]
        else:
            station = ""
        if "e" in match_dict:
            event = match_dict["e"]
        else:
            event = ""
    else:
        cruise_name = station = event = ""
    if station:
        station = f"{station.lstrip('0')}-{event.lstrip('0')}"
        # handle all-zero case
        if station == "-":
            station = ""
    else:
        station = ""
    return cruise_name, station


def create_event_string(
    cruise: str,
    station_event: str,
    leading_zeroes: bool = True,
) -> str:
    """
    Produce a output event string.

    Parameters
    ----------
    cruise: str
        The cruise it belongs to
    station_event: str
        The event information from read_event_name
    leading_zeroes: bool
        Whether to save the event info with leading zeroes (Default value = True)

    Returns
    -------
    The output event string.
    """
    if station_event == "":
        return ""
    station, event = station_event.split("-")
    if leading_zeroes:
        return f"{cruise.upper()}_{float(station):03.0f}-{int(event):02.0f}"
    else:
        return f"{cruise.upper()}_{int(station)}-{int(event)}"


def parse_xmlcon_sensor_data(sensor_info: dict) -> dict:
    """
    Parse sensor data from .cnv files.

    Parameters
    ----------
    sensor_info: dict
        The xmltodict output of a .cnv file

    Returns
    -------
    Tidied dictionary sensor information.
    """
    sensor_info = sensor_info["SBE_InstrumentConfiguration"]["Instrument"][
        "SensorArray"
    ]
    # rename sensor array size -> count
    sensor_info = {
        "@count" if k == "@Size" else k: v for k, v in sensor_info.items()
    }
    # rename Sensor -> sensor
    sensor_info = {
        "sensor" if k == "Sensor" else k: v for k, v in sensor_info.items()
    }
    for sensor in sensor_info["sensor"]:
        # remove redudant SensorID
        sensor.pop("@SensorID")
        # rename index -> Channel
        sensor["@Channel"] = str(int(sensor.pop("@index")) + 1)

    return sensor_info


def extract_sensor_name(sensors: dict) -> list:
    """
    Parse sensor data from .xmlcon files.

    Parameters
    ----------
    sensors: dict
        xmltodict parsed .xmlcon data

    Returns
    -------
    A list of sensor dictionaries.
    """
    # create a tidied version of the xml-parsed sensor dict
    sensor_names = []
    tidied_sensor_list = []
    for entry in sensors:
        try:
            sensor_key = [
                key
                for key in entry.keys()
                if key.endswith(("Sensor", "Meter"))
            ][0]
        except IndexError:
            continue
        sensor_name = sensor_key.removesuffix("Sensor")
        # the wetlab sensors feature a suffix _Sensor
        sensor_name = sensor_name.removesuffix("_")
        # assuming, that the first sensor in the xmlcon is also on the
        # first sensor strand, the second occurence of the name is
        # suffixed with '2'
        if sensor_name in sensor_names:
            sensor_name += "2"
        sensor_names.append(sensor_name)
        # move the calibration info one dictionary level up
        calibration_info = entry[sensor_key]
        # build the new dictionary
        try:
            new_dict = {
                "Channel": str(int(entry["@index"]) + 1),
                "SensorName": sensor_name,
                **calibration_info,
            }
        except Exception:
            new_dict = {
                "Channel": entry["@Channel"],
                "SensorName": sensor_name,
                **calibration_info,
            }
        tidied_sensor_list.append(new_dict)
    return tidied_sensor_list


def get_unique_sensor_data(
    sensor_data: list[list[dict]],
) -> list[tuple[list[dict]]]:
    """
    Returns all the unique sensors and their configuration used in the given
    collection of sensor data. These will typically be parsed from xml inside
    .cnv or .xmlcon files.
    If for example, the first oxygen sensor has been replaced after the 8 cast,
    then we will see that in the output structure by a seconde tuple, with the
    number 8 and the individual sensor information for that new oxygen sensor.

    Parameters
    ----------
    sensor_data : list[list[dict]] :
        The structure of xml-parsed dicts inside two organizing lists.

    Returns
    -------
    A list of sensor tuples.
    """
    unique = []
    last_unique = None
    for index, individual_sensor_data in enumerate(
        [file for file in sensor_data]
    ):
        if last_unique is None:
            unique.append((index, individual_sensor_data))
        else:
            differing_dicts = [
                current_dict
                for last_dict, current_dict in zip_longest(
                    last_unique, individual_sensor_data
                )
                if current_dict != last_dict
            ]
            if differing_dicts:
                unique.append((index, differing_dicts))
        last_unique = individual_sensor_data
    return unique


def coordinates_to_float(coordinate: str, axis: Optional[str] = None) -> float:
    """
    reads encoded coordinates and parses them as regular floats

    Parameters
    ----------
    coordinate : str
        float + cardinal direction
        e.g. 0.241251E, 0.9215152N

    axis: Optional[str]
        offers optional input to explicitly document/enforce either North-South or West-East axis

    Returns
    -------
    float
        returns pure float with cartesian coordinate sign
    """
    neg_directions = ("S", "W")

    try:
        if axis:
            if axis not in coordinate:
                raise ValueError(
                    f"Direction '{axis}' not found in coordinate '{coordinate}'"
                )
            coord = float(coordinate.replace(axis, ""))
            return -coord if axis in neg_directions else coord

        else:
            direction = coordinate[-1]
            if direction not in ("N", "S", "E", "W"):
                raise ValueError(
                    f"Invalid direction '{direction}'. Expected N, S, E, or W"
                )

            coord = float(coordinate[:-1])
            return -coord if direction in neg_directions else coord

    except ValueError as e:
        raise ValueError(f"Error while parsing coordinate '{coordinate}': {e}")


def sbe_to_decimal(data_str: str) -> float:
    """Converts NMA Coordinates to Decimal"""
    try:
        parts = data_str.split()
        degrees = float(parts[0])
        minutes = float(parts[1])
        direction = parts[2]

        decimal = degrees + (minutes / 60)
        if direction in ["S", "W"]:
            decimal *= -1
        return decimal
    except (IndexError, ValueError) as e:
        raise ValueError(f"Error while parsing Coordinates '{data_str}': {e}")


def map_metadata(name: str = "", second_sensor: bool = False) -> dict:
    """
    Retrieve default metadata for a given parameter.

    Parameters
    ----------
    name: str
        The parameter name to find metadata for

    Returns
    -------
    The metadata info as dictionary.
    """
    if second_sensor:
        name = name + " 2"
    try:
        lower_mapping = {k.lower(): v for k, v in PARAMETER_MAPPING.items()}
        return lower_mapping[name.lower()]
    except KeyError:
        return {}


def get_cast_number_from_btl_id(id: int, bottle_capacity: int = 25) -> int:
    """
    Returns the corresponding cast number to a given global Bottle ID.

    Parameters
    ----------
    id: int:
        The target Bottle ID
    bottle_capacity: int:
        The number of water bottles attached to the CTD rosette

    Returns
    -------
    An integer representing the cast number inside a cruise
    """
    quotient = id // bottle_capacity
    if quotient == 0:
        return bottle_capacity
    else:
        return quotient
