import logging
import re
from datetime import datetime

import pandas as pd

from ctdam.parser import DataFile

logger = logging.getLogger(__name__)


class BottleLogFile(DataFile):
    """Bottle Log file (.bl) representation, that extracts the three different data
    types from the file: reset time and the table with bottle IDs and
    corresponding data ranges.

    Parameters
    ----------
    path_to_file : Path | str
        Path to .bl file
    create_dataframe : bool
        Whether to parse as dataframe
    """

    def __init__(self, path_to_file, create_dataframe=False):
        super().__init__(path_to_file)
        self.reset_time = self.obtaining_reset_time()
        self.origin_cnv = self.raw_file_data[0].strip()
        self.data = self.data_whitespace_removal()

        if create_dataframe:
            self.original_df = self.create_dataframe()
            self.df = self.original_df
        else:
            self.data_list = self.create_list()

    def data_whitespace_removal(self) -> list:
        """Strips the input from whitespace characters, in this case especially
        newline characters.

        Parameters
        ----------

        Returns
        -------
        the original data stripped off the whitespaces

        """
        temp_data = []
        for line in self.raw_file_data[2:]:
            temp_data.append(line.strip())
        return temp_data

    def obtaining_reset_time(self) -> datetime:
        """Reading reset time with small input check.

        Parameters
        ----------

        Returns
        -------
        a datetime.datetime object of the device reset time

        """

        regex_check = re.search(
            r"RESET\s(\w{3}\s\d+\s\d{4}\s\d\d:\d\d:\d\d)",
            self.raw_file_data[1],
        )
        if regex_check:
            return datetime.strptime(regex_check.group(1), "%b %d %Y %H:%M:%S")
        else:
            error_message = """BottleLogFile is not formatted as expected:
                Reset time could not be extracted."""
            logger.error(error_message)
            raise IOError(error_message)

    def create_list(self) -> list:
        """Creates a list of usable data from the list specified in self.data.
        the list consists of: an array of ID's representing the bottles, the date and time of the data sample
        and the lines of the cnv corresponding to the bottles

        Parameters
        ----------

        Returns
        -------
        a list representing the bl files table information
        """
        content_array = []
        for i in range(len(self.data)):
            bottles = [int(x) for x in self.data[i].split(",")[:2]]
            date = self.convert_date(self.data[i].split(",")[2])
            lines = tuple([int(x) for x in self.data[i].split(",")[3:]])

            content_array.append([bottles, date, lines])

        return content_array

    def convert_date(self, date: str):
        """
        Converts the Dates of the .bl files to an ISO 8601 standard

        Parameters
        ----------
        date : str
            The date to convert

        Returns
        -------
        a string with the date in the form of "yymmddThhmmss"
        """
        date = date.strip()
        month_list = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        month_ind = month_list.index(date.split(" ")[0]) + 1
        if month_ind < 10:
            month = "0" + str(month_ind)
        else:
            month = str(month_ind)
        day = date.split(" ")[1]
        year = (date.split(" ")[2])[2:]
        time = date.split(" ")[3].replace(":", "")
        return year + month + day + "T" + time

    def create_dataframe(self) -> pd.DataFrame:
        """Creates a dataframe from the list specified in self.data.

        Parameters
        ----------

        Returns
        -------
        a pandas.Dataframe representing the bl files table information
        """
        data_lists = []
        for line in self.data:
            inner_list = line.split(",")
            # dropping first column as its the index
            data_lists.append(inner_list[1:])
        df = pd.DataFrame(data_lists)
        df.columns = ["Bottle ID", "Datetime", "start_range", "end_range"]
        return df
