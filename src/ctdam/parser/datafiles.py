import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import xmltodict

from ctdam.utils import (
    create_event_string,
    extract_sensor_name,
    read_event_name,
    sbe_to_decimal,
)

logger = logging.getLogger(__name__)


class DataFile:
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
        self.raw_file_data = []  # the text file input
        self.header = []  # the full file header
        self.sbe9_data = []  # device specific information
        self.metadata = {}  # non-SeaBird metadata
        self.metadata_list = []  # unstructured metadata for easier export
        self.data_table_description = []  # the column names and other info
        self.sensor_data = []
        self.sensors = {}  # xml-parsed sensor data
        self.processing_info = []  # everything after the sensor data
        self.data = []  # the data table
        self.file_data = self.raw_file_data  # variable file information
        self.read_file()
        self.metadata = self.structure_metadata(self.metadata_list)
        if len(self.sensor_data) > 0:
            self.sensors = self.sensor_xml_to_flattened_dict(
                "".join(self.sensor_data)
            )
        self.start_time = self.reading_start_time()
        self.start_position = self.reading_start_position()
        self.read_event_information()

    def __str__(self) -> str:
        return "/n".join(self.file_data)

    def __repr__(self) -> str:
        return str(self.path_to_file.absolute())

    def __eq__(self, other) -> bool:
        return self.file_data == other.file_data

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

    def read_file(self):
        """
        Reads and structures all the different information present in the file.

        Lists and Dictionaries are the data structures of choice. Uses
        basic prefix checking to distinguish different header information.
        """
        past_bad_flag = False
        with self.path_to_file.open("r", encoding="latin-1") as file:
            for line in file:
                self.raw_file_data.append(line)
                if line.startswith("* "):
                    self.header.append(line)
                    self.sbe9_data.append(line[2:])
                elif line.startswith("**"):
                    self.header.append(line)
                    self.metadata_list.append(line[3:])
                elif line.startswith("#"):
                    self.header.append(line)
                    if line[2:].strip().startswith("<"):
                        self.sensor_data.append(line[2:])
                    else:
                        if past_bad_flag:
                            self.processing_info.append(line[2:])
                        else:
                            self.data_table_description.append(line[2:])
                            if line.startswith("# bad_flag"):
                                past_bad_flag = True
                else:
                    if line.startswith("*END*"):
                        self.header.append(line)
                        if self.only_header:
                            break
                    else:
                        self.data.append(line)

    def reading_start_time(self) -> datetime | None:
        """
        Extracts the Cast start time from the metadata header.

        Returns
        -------
        A datetime object.
        """
        start_time = None
        for line in self.header:
            if line.startswith(("* System UTC", "* NMEA UTC")):
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
        for line in self.sbe9_data:
            if line.startswith("NMEA Latitude"):
                lat = sbe_to_decimal(line.split("=", 1)[1].strip())
            elif line.startswith("NMEA Longitude"):
                lon = sbe_to_decimal(line.split("=", 1)[1].strip())
        return (lat, lon)

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

    def define_output_path(
        self,
        file_path: Path | str | None = None,
        file_name: str | None = None,
        file_type: str = ".csv",
    ) -> Path:
        """
        Creates a Path object holding the desired output path.

        Parameters
        ----------
        file_path : Path
            Directory the file sits in (Default value = self.file_dir)
        file_name : str
            The original file name (Default value = self.file_name)
        file_type : str
            The file suffix (Default value = ".csv")

        Returns
        -------


        """
        file_path = self.file_dir if file_path is None else file_path
        file_name = self.file_name if file_name is None else file_name
        if file_type[0] != ".":
            file_type = "." + file_type
        return Path(file_path).joinpath(file_name).with_suffix(file_type)

    def to_csv(
        self,
        data: pd.DataFrame | np.ndarray,
        with_header: bool = True,
        output_file_path: Path | str | None = None,
        output_file_name: str | None = None,
    ):
        """
        Writes a .csv file from the given data.

        Parameters
        ----------
        data : pd.DataFrame | np.ndarray
            The source data to use.
        with_header : boolean :
            Indicating whether the header shall appear in the output (Default value = True)
        output_file_path : Path
            File directory (Default value = None)
        output_file_name : str
            Original file name (Default value = None)
        """
        new_file_path = self.define_output_path(
            output_file_path, output_file_name
        )
        if with_header:
            with open(new_file_path, "w") as file:
                for line in self.header:
                    file.write(line)
        if isinstance(data, pd.DataFrame):
            data.to_csv(new_file_path, index=False, mode="a")
        else:
            np.savetxt(new_file_path, data, delimiter=",")

    def selecting_columns(
        self,
        list_of_columns: list | str,
        df: pd.DataFrame,
    ):
        """
        Alters the dataframe to only hold the given columns.

        Parameters
        ----------
        list_of_columns : list or str
            A collection of columns
        df : pandas.Dataframe :
            Dataframe (Default value = None)
        Returns
        -------


        """
        # ensure that the input is a list, so that isin() can do its job
        if isinstance(list_of_columns, str):
            list_of_columns = [list_of_columns]
        if isinstance(df, pd.DataFrame):
            self.df = df[list_of_columns].reset_index(drop=True)
