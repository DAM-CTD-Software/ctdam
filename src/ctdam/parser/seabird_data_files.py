import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

import numpy as np
import xmltodict

from ctdam.exceptions import UnexpectedFileFormat
from ctdam.utils import (
    create_event_string,
    extract_sensor_name,
    read_event_name,
    sbe_to_decimal,
)

logger = logging.getLogger(__name__)


class SeabirdDataFile:
    """
    The base class for all Sea-Bird data files, which are .cnv, .btl, and .bl .
    One instance of this class, or its children, represents one data text file.
    The different information bits of such a file are structured into individual
    lists or dictionaries. The data table will be loaded as numpy array and
    can be converted to a pandas DataFrame. Datatype-specific behavior is
    implemented in the subclasses.

    Parameters
    ----------
    path_to_file: Path | str
        The file to the data file.
    only_header: bool
        Whether to stop reading the file after the metadata header.

    Attributes
    ----------
    path_to_file: Path
        The path to the file this object represents
    file_name: str
        The file name
    file_dir: Path
        The directory the file resides in
    sbe9_data: list
        Device specific information
    metadata: dict
        Non-SeaBird metadata
    metadata_list: list
        Unstructured metadata for easier export
    data_table_description: list
        The column names and other info
    sensor_data: list
        The sensor lines
    sensors: dict
        Xml-parsed sensor data
    processing_info: list
        Everything after the sensor data
    data: list
        The data table
    metadata: dict
        Parsed custom metadata
    start_time: datetime
        The start time of the data acquisition
    start_position: tuple
        Latitude, Longitude tuple
    cruise: str
        The name of the cruise the data belongs to
    station: str
        The station idenifier of the data
    event_name: str
        The streamlined data event name, consisting of cruise and station name

    """

    def __init__(
        self,
        path_to_file: Path | str,
        only_header: bool = False,
    ):

        self.path_to_file = Path(path_to_file)
        self.file_name = self.path_to_file.stem
        self.file_dir = self.path_to_file.parent
        self.only_header = only_header
        self.read_file()
        self.metadata = self.structure_metadata(self.custom_metadata)
        # if len(self.sensor_metadata) > 0:
        #     self.sensors = self.sensor_xml_to_flattened_dict(
        #         "".join(self.sensor_metadata)
        #     )
        self.start_time = self.reading_start_time()
        self.start_position = self.reading_start_position()
        self.read_event_information()

    def __str__(self) -> str:
        return str(self.path_to_file.absolute())

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        return self.__str__() == other.__str__()

    def read_file(self):
        """
        Reads and structures all the different information present in the file.

        Lists and Dictionaries are the data structures of choice. Uses
        basic prefix checking to distinguish different header information.
        """
        self.raw_data: list = []
        self.instrument_metadata: list = []
        self.custom_metadata: list = []
        self.sensor_metadata: list = []
        self.processing_history: list = []
        self.data_table_description: list = []
        past_bad_flag = False
        with self.path_to_file.open("r", encoding="latin-1") as file:
            for line in file:
                if line.startswith("*END*"):
                    if self.only_header:
                        break
                    continue

                if line.startswith("* "):
                    self.instrument_metadata.append(line[2:])
                    continue

                if line.startswith("**"):
                    self.custom_metadata.append(line[3:])
                    continue

                if line.startswith("#"):
                    content = line[2:]
                    if content.strip().startswith("<"):
                        self.sensor_metadata.append(content)
                    elif past_bad_flag:
                        self.processing_history.append(content)
                    else:
                        self.data_table_description.append(content)
                        if line.startswith("# bad_flag"):
                            past_bad_flag = True
                    continue

                self.raw_data.append(line)

    def reading_start_time(self) -> datetime | None:
        """
        Extracts the Cast start time from the metadata header.

        Returns
        -------
        A datetime object.
        """
        start_time = None
        for line in self.instrument_metadata:
            if line.startswith(("System UTC", "NMEA UTC")):
                start_time = line.split("=", 1)[1].strip()
                break
        if start_time:
            start_time = datetime.strptime(start_time, "%b %d %Y %H:%M:%S")
        return start_time

    def reading_start_position(self) -> Tuple:
        """
        Extracts the Casts starting position.

        Returns
        -------
        A tuple with latitude and longitude in decimal degrees.
        """
        lat = lon = 0
        for line in self.instrument_metadata:
            if line.startswith("NMEA Latitude"):
                lat = sbe_to_decimal(line.split("=", 1)[1].strip())
            elif line.startswith("NMEA Longitude"):
                lon = sbe_to_decimal(line.split("=", 1)[1].strip())
        return (lat, lon)

    def read_event_information(
        self,
        regex_string: str = r"(?P<c>[a-z]{1,3}\d{1,3})(-|_|\/)?(?P<cn>1|2)?(-|_)(?P<s>\d{1,4})(-|_)(?P<e>\d{1,2})",
        leading_zeroes: bool = False,
    ):
        """
        Save the event metadata of the cast inside self.station .

        Additionally save cruise information inside self.cruise, if possible.
        The data sources are file name and custom metadata header, in this
        order.


        Parameters
        ----------
        regex_string: str
            The regex to use for event metadata retrieval
        leading_zeroes: bool
            Whether to save the info with leading zeroes (Default value = False)
        """
        self.cruise, self.station = read_event_name(
            self.file_name,
            regex_string,
        )
        if "Station" in self.metadata and not self.station:
            station_string = self.metadata["Station"]
            self.cruise, self.station = read_event_name(
                station_string,
                regex_string,
            )
        self.event_name = create_event_string(
            self.cruise,
            self.station,
            leading_zeroes,
        )
        self.metadata["Station"] = self.event_name

    def sensor_xml_to_flattened_dict(
        self, sensor_data: str
    ) -> list[dict] | dict:
        """
        Reads the pure xml sensor input and creates a multilevel dictionary,
        dropping the first two dictionaries, as they are single entry only.

        Parameters
        ----------
        sensor_data : str:
            The raw xml sensor data.

        Returns
        -------
        A list of sensor metadata dictionaries.
        """
        full_sensor_dict = xmltodict.parse(sensor_data, process_comments=True)
        try:
            sensors = full_sensor_dict["Sensors"]["sensor"]
        except KeyError as error:
            logger.error(f"XML is not formatted as expected: {error}")
            return full_sensor_dict
        else:
            # create a tidied version of the xml-parsed sensor dict
            return extract_sensor_name(sensors)

    def structure_metadata(self, metadata_list: list) -> dict:
        """
        Creates a dictionary to store custom metadata, of which Sea-Bird allows
        12 lines in each file.

        Parameters
        ----------
        metadata_list list
            A list of the individual lines of metadata found in the file

        Returns
        -------
        A dictionary storing the custom metadata.
        """
        out_dict = {}
        for line in metadata_list:
            if "=" in line:
                (key, val) = line.split("=")
            elif ":" in line:
                (key, val) = line.split(":")
            else:
                key = line
                val = ""
            out_dict[key.strip()] = val.strip()
        return out_dict


