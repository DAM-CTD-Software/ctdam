import logging
from datetime import datetime, time
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

from ctdam.parser import DataFile

logger = logging.getLogger(__name__)


class BottleFile(DataFile):
    """
    Class that represents a Sea-Bird Bottle File (.btl) .

    Organizes the files table information into a pandas dataframe. This
    allows the usage of this powerful library for statistics, visualization,
    data manipulation, export, etc.

    Parameters
    ----------
    path_to_file : Path | str
        The path to the .btl file
    only_header : bool
        Whether to only check the header and not parse data
    """

    def __init__(self, path_to_file: Path | str, only_header: bool = False):
        super().__init__(path_to_file, only_header)
        if not only_header:
            self.original_df = self.create_dataframe()
            self.df = self.original_df
            self.setting_dataframe_dtypes()
            self.adding_timestamp_column()

    def create_dataframe(self):
        """
        Creates a dataframe out of the .btl file.

        Handles the double data header correctly.

        """
        # TODO: this needs to be broken down into smaller pieces...
        top_names, bottom_names = self.reading_data_header()
        # creating statistics column to store the row type information:
        # 4 rows per bottle, average, standard deviation, max value, min value
        top_names.append("Statistic")
        # TODO: sexier way to construct dataframe than opening the file a
        # second time
        df: pd.DataFrame = pd.read_fwf(
            self.path_to_file,
            index_col=False,
            skiprows=len(self.header) + 2,
            header=None,
            names=top_names,
        )

        # handling the double row header
        rowtypes = df[df.columns[-1]].unique()

        # TODO: can this be made a little pretier?
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
        """
        Creates a timestamp column that holds both, Date and Time information.
        """
        # constructing timestamp column
        timestamp = []
        for datepoint, timepoint in zip(self.df.Date, self.df.Time):
            timestamp.append(
                datetime.combine(datepoint, time.fromisoformat(str(timepoint)))
            )
        self.df.insert(2, "Timestamp", timestamp)
        self.df.Timestamp = pd.to_datetime(self.df.Timestamp)

    def setting_dataframe_dtypes(self):
        """Sets the types for the column values in the dataframe."""
        # setting dtypes
        # TODO: extending this to the other columns!
        self.df.Date = pd.to_datetime(self.df.Date)
        self.df.Bottle_ID = self.df.Bottle_ID.astype(int)

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
            (Default value = ['avg'])
        statistic_of_interest: Union[list

        str] :
             (Default value = ["avg"])

        Returns
        -------


        """
        df = self.df if df is None else df
        # ensure that the input is a list, so that isin() can do its job
        if isinstance(statistic_of_interest, str):
            statistic_of_interest = [statistic_of_interest]
        self.df = df.loc[df["Statistic"].isin(statistic_of_interest)]

    def reading_data_header(self):
        """
        Identifies and separatly collects the rows that specify the data
        tables headers.

        Parameters
        ----------

        Returns
        -------


        """
        n = 11  # fix column width of a seabird btl file
        top_line = self.data[0]
        second_line = self.data[1]
        top_names = [
            top_line[i : i + n].split()[0]
            for i in range(0, len(top_line) - n, n)
        ]
        bottom_names = [
            second_line[i : i + n].split()[0] for i in range(0, 2 * n, n)
        ]
        return top_names, bottom_names

    def add_station_and_event_column(self):
        event_list = [self.metadata["Station"] for _ in self.data]
        self.df.insert(0, "Event", pd.Series(event_list))

    def add_position_columns(self):
        latitude_list = [self.metadata["GPS_Lat"] for _ in self.data]
        self.df.insert(1, "Latitude", pd.Series(latitude_list))
        longitude_list = [self.metadata["GPS_Lon"] for _ in self.data]
        self.df.insert(2, "Longitude", pd.Series(longitude_list))
