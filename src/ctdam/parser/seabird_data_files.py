import io
import logging
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Tuple, Union

import numpy as np
import odf.sbe.accessors
import pandas as pd
import xarray as xr
import xmltodict
from odf.sbe.io import read_hex, string_loader

from ctdam.exceptions import UnexpectedFileFormat
from ctdam.parser.xmlfiles import XMLCONFile
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
    lists or dictionaries.

    Attributes
    ----------
    path_to_file: Path
        The path to the file this object represents
    file_name: str
        The file name
    file_dir: Path
        The directory the file resides in
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
        """Extracts the Cast start time from the metadata header."""
        start_time = None
        for line in self.instrument_metadata:
            if line.startswith(("System UTC", "NMEA UTC")):
                start_time = line.split("=", 1)[1].strip()
                break
        if start_time:
            start_time = datetime.strptime(start_time, "%b %d %Y %H:%M:%S")
        return start_time

    def reading_start_position(self) -> Tuple:
        """Extracts the Casts starting position."""
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
        metadata_list : list :
            A list of the individual lines of metadata found in the file

        Returns
        -------
        A dictionary representation of the custom metadata
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
    """A representation of a cnv-file as used by SeaBird."""

    def __init__(
        self,
        path_to_file: Path | str,
        only_header: bool = False,
    ):
        super().__init__(path_to_file, only_header)
        self.data = self.parse_cnv_data_format()
        self.unixtime = self.absolute_time_calculation()

    def parse_cnv_data_format(self) -> dict[str, np.ndarray]:
        """ """
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


