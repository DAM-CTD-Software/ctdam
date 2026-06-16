from __future__ import annotations

import logging
import re
from collections import UserDict
from typing import Tuple

import gsw
import numpy as np
import pandas as pd

from ctdam.utils import map_metadata

logger = logging.getLogger(__name__)


class Parameters(UserDict):
    """
    A collection of all the parameters in a CnvFile.

    Allows for clean handling of parameter data and their metadata.

    Parameters
    ----------
    data : list
        The raw data as extracted by DataFile
    metadata : list
        The raw metadata as extracted by DataFile
    only_header: bool
        Whether to only work with metadata (Default=False)
    bad_flag: float
        The value to consider as bad (Default=-9.990e-29)
    """

    def __init__(
        self,
        data: list,
        metadata: list,
        only_header: bool = False,
        bad_flag: float = -9.990e-29,
    ):
        self.data = {}
        self.sample_rate = self.get_sample_rate()
        self.bad_flag = bad_flag
        parsed_metadata, self.duplicate_columns = self.reading_data_header(
            metadata
        )
        if not only_header:
            if not parsed_metadata:
                raise ValueError("Cannot parse empty CNV file.")
            self.full_data_array = self.create_full_ndarray(data)
            if self.full_data_array.size == 0:
                raise ValueError("Cannot parse empty CNV file.")
            self.create_parameter_instances(
                self.full_data_array, parsed_metadata
            )

    def __repr__(self) -> str:
        return ", ".join(self.data.keys())

    def __eq__(self, other: object, /) -> bool:
        if hasattr(other, "data"):
            try:
                return self.data == other.data
            except ValueError:
                return False
        else:
            return False

    def get_param_types(self) -> list[str]:
        """Return the parameter names."""
        return [p.param for p in self.data.values()]

    def get_data_length(self) -> int:
        """Return the number of data points."""
        return self.data[list(self.data.keys())[0]].data.shape[0]

    def get_full_data_array(self) -> np.ndarray:
        """Return a 2D numpy array holding all data."""
        return np.array([parameter.data for parameter in self.data.values()]).T

    def get_names(self) -> list[str]:
        """Return the shortnames."""
        return [parameter.name for parameter in self.data.values()]

    def get_metadata(self) -> dict[str, dict]:
        """Return the metadata."""
        return {
            parameter.name: parameter.metadata
            for parameter in self.data.values()
        }

    def get_parameter_list(self) -> list[Parameter]:
        """Return the parameter descriptions."""
        return list(self.data.values())

    def set_sample_rate(self, rate: float, unit: str):
        """
        Setter for sample rate of binned data.

        Parameters
        ----------
        rate: float
            The sample rate to set to
        unit: str
            The unit of the sample rate
        """
        self.binned = True
        self.sample_rate = rate
        self.bin_unit = unit

    def get_sample_rate(self, raw_interval_info: str = "") -> float:
        """
        Getter of the sample rate.

        Determines whether data is binned.

        Parameters
        ----------
        raw_interval_info: str
            The .cnv metadata (Default value = "")

        Returns
        -------
        The sample rate.
        """
        self.binned = False
        self.bin_unit = "seconds"
        try:
            interval_info = raw_interval_info.split(":")
        except Exception:
            pass
        else:
            if interval_info[0] == "seconds":
                sample_rate = np.round(1 / float(interval_info[1]))
                if sample_rate == 1:
                    self.binned = True
            elif interval_info[0] == "decibars" or interval_info[0] == "db":
                sample_rate = float(interval_info[1])
                self.binned = True
                self.bin_unit = "decibars"
            else:
                logger.debug(f"Unknown sample rate {interval_info[0]}.")

        # default rate, calculated if able
        try:
            return sample_rate
        except Exception:
            try:
                sample_rate = float(
                    np.round(1 / np.mean(np.diff(self.data["timeS"])))
                )
            except Exception:
                sample_rate = 24
            return sample_rate

    def remove_parameter(self, parameter: str):
        """
        Remove a parameter.

        Parameters
        ----------
        parameter : str
            A name of the parameter to be removed

        """
        if parameter in self.get_names():
            self.data.pop(parameter)

    def create_full_ndarray(self, data_table: list = []) -> np.ndarray:
        """
        Parser for .cnv data table data.

        Parameters
        ----------
        data_table : list
            The data to work with (Default value = [])

        Returns
        -------
        A numpy array holding the data
        """
        n = 11
        row_list = []
        for line in data_table:
            row_list.append(
                [
                    line[i : i + n].split()[0]
                    for i in range(0, len(line) - n, n)
                ]
            )
        try:
            return np.array(row_list, dtype=float)
        except ValueError as error:
            logger.error(
                f"Parameters: Wrong data or file format for numpy array creation: {error}"
            )
            return np.array([])

    def sort_parameters(
        self,
        top: list = [
            "depSM",
            "prDM",
            "t090C",
            "t190C",
            "sal00",
            "sal11",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "flECO-AFL",
            "turbWETntu0",
            "par",
            "spar",
        ],
        bottom: list = [
            "gsw_densityA0",
            "gsw_densityA1",
            "gsw_saA0",
            "gsw_saA1",
            "gsw_ctA0",
            "gsw_ctA1",
            "sbeox0ML/L",
            "sbeox1ML/L",
            "c0mS/cm",
            "c1mS/cm",
            "latitude",
            "longitude",
            "flag",
        ],
    ) -> dict:
        """
        Allows sorting of parameter instances for output reasons.

        Parameters
        ----------
        top: list
            The parameters to fix to the top
        bottom: list
            The parameters to fix to the bottom

        Returns
        -------
        A dictionary of the sorted parameters.
        """
        # ensure parameters at the top
        new_data = {}
        for shortname in top:
            for param in self.data.values():
                if shortname == param.name:
                    new_data[shortname] = param

        # ensure parameters at the bottom
        bottom_data = {}
        for shortname in bottom:
            for param in self.data.values():
                if shortname == param.name:
                    bottom_data[shortname] = param

        for param in self.data.values():
            if param.name not in [*top, *bottom]:
                new_data[param.name] = param

        self.data = {**new_data, **bottom_data}
        return self.data

    def create_parameter_instances(
        self,
        array_data: np.ndarray,
        metadata: dict[str, dict],
    ) -> dict[str, Parameter]:
        """
        Differentiates the individual parameter columns into separate parameter
        instances.

        Parameters
        ----------
        array_data: np.ndarray
            The parsed CTD data array
        metadata : dict[str, dict] :
            The structured metadata dictionary (Default value = {})

        Returns
        -------


        """
        parameter_dict = {}
        list_of_metadata_shortnames = list(metadata.keys())
        # if column number and metadata number is different, we are propably
        # working with duplicate_columns and will drop the duplicates
        if array_data.shape[1] != len(list_of_metadata_shortnames):
            array_data = np.delete(array_data, self.duplicate_columns, 1)
            assert array_data.shape[1] == len(list_of_metadata_shortnames)
        for i in range(array_data.shape[1]):
            key = list_of_metadata_shortnames[i]
            parameter_dict[key] = self.create_parameter(
                data=array_data[:, i],
                metadata=metadata[key],
                name=key,
            )
        return parameter_dict

    def _form_data_table_info(self, output_spans: bool = True) -> list:
        """
        Recreates the data table metadata.

        These can be column names and spans and uses the stuctured
        dictionaries these values were stored in.

        Parameters
        ----------
        output_spans: bool
            Whether to recreate data spans (Default value = True)

        Returns
        -------
        A list that represents the data table metadata
        """
        new_table_info = []
        # 'data table stats'
        data_array = self.get_full_data_array()
        new_table_info.append(f"nquan = {data_array.shape[1]}\r\n")
        new_table_info.append(f"nvalues = {data_array.shape[0]}\r\n")
        new_table_info.append("units = specified\r\n")
        # 'data tables names'
        for index, metadata in enumerate(self.get_metadata().values()):
            new_table_info.append(
                f"name {index} = {metadata['shortname']}: {metadata['longinfo']}\r\n"
            )
        # 'data table spans'
        if output_spans:
            output_formats = [p.output_format for p in self.values()]
            for index, ((minimum, maximum), output_format) in enumerate(
                zip(self.get_spans(), output_formats)
            ):
                try:
                    new_table_info.append(
                        f"span {index} = {output_format.format(minimum)}, {output_format.format(maximum)}\r\n"
                    )
                except ValueError:
                    new_table_info.append(f"span {index} = None, None")
        return new_table_info

    def add_parameter(self, parameter: Parameter, position: str = ""):
        """
        Adds one parameter instance to the collection.

        Parameters
        ----------
        parameter: Parameter :
            The new parameter instance
        position: str
            The parameter to insert the new one after (Default value = "")
        """
        # add to parameter dict at given position
        if position:
            new_dict = {}
            for key, value in self.data.items():
                new_dict[key] = value
                if key == position:
                    new_dict[parameter.name] = parameter
            self.data = new_dict

        else:
            self.data[parameter.name] = parameter

    def create_parameter(
        self,
        data: np.ndarray | int | float | str | None,
        metadata: dict = {},
        name: str = "",
        position: str = "",
    ) -> Parameter:
        """
        Creates a new parameter instance with the given data and metadata.

        The input data is either a numpy array or a single value. The single
        value will be broadcasted to the shape of the data table. A use-case
        would be the addition of an 'event' or 'cast' column.

        Parameters
        ----------
        data: np.ndarray | int | float | str | None
            Data to use as array or a value to expand to an array
        metadata: dict
            Metadata for the new parameter (Default value = {})
        name: str
            Name to use for missing metadata values (Default value = "")
        position: str
            The parameter position to add the new one after (Default value = "")

        Returns
        -------
        The new parameter instance.
        """
        if len(metadata) < 5:
            if len(name) > 0:
                metadata = self.add_default_metadata(
                    name=name, metadata=metadata
                )
            else:
                raise ValueError(
                    "Please specify either a name or sufficient metadata"
                )
        if not isinstance(data, np.ndarray):
            data = np.full(
                fill_value=data,
                shape=self.get_full_data_array().shape[0],
            )
        parameter = Parameter(
            data=data, metadata=metadata, bad_flag=self.bad_flag
        )
        self.add_parameter(parameter, position)
        return parameter

    def add_default_metadata(
        self,
        name: str,
        metadata: dict = {},
        list_of_keys: list = [
            "shortname",
            "longinfo",
            "name",
            "metainfo",
            "unit",
        ],
    ) -> dict:
        """
        Fills up missing metadata points with a default value.

        Parameters
        ----------
        name : str
            The value to use as default
        metadata : dict
            The present metadata (Default value = {})
        list_of_keys : list
            The expected metadata keys

        Returns
        -------
        A dictionary with new metadata
        """
        default = map_metadata(name)
        for key in list_of_keys:
            if key not in list(metadata.keys()) and key not in list(
                default.keys()
            ):
                if key in ["metainfo", "unit"]:
                    default[key] = ""
                else:
                    default[key] = name
        return {**metadata, **default}

    def update_spans(self):
        """Updates all spans of the parameters."""
        for parameter in self.get_parameter_list():
            parameter.update_span()

    def get_spans(self) -> list[tuple[int, int]]:
        """Returns all span tuples of the parameters."""
        # update spans first
        self.update_spans()
        return [parameter.span for parameter in self.get_parameter_list()]

    def get_pandas_dataframe(self) -> pd.DataFrame:
        """Returns a pandas DataFrame of the current parameter data."""
        data = np.array(
            [parameter.data for parameter in self.get_parameter_list()]
        ).T
        columns = [parameter.name for parameter in self.get_parameter_list()]
        assert data.shape[1] == len(columns)
        df = pd.DataFrame(data=data, columns=columns)
        for column in df.columns:
            try:
                df[column].astype("float64")
            except (TypeError, ValueError):
                df[columns].astype("str")
        return df

    def with_name_type(self, name_type: str = "shortname"):
        """
        Uses the given name_type as column descriptors.

        Parameters
        ----------
        name_type: str
            The name type to use (Default value = "shortname")
        """
        for parameter in self.get_parameter_list():
            parameter.use_name(name_type)

    def reading_data_header(
        self, header_info: list = []
    ) -> Tuple[dict[str, dict], list[int]]:
        """
        Parsing data table metadata information.

        Parameters
        ----------
        header_info : list:
            The header values from the file (Default value = [])

        Returns
        -------
        Structured data table metadata and a list of duplicate columns.
        """
        table_header = {}
        duplicate_columns = []
        for line in header_info:
            if line.startswith("name"):
                header_meta_info = {}
                # get basic shortname and the full, non-differentiated info
                shortname = longinfo = line_info = line.split("=", 1)[
                    1
                ].strip()
                try:
                    shortname, longinfo = line_info.split(":", 1)
                except IndexError:
                    pass
                finally:
                    shortname = shortname.strip()
                    if shortname in list(table_header.keys()):
                        try:
                            duplicate_columns.append(
                                int(line.split("=", 1)[0].strip().split()[1])
                            )
                        except IndexError as error:
                            logger.error(
                                f"Could not resolve duplicate column: {
                                    shortname
                                }, {error}"
                            )
                    else:
                        header_meta_info["shortname"] = shortname
                        header_meta_info["longinfo"] = longinfo.strip()
                        metainfo = self._extract_data_header_meta_info(
                            longinfo.strip()
                        )
                        header_meta_info = {**header_meta_info, **metainfo}
                        table_header[shortname.strip()] = header_meta_info
            elif line.startswith("interval"):
                self.sample_rate = self.get_sample_rate(
                    line.split("=", 1)[1].strip()
                )

        return table_header, duplicate_columns

    def _extract_data_header_meta_info(self, line: str) -> dict:
        """
        Extracts the individual information bits inside of the header lines.

        Parameters
        ----------
        line : str:
            One header line, trimmed by the 'name =' prefix and the shortname

        Returns
        -------
        A dictionary of data table metadata.
        """
        regex_string = r"(?:(?P<name0>.+),\s(?P<metainfo0>.+)\s\[(?P<unit0>.+)\]|(?P<name2>.+)\s\[(?P<unit2>.+)\]|(?P<name3>.+),\s(?P<metainfo2>.[^\s]+)|(?P<name4>.+))"
        regex_check = re.search(regex_string, line, flags=re.IGNORECASE)
        if regex_check:
            regex_info = dict(regex_check.groupdict())
            regex_info = {
                key[:-1]: value
                for key, value in regex_info.items()
                if value is not None
            }
            if len(regex_info) > 2:
                # check for second sensors and adjust their names
                if regex_info["metainfo"][-1] == "2":
                    regex_info["name"] = regex_info["name"] + " 2"
                    regex_info["metainfo"] = regex_info["metainfo"][:-1]
                    if len(regex_info["metainfo"]) == 0:
                        regex_info.pop("metainfo")
            if regex_info["name"] == "flag":
                regex_info["metainfo"] = regex_info["name"]
                regex_info["unit"] = regex_info["name"]
            return regex_info
        return {}

    def calculate_depth(self, decimals: int = 3) -> bool:
        """
        (Re-)calculates the depth from pressure and latitude.

        Parameters
        ----------
        decimals : int:
            The number of digits to represent the depth with

        Returns
        -------
        A boolean indicating the success of the operation.
        """
        try:
            depth = -gsw.z_from_p(
                self.data["prDM"].data, self.data["latitude"].data
            )
        except (KeyError, ValueError) as error:
            logger.error(f"Could not calculate depth: {error}")
            return False
        self.create_parameter(np.round(depth, decimals=decimals), name="depth")
        return True


