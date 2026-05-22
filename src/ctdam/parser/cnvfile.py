import logging
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from ctdam.parser import CnvProcessingSteps, DataFile, Parameters

logger = logging.getLogger(__name__)


class CnvFile(DataFile):
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
    create_dataframe: bool
        Whether to create a pandas DataFrame from the data table.
    absolute_time_calculation: bool
        Whether to use a real timestamp instead of the second count
    event_log_column: bool
        Whether to add a station and device event column from DSHIP
    coordinate_columns: bool
        Whether to add longitude and latitude from the extra metadata header
    """

    def __init__(
        self,
        path_to_file: Path | str,
        only_header: bool = False,
        create_dataframe: bool = False,
        absolute_time_calculation: bool = False,
        event_log_column: bool = False,
        coordinate_columns: bool = False,
    ):
        super().__init__(path_to_file, only_header)
        self.processing_steps = self.get_processing_step_infos()
        self.parameters = Parameters(
            self.data, self.data_table_description, only_header
        )
        if not only_header:
            self.check_and_add_default_parameters()
        if create_dataframe:
            self.df = self.create_dataframe()
        if absolute_time_calculation:
            self.absolute_time_calculation()
        if event_log_column:
            self.add_station_and_event_column()
        if coordinate_columns:
            self.add_position_columns()

    def check_and_add_default_parameters(self):
        sample_interval = 1 / self.parameters.sample_rate
        data_mapping = {
            "timeS": np.arange(
                0,
                sample_interval * self.parameters.get_data_length(),
                sample_interval,
            ),
            "latitude": self.start_position[0],
            "longitude": self.start_position[1],
        }
        for param in data_mapping.keys():
            if param in self.parameters:
                continue
            self.parameters.create_parameter(
                data=data_mapping[param],
                name=param,
            )

    def create_dataframe(self) -> pd.DataFrame:
        """
        Plain dataframe creator.
        """
        self.df = self.parameters.get_pandas_dataframe()
        return self.df

    def absolute_time_calculation(self) -> bool:
        """
        Replaces the basic cnv time representation of counting relative to the
        casts start point, by a unix timestamp.

        A new parameter column, 'timeU', will be created.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        if not self.start_time:
            return False
        if "timeS" in self.parameters.keys():
            data = [
                timedelta(seconds=float(time))
                for time in self.parameters["timeS"].data
            ]
        elif "timeJ" in self.parameters.keys():
            data = [
                timedelta(days=float(time))
                for time in self.parameters["timeJ"].data
            ]
        else:
            return False
        self.parameters.create_parameter(
            name="timeU",
            data=np.array(
                [(self.start_time + d).timestamp() for d in data]
            ).astype("int"),
        )
        return True

    def add_start_time(self) -> bool:
        """
        Create a parameter column holding the start time.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        if self.start_time:
            self.parameters.create_parameter(
                name="start_time",
                data=str(self.start_time),
            )
            return True
        return False

    def get_processing_step_infos(self) -> CnvProcessingSteps:
        """
        Collects the individual validation modules and their respective
        information, usually present in key-value pairs.
        """
        return CnvProcessingSteps(self.processing_info)

    def df2cnv(self, df: pd.DataFrame | None = None) -> list:
        """
        Parses a pandas dataframe into a list that represents the lines inside
        of a cnv data table.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to export, default is self.df

        Returns
        -------
        A list of lines in the cnv data table format.
        """
        df = df if isinstance(df, pd.DataFrame) else self.df
        cnv_out = []
        for _, row in df.iterrows():
            cnv_like_row = "".join(
                (lambda column: f"{str(column):>11}")(value) for value in row
            )
            cnv_out.append(cnv_like_row + "\r\n")
        return cnv_out

    def array2cnv(self) -> list:
        """
        Parses a numpy array into the .cnv data format.

        Delegates to the CTDData method of the same name.

        Returns
        ----------
        A list that represents the rows of the .cnv data format.
        """
        ctddata = self.to_ctd_data()
        return ctddata.array2cnv()

    def to_cnv(self, file_name: Path | str = ""):
        """
        Writes the data and metadata inside of this instance as new .cnv
        file to disk.

        Delegates to the CTDData method of the same name.

        Parameters
        ----------
        file_name: Path
            The new file name to use for writing
        """
        ctddata = self.to_ctd_data()
        ctddata.to_cnv(file_name)

    def to_ctd_data(self):
        """
        Create a CTDData instance using the information inside this .cnv
        file instance.

        Returns
        ----------
        The CTDData representation of this file.
        """
        from ctdam.parser.ctddata import CTDData

        ctd_data = CTDData(
            parameters=self.parameters,
            metadata_source=self,
        )

        return ctd_data

    def _update_header(self):
        """Re-creates the cnv header."""
        self.data_table_description = self.parameters._form_data_table_info()
        self.processing_info = self.processing_steps._form_processing_info()
        self.header = [
            *[f"* {data}" for data in self.sbe9_data[:-1]],
            *[
                f"** {key} = {value}\r\n" if value else f"** {key}\r\n"
                for key, value in self.metadata.items()
            ],
            f"* {self.sbe9_data[-1]}",
            *[f"# {data}" for data in self.data_table_description],
            *[f"# {data}" for data in self.sensor_data],
            *[f"# {data}" for data in self.processing_info],
            "*END*\r\n",
        ]
        self.data = self.array2cnv()
        self.file_data = [*self.header, *self.data]

    def add_processing_metadata(self, module: str, key: str, value: str):
        """
        Adds new processing lines to the list of processing module information

        Parameters
        ----------
        module: str
            The name of the processing module
        key: str
            The description of the value
        value: str
            The information

        """
        self.processing_steps.add_info(module, key, value)
        self._update_header()

    def add_station_and_event_column(self) -> bool:
        """
        Adds a column with the DSHIP station and device event numbers to the
        dataframe. These must be present inside the extra metadata header.
        """
        if "Station" in self.metadata:
            data_value = self.metadata["Station"]
            return_value = True
        else:
            data_value = None
            return_value = False
        self.parameters.create_parameter(
            data=data_value,
            name="Event",
        )
        return return_value

    def add_position_columns(self) -> bool:
        """
        Adds parameter columns with the longitude and latitude information.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        if ("latitude" or "longitude") in [
            k.lower() for k in self.parameters.keys()
        ]:
            return True
        if ("GPS_Lat" and "GPS_Lon") in self.metadata:
            self.parameters.create_parameter(
                data=self.metadata["GPS_Lat"],
                name="Latitude",
            )
            self.parameters.create_parameter(
                data=self.metadata["GPS_Lon"],
                name="Longitude",
            )
            return True
        else:
            return False

    def add_cast_number(self, number: int | None = None) -> bool:
        """
        Adds a parameter column holding the cast number inside a cruise.

        Kept for legacy compatibility.

        Parameters
        ----------
        number: int
            The cast number of this files cast

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        if ("Cast" in self.metadata.keys()) and (not number):
            number = int(self.metadata["Cast"])
        if number:
            self.parameters.create_parameter(
                data=number,
                name="Cast",
            )
            return True
        return False