class CnvFile(SeabirdDataFile):
    """
    A representation of a cnv-file as used by SeaBird.

    This class intends to fully extract and organize the different types of
    data and metadata present inside of such a file. Downstream libraries shall
    be able to use this representation for all applications concerning cnv
    files, like data processing, transformation or visualization.

    To achieve that, the metadata header is organized by the parent-class,
    DataFile, while the data table is extracted by this class. The data
    representation can be a numpy array or pandas dataframe. The handling of
    the data is mostly done inside parameters, a representation of the
    individual measurement parameter data and metadata.

    This class is also able to parse the edited data and metadata back to the
    original .cnv file format, allowing for custom data processing using this
    representation, while still being able to use Sea-Birds original software
    on that output. It also allows to stay comparable with other parsers or
    methods in general.

    Parameters
    ----------
    path_to_file: Path | str
        The path to the file
    only_header: bool
        Whether to stop reading the file after the metadata header.
    """

    def __init__(
        self,
        path_to_file: Path | str,
        only_header: bool = False,
    ):
        super().__init__(path_to_file, only_header)
        self.data = self.parse_cnv_data_format()
        self.unixtime = self.absolute_time_calculation()

    def parse_cnv_data_format(self) -> dict[str, np.ndarray]:
        # read data table header shortnames
        # name 0 = prDM: Pressure, Digiquartz [db]
        shortnames = [
            line.split("=", 1)[1].split(":", 1)[0].strip()
            for line in self.data_table_description
            if line.startswith("name")
        ]

        n = 11
        row_list = []
        for line in self.raw_data:
            row_list.append(
                [
                    line[i : i + n].split()[0]
                    for i in range(0, len(line) - n, n)
                ]
            )
        try:
            full_data_array = np.array(row_list, dtype=float)
        except ValueError as error:
            raise UnexpectedFileFormat("CnvFile", str(error))

        assert len(shortnames) == full_data_array.shape[1], (
            "unmatching cnv header and data"
        )

        return {
            name: full_data_array[:, i] for i, name in enumerate(shortnames)
        }

    def absolute_time_calculation(self) -> np.ndarray:
        """
        Replaces the basic cnv time representation of counting relative to the
        casts start point, by a unix timestamp.

        Returns
        -------
        A numpy array containing the unixtime information.
        """
        if not self.start_time:
            return np.ndarray([])
        if "timeS" in self.data.keys():
            data = [
                timedelta(seconds=float(time)) for time in self.data["timeS"]
            ]
        elif "timeJ" in self.data.keys():
            data = [timedelta(days=float(time)) for time in self.data["timeJ"]]
        else:
            return np.ndarray([])
        return np.array(
            [(self.start_time + d).timestamp() for d in data]
        ).astype("float")