class HexFile(SeabirdDataFile):
    """
    A representation of a .hex file as used by SeaBird.

    When no corresponding .xmlcon file given, a search algorithm is used
    to determine the matching .xmlcon automatically.
    """

    def __init__(
        self,
        path_to_file: Path | str,
        path_to_xmlcon: Path | str = "",
        *args,
        **kwargs,
    ):
        # force loading only metadata
        super().__init__(path_to_file, True)
        self.xmlcon = self.get_corresponding_xmlcon(path_to_xmlcon)
        self.raw_ds = self.parse_hex(path_to_file)
        self.unixtime = self._handle_time()

    def parse_hex(self, hex: Path | str) -> xr.Dataset:
        """
        Parse the individual hex information bits using sbe.odf

        Parameters
        ----------
        hex: Path | str :
            The path to the target hex file

        Returns
        -------
        A xarray Dataset storing the parsed data
        """
        raw_ds = read_hex(hex)
        # extra xmlcon parsing necessary, because our xmlcon detection is way
        # smarter than the one inside odf.sbe
        if not "xmlcon" in raw_ds.data_vars and isinstance(
            self.xmlcon, XMLCONFile
        ):
            raw_ds["xmlcon"] = string_loader(
                self.xmlcon.path_to_file,
                "xmlcon",
            )["xmlcon"]
        if not "xmlcon" in raw_ds.data_vars:
            raise AttributeError(
                f"Could not detect matching xmlcon file for hex {self.path_to_file}. No further data serialization possible."
            )
        serialized_ds = raw_ds.sbe.serialize()
        return serialized_ds

    def _get_time_gaps(self) -> dict:
        """Detect missing data points in the raw CTD data."""
        data_integrity = self.raw_ds["mod"].values.astype(int)
        diff = np.diff(data_integrity) % 256
        gap_positions = np.where(diff != 1)[0]
        gap_sizes = {int(a): int(diff[a] - 1) for a in gap_positions}
        return gap_sizes

    def _handle_time(self):
        """
        Fills data gaps and creates correct time arrays.
        Data gaps are filled with NaNs.
        Adds a time column counting the seconds from the start.
        """
        self.gaps = self._get_time_gaps()

        # integer dtypes silently reject np.nan, so cast to float first.
        for param in self.raw_ds.data_vars:
            if param in ("hex", "xmlcon"):
                continue
            if np.issubdtype(self.raw_ds[param].dtype, np.integer):
                self.raw_ds[param] = self.raw_ds[param].astype(float)

        for index, gap_size in sorted(self.gaps.items(), reverse=True):
            if gap_size <= 0:
                continue
            if index >= self.raw_ds.scan.size:
                continue

            pre = self.raw_ds.isel(scan=slice(0, index + 1))
            post = self.raw_ds.isel(scan=slice(index + 1, None))

            # Build a gap-sized NaN block that matches every variable's
            # dims/dtype (so "hex" with its extra channel dim works too).
            nan_vars = {}
            for param, da in self.raw_ds.data_vars.items():
                if "scan" not in da.dims:
                    # e.g. xmlcon / config data not indexed by scan -- skip
                    continue
                template = da.isel(scan=slice(0, gap_size))
                fill_dtype = (
                    float
                    if np.issubdtype(template.dtype, np.integer)
                    else template.dtype
                )
                nan_vars[param] = xr.full_like(
                    template, np.nan, dtype=fill_dtype
                )
            nan_block = xr.Dataset(nan_vars)

            self.raw_ds = xr.concat(
                [pre, nan_block, post],
                dim="scan",
                data_vars="minimal",
                coords="minimal",
            )

        # reset the scan coordinate
        self.raw_ds = self.raw_ds.drop_vars("scan")
        self.raw_ds = self.raw_ds.assign_coords(
            scan=np.arange(self.raw_ds.f0.size)
        )

        # build time vector holding seconds since start, called 'timeS'
        # in the Sea-Bird world
        seconds_since_start = np.arange(self.raw_ds.scan.size) * (1 / 24)
        start_time_posix = self.start_time.timestamp()
        corrected_time_array = seconds_since_start + start_time_posix
        return corrected_time_array.astype("float")

    def get_corresponding_xmlcon(
        self,
        path_to_xmlcon: Path | str = "",
    ) -> XMLCONFile | None:
        """
        Finds the best matching .xmlcon file inside the same directory.

        The logics works as follows:

        - if an .xmlcon of the same name exists, take that
        - else, find all .xmlcons of the same cruise inside the given
          directory and use the one used by the previous .hex file, sorted
          by file name.
        """
        # xmlcon path given, test and use it
        if isinstance(path_to_xmlcon, str):
            if path_to_xmlcon:
                return XMLCONFile(path_to_xmlcon)
        else:
            if path_to_xmlcon.exists():
                return XMLCONFile(path_to_xmlcon)
        # no xmlcon path, lets find one in the same dir
        # get all xmlcons in the dir
        # first, try the very same name
        same_name_xmlcon = self.path_to_file.with_suffix(".XMLCON")
        if same_name_xmlcon.exists():
            return XMLCONFile(same_name_xmlcon)

        # otherwise, take the xmlcon of the previous hex file, sorted by name
        # use either the extracted cruise name or the first five letters for
        # searching for xmlcons of the same cruise
        if self.cruise:
            prefix = (
                re.split(r"[_\-\/]", self.cruise.lower())[0]
                if any(x in self.cruise.lower() for x in ["_", "-", "/"])
                else self.cruise.lower()
            )
        else:
            prefix = self.file_name.lower()[:5]
        xmlcons = [
            xmlcon
            for xmlcon in sorted(
                self.file_dir.glob("*.XMLCON", case_sensitive=False)
            )
            if xmlcon.stem.lower().startswith(prefix)
        ]
        if not xmlcons:
            return None

        # looking back and using xmlcon from the previous hex file
        all_hexes = [
            hex
            for hex in sorted(
                self.file_dir.glob("*.hex", case_sensitive=False)
            )
            if hex.stem.lower().startswith(prefix)
        ]
        index = all_hexes.index(self.path_to_file)
        previous_hexes = all_hexes[:index]
        if previous_hexes:
            try:
                return HexFile(previous_hexes[-1]).xmlcon
            except AttributeError:
                pass

        return XMLCONFile(xmlcons[0])


class BottleLogFile(SeabirdDataFile):
    """
    Bottle Log file (.bl) representation, that extracts the three different data
    types from the file: reset time and the table with bottle IDs and
    corresponding data ranges.
    """

    def __init__(self, path_to_file):
        super().__init__(path_to_file)
        self.reset_time = self.obtaining_reset_time()
        self.data = self.data_whitespace_removal()
        self.df = self.create_dataframe()

    def data_whitespace_removal(self) -> list:
        """
        Strips the input from whitespace characters, in this case especially
        newline characters.
        """
        temp_data = []
        for line in self.raw_data[2:]:
            temp_data.append(line.strip())
        return temp_data

    def obtaining_reset_time(self) -> datetime:
        """Reading reset time with small input check."""

        regex_check = re.search(
            r"RESET\s(\w{3}\s\d+\s\d{4}\s\d\d:\d\d:\d\d)",
            self.raw_data[1],
        )
        if regex_check:
            return datetime.strptime(regex_check.group(1), "%b %d %Y %H:%M:%S")
        else:
            error_message = """BottleLogFile is not formatted as expected:
                Reset time could not be extracted."""
            logger.error(error_message)
            raise IOError(error_message)

    def create_dataframe(self) -> pd.DataFrame:
        """Creates a dataframe from the list specified in self.data."""
        data_lists = []
        for line in self.data:
            inner_list = line.split(",")
            # dropping first column as its the index
            data_lists.append(inner_list[1:])
        df = pd.DataFrame(data_lists)
        df.columns = ["Bottle ID", "Datetime", "start_range", "end_range"]
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df["Bottle ID"].astype("int")
        df["start_range"].astype("int")
        df["end_range"].astype("int")
        return df