class Parameter:
    """
    A representation of one parameter in CTD data.

    Consists of the data and metadata.

    Parameters
    ----------
    data: np.ndarray
        The data array
    metadata: dict
        The metadata information
    bad_flag: float
        The value to consider as bad (Default=-9.990e-29)
    """

    def __init__(
        self,
        data: np.ndarray,
        metadata: dict,
        bad_flag: float = -9.990e-29,
    ) -> None:
        self.data = data
        self.metadata = metadata
        self.name = metadata["shortname"]
        self.param = re.split(r"[,\s]", metadata["name"])[0]
        self.sensor_number = 2 if metadata["name"][-1] == "2" else 1
        self.unit = metadata["unit"]
        self.type = "data" if self.data.dtype in ["float", "int"] else "meta"
        self.bad_flag = bad_flag
        self.parse_to_float()
        self.update_span()
        self.set_output_format()

    def __str__(self) -> str:
        return str(self.metadata["longinfo"])

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        return self.data == other.data

    def __len__(self) -> int:
        return self.data.shape[0]

    def get_pandas_series(self) -> pd.Series:
        """Returns a pandas Series of the current parameter data."""
        return pd.Series(data=self.data, name=self.name)

    def use_name(self, name_type: str = "shortname"):
        """
        Uses the given name as parameter descriptor.

        Parameters
        ----------
        name_type: str
            The name type to use (Default value = "shortname")
        """
        try:
            self.name = self.metadata[name_type]
        except KeyError:
            return

    def parse_to_float(self):
        """Tries to parse the data array type to float."""
        try:
            self.data = self.data.astype("float64")
        except (ValueError, TypeError):
            pass

    def update_span(self):
        """
        Updates the data span.

        Uses the first value if dtype is not numeric.
        """
        if self.data.dtype in ["float64", "int"]:
            try:
                mx = np.ma.masked_array(
                    self.data, mask=self.data == self.bad_flag
                )
                self.span = (np.nanmin(mx), np.nanmax(mx))
            except ValueError:
                self.span = (0, 0)
        else:
            self.span = (self.data[0], self.data[0])

    def set_output_format(self):
        """Sets a parameter-specific number format."""
        if self.name in ["timeU", "flag"]:
            decimal_digits = 0
        elif self.name in [
            "timeS",
            "prDM",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "depSM",
        ]:
            decimal_digits = 3
        elif self.name in ["latitude", "longitude"]:
            decimal_digits = 5
        elif self.param == "Conductivity":
            decimal_digits = 6
        else:
            decimal_digits = 4
        self.output_format = f"{{:.{decimal_digits}f}}"
