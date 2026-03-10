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
    path_to_file: Path | str:
        the path to the file
    only_header: bool :
        Whether to stop reading the file after the metadata header.
    create_dataframe: bool :
        Whether to create a pandas DataFrame from the data table.
    absolute_time_calculation: bool:
        whether to use a real timestamp instead of the second count
    event_log_column: bool:
        whether to add a station and device event column from DSHIP
    coordinate_columns: bool:
        whether to add longitude and latitude from the extra metadata header

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
        if create_dataframe:
            self.df = self.create_dataframe()
        if absolute_time_calculation:
            self.absolute_time_calculation()
        if event_log_column:
            self.add_station_and_event_column()
        if coordinate_columns:
            self.add_position_columns()

    def create_dataframe(self) -> pd.DataFrame:
        """
        Plain dataframe creator.
        """
        self.df = self.parameters.get_pandas_dataframe()
        return self.df

    def absolute_time_calculation(self) -> bool:
        """
        Replaces the basic cnv time representation of counting relative to the
        casts start point, by real UTC timestamps.
        This operation will act directly on the dataframe.

        """
        time_parameter = None
        for parameter in self.parameters.keys():
            if parameter.lower().startswith("time"):
                time_parameter = parameter
        if time_parameter and self.start_time:
            self.parameters.create_parameter(
                name="datetime",
                data=np.array(
                    [
                        timedelta(days=float(time)) + self.start_time
                        if time_parameter == "timeJ"
                        else timedelta(seconds=float(time)) + self.start_time
                        for time in self.parameters[time_parameter].data
                    ],
                    dtype=str,
                ),
            )
            return True
        return False

    def add_start_time(self) -> bool:
        """
        Adds the Cast start time to the dataframe.
        Necessary for joins on the time.
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
        df: DataFrame to export, default is self.df

        Returns
        -------
        a list of lines in the cnv data table format

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
        result = []
        for row in self.parameters.full_data_array:
            formatted_row = "".join(str(elem).rjust(11) for elem in row)
            result.append(formatted_row + "\r\n")
        return result

    def to_cnv(
        self,
        file_name: Path | str | None = None,
        use_dataframe: bool = False,
    ):
        """
        Writes the values inside of this instance as a new cnv file to disc.

        Parameters
        ----------
        file_name: Path:
            the new file name to use for writing
        use_current_df: bool:
            whether to use the current dataframe as data table
        use_current_validation_header: bool:
            whether to use the current processing module list
        header_list: list:
            the data columns to use for the export

        """
        file_name = self.path_to_file if file_name is None else file_name
        # content construction
        if use_dataframe:
            data = self.df2cnv()
        else:
            data = self.array2cnv()
        self._update_header()
        self.file_data = [*self.header, *data]
        # writing content out
        try:
            with open(file_name, "w", encoding="latin-1") as file:
                for line in self.file_data:
                    file.write(line)

        except IOError as error:
            logger.error(f"Could not write cnv file: {error}")

    def to_ctd_data(self):
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
        module: str :
            the name of the processing module
        key: str :
            the description of the value
        value: str :
            the information

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
        Adds a column with the longitude and latitude to the dataframe.
        These must be present inside the extra metadata header.

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
        Adds a column with the cast number to the dataframe.

        Parameters
        ----------
        number: int:
            the cast number of this files cast

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