class BottleFile(SeabirdDataFile):
    """Class that represents a Sea-Bird Bottle File (.btl) ."""

    def __init__(self, path_to_file: Path | str):
        super().__init__(path_to_file)
        self.df = self.create_dataframe()
        self.adding_timestamp_column()

    def create_dataframe(self):
        """
        Creates a dataframe out of the .btl file.
        Handles the double data header correctly.
        """
        top_names, bottom_names = self.reading_data_header()
        # creating statistics column to store the row type information:
        # 4 rows per bottle, average, standard deviation, max value, min value
        top_names.append("Statistic")
        data_text = "".join(self.raw_data[2:])

        df = pd.read_fwf(
            io.StringIO(data_text),
            index_col=False,
            header=None,
            names=top_names,
        )

        # handling the double row header
        rowtypes = df[df.columns[-1]].unique()

        def separate_double_header_row(df, column, length):
            """
            Differentiates the two header rows.

            Parameters
            ----------
            df :

            column :

            length :


            Returns
            -------

            """
            column_idx = df.columns.get_loc(column)
            old_column = df.iloc[::length, column_idx].reset_index(drop=True)
            new_column = df.iloc[1::length, column_idx].reset_index(drop=True)
            old_column_expanded = pd.Series(
                np.repeat(old_column, length)
            ).reset_index(drop=True)
            new_column_expanded = pd.Series(
                np.repeat(new_column, length)
            ).reset_index(drop=True)
            df[column] = old_column_expanded
            df.insert(
                column_idx + 1, bottom_names[column_idx], new_column_expanded
            )
            return df

        df = separate_double_header_row(df, "Date", len(rowtypes))
        df = separate_double_header_row(df, top_names[0], len(rowtypes))
        # remove brackets around statistics values
        df["Statistic"] = df["Statistic"].str.strip("()")
        df = df.rename(
            mapper={"Btl_ID": "Bottle_ID", "Bottle": "Bottle_ID"}, axis=1
        )
        return df

    def adding_timestamp_column(self):
        """Creates a timestamp column that holds both, Date and Time information."""
        # constructing timestamp column
        self.df.Date = pd.to_datetime(self.df.Date)
        timestamp = []
        for datepoint, timepoint in zip(self.df.Date, self.df.Time):
            timestamp.append(
                datetime.combine(
                    datepoint,
                    time.fromisoformat(str(timepoint)),
                ).timestamp()
            )
        self.df.insert(2, "unixtime", timestamp)

    def selecting_rows(
        self,
        df=None,
        statistic_of_interest: Union[list, str] = ["avg"],
    ):
        """
        Creates a dataframe with the given row identifier, using the
        statistics column. A single string or a list of strings can be
        processed.

        Parameters
        ----------
        df : pandas.Dataframe :
            the files Pandas representation (Default value = self.df)
        statistic_of_interest : list or str
            collection of values of the 'statistics' column in self.df
        """
        df = self.df if df is None else df
        # ensure that the input is a list, so that isin() can do its job
        if isinstance(statistic_of_interest, str):
            statistic_of_interest = [statistic_of_interest]
        self.df = df.loc[df["Statistic"].isin(statistic_of_interest)]
        self.df.drop(columns=["Statistic"], inplace=True)

    def reading_data_header(self):
        """
        Identifies and separatly collects the rows that specify the data
        tables headers.
        """
        n = 11  # fix column width of a seabird btl file
        top_line = self.raw_data[0]
        second_line = self.raw_data[1]
        top_names = [
            top_line[i : i + n].split()[0]
            for i in range(0, len(top_line) - n, n)
        ]
        bottom_names = [
            second_line[i : i + n].split()[0] for i in range(0, 2 * n, n)
        ]
        return top_names, bottom_names
