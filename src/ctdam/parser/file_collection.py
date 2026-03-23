from __future__ import annotations

import logging
import warnings
from collections import UserList
from pathlib import Path
from typing import Callable, Type

import numpy as np
import pandas as pd

from ctdam.parser import (
    BottleFile,
    BottleLogFile,
    CnvFile,
    DataFile,
    HexFile,
)
from ctdam.utils import get_unique_sensor_data

logger = logging.getLogger(__name__)


def get_collection(
    path_to_files: Path | str,
    file_suffix: str = "cnv",
    only_metadata: bool = False,
    pattern: str = "",
    sorting_key: Callable | None = None,
) -> Type[FileCollection]:
    """
    Factory to create instances of FileCollection, depending on input type.

    Parameters
    ----------
    path_to_files : Path | str
        The path to the directory to search for files.
    file_suffix : str
        The suffix to search for. (Default value = "cnv")
    only_metadata : bool
        Whether to read only metadata. (Default value = False)
    pattern: str
        A filter for file selection. (Default value = '')
    sorting_key : Callable | None
        A callable that returns the filename-part to use to sort the collection. (Default value = None)
    Returns
    -------
    An instance of FileCollection or one of its children.

    """
    mapping_suffix_to_type = {
        "cnv": CnvCollection,
        "btl": FileCollection,
        "bl": FileCollection,
        "hex": HexCollection,
    }
    file_suffix = file_suffix.strip(".")
    try:
        collection = mapping_suffix_to_type[file_suffix](
            path_to_files, file_suffix, only_metadata, pattern, sorting_key
        )
    except KeyError:
        raise ValueError(f"Unknown input file type: {file_suffix}, aborting.")
    else:
        return collection


class FileCollection(UserList):
    """
    A representation of multiple files of the same kind. These files share
    the same suffix and are otherwise closely connected to each other. A common
    use case would be the collection of CNVs to allow for easier processing or
    integration of field calibration measurements.

    Parameters
    ----------
    path_to_files : Path | str
        The path to the directory to search for files.
    file_suffix : str
        The suffix to search for. (Default value = "cnv")
    only_metadata : bool
        Whether to read only metadata. (Default value = False)
    pattern: str
        A filter for file selection. (Default value = '')
    sorting_key : Callable | None
        A callable that returns the filename-part to use to sort the collection. (Default value = None)
    """

    def __init__(
        self,
        path_to_files: str | Path,
        file_suffix: str,
        only_metadata: bool = False,
        pattern: str = "",
        sorting_key: Callable | None = None,
    ):
        super().__init__()
        self.path_to_files = Path(path_to_files)
        self.file_suffix = file_suffix.strip(".")
        self.pattern = pattern
        self.sorting_key = sorting_key
        self.file_type = self.extract_file_type(self.file_suffix)
        self.individual_file_paths = self.collect_files(
            pattern=pattern,
            sorting_key=sorting_key,
        )
        self.data = self.load_files(only_metadata)
        if not only_metadata:
            self.df_list = self.get_dataframes()
            self.df = self.get_collection_dataframe(self.df_list)

    def __str__(self):
        return "/n".join(self.data)

    def extract_file_type(self, suffix: str) -> Type[DataFile]:
        """
        Determines the file type using the input suffix.

        Parameters
        ----------
        suffix : str
            The file suffix.
        Returns
        -------
        An object corresponding to the given suffix.
        """
        mapping_suffix_to_type = {
            "cnv": CnvFile,
            "btl": BottleFile,
            "bl": BottleLogFile,
            "hex": HexFile,
        }
        file_type = DataFile
        for key, value in mapping_suffix_to_type.items():
            if key == suffix:
                file_type = value
                break
        return file_type

    def collect_files(
        self,
        pattern: str = "",
        sorting_key: Callable | None = lambda file: int(
            file.stem.split("_")[3]
        ),
    ) -> list[Path]:
        """
        Creates a list of target files, recursively from the given directory.
        These can be sorted with the help of the sorting_key parameter, which
        is a Callable that identifies the part of the filename that shall be
        used for sorting.

        Parameters
        ----------
        pattern: str
            A filter for file selection. Is given to rglob. (Default value = '')
        sorting_key : Callable | None
            The part of the filename to use in sorting. (Default value = lambda file: int(file.stem.split("_")[3]))
        Returns
        -------
        A list of all paths found.
        """
        if self.path_to_files.is_file():
            return [self.path_to_files]
        else:
            return sorted(
                self.path_to_files.rglob(f"*{pattern}*{self.file_suffix}"),
                key=sorting_key,
            )

    def load_files(self, only_metadata: bool = False) -> list[DataFile]:
        """
        Creates python instances of each file.

        Parameters
        ----------
        only_metadata : bool
            Whether to load only file metadata. (Default value = False)
        Returns
        -------
        A list of all instances.
        """
        data = []
        for file in self.individual_file_paths:
            try:
                data.append(
                    self.file_type(
                        path_to_file=file,
                        only_header=only_metadata,
                    )
                )
            except TypeError:
                logger.error(
                    f"Could not open file {file} with the type "
                    f"{self.file_type}."
                )
                continue
        return data

    def get_dataframes(
        self,
        event_log: bool = False,
        coordinates: bool = False,
        time_correction: bool = False,
        cast_identifier: bool = False,
    ) -> list[pd.DataFrame]:
        """
        Collects all individual dataframes and allows additional column
        creation.

        Parameters
        ----------
        event_log : bool
            (Default value = False)
        coordinates : bool
            (Default value = False)
        time_correction : bool
            (Default value = False)
        cast_identifier : bool
            (Default value = False)

        Returns
        -------
        A list of the individual pandas DataFrames.
        """
        for index, file in enumerate(self.data):
            if event_log:
                file.add_station_and_event_column()
            if coordinates:
                file.add_position_columns()
            if time_correction:
                file.absolute_time_calculation()
                file.add_start_time()
            if cast_identifier:
                file.add_cast_number(index + 1)
        return [file.df for file in self.data]

    def get_collection_dataframe(
        self, list_of_dfs: list[pd.DataFrame] | None = None
    ) -> pd.DataFrame:
        """
        Creates one DataFrame from the individual ones, by concatenation.

        Parameters
        ----------
        list_of_dfs : list[pd.DataFrame] | None
            A list of the individual DataFrames. (Default value = None)
        Returns
        -------
        A pandas DataFrame representing the whole dataset.
        """
        if not list_of_dfs:
            list_of_dfs = self.get_dataframes()
        if not list_of_dfs:
            raise ValueError("No dataframes to concatenate.")
        df = pd.concat(list_of_dfs, ignore_index=True)
        self.df = df
        return df

    def tidy_collection_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the different dataframe edits to the given dataframe.

        Parameters
        ----------
        df : pd.DataFrame
            A DataFrame to edit.
        Returns
        -------
        The tidied dataframe.
        """
        df = self.use_bad_flag_for_nan(df)
        df = self.set_dtype_to_float(df)
        return self.select_real_scan_data(df)

    def use_bad_flag_for_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Replace all Nan values by the bad flag value, defined inside the files.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to edit.
        Returns
        -------
        The edited DataFrame.
        """
        bad_flags = set()
        for file in self.data:
            for line in file.data_table_description:
                if line.startswith("bad_flag"):
                    flag = line.split("=")[1].strip()
                    bad_flags.add(flag)
        for flag in bad_flags:
            df.replace(to_replace=flag, value=np.nan, inplace=True)
        return df

    def set_dtype_to_float(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Use the float-dtype for all DataFrame columns.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to edit.
        Returns
        -------
        The edited DataFrame.
        """
        for parameter in df.columns:
            if parameter in ["datetime"]:
                continue
            df[parameter] = df[parameter].astype("float")
            continue
        return df

    def select_real_scan_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop data rows have no 'Scan' value, if that column exists.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to edit.
        Returns
        -------
        The edited DataFrame.
        """
        try:
            scan_column = [
                c for c in df.columns if c.lower().startswith("scan")
            ][0]
        except IndexError:
            return df
        else:
            df = df.loc[df[scan_column].notna()]
        return df

    def to_csv(self, file_name):
        """
        Writes a csv file with the given filename.

        Parameters
        ----------
        file_name :
            The new csv file name.
        """
        self.df.to_csv(file_name)


class CnvCollection(FileCollection):
    """
    Specific methods to work with collections of .cnv files.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        if len(args) < 3 and "file_suffix" not in kwargs:
            kwargs["file_suffix"] = "cnv"
        super().__init__(*args, **kwargs)
        self.data_meta_info = self.get_data_table_meta_info()
        self.sensor_data = get_unique_sensor_data(
            [file.sensors for file in self.data]
        )
        self.array = self.get_array()
        self.processing_steps = self.get_processing_steps()

    def get_dataframes(
        self,
        event_log: bool = False,
        coordinates: bool = False,
        time_correction: bool = False,
        cast_identifier: bool = False,
    ) -> list[pd.DataFrame]:
        """
        Collects all individual dataframes and allows additional column
        creation.

        Parameters
        ----------
        event_log : bool
            (Default value = False)
        coordinates : bool
            (Default value = False)
        time_correction : bool
            (Default value = False)
        cast_identifier : bool
            (Default value = False)
        Returns
        -------
        A list of the individual pandas DataFrames.
        """
        for index, file in enumerate(self.data):
            if event_log:
                file.add_station_and_event_column()
            if coordinates:
                file.add_position_columns()
            if time_correction:
                file.absolute_time_calculation()
                file.add_start_time()
            if cast_identifier:
                file.add_cast_number(index + 1)
        return [file.create_dataframe() for file in self.data]

    def get_data_table_meta_info(self) -> list[dict]:
        """
        Ensures the same data description in all input cnv files and returns
        it.
        Acts as an early alarm when working on different kinds of files, which
        cannot be concatenated together.

        Returns
        -------
        A list of dictionaries that represent the data column information.
        """
        all_column_descriptions = [
            file.parameters.get_metadata() for file in self.data
        ]
        for index, info in enumerate(all_column_descriptions):
            if all_column_descriptions[0] != info:
                for expected, real in zip(
                    all_column_descriptions[0].items(), info.items()
                ):
                    # allow difference in latitude inside depth
                    if expected[0] == "depSM":
                        if real[0] != "depSM":
                            raise AssertionError(
                                f"Data files {self.data[0].path_to_file} and {self.data[index].path_to_file} differ in:\n{expected} and {real}"
                            )

                    elif expected != real:
                        warnings.warn(
                            f"Data files {self.data[0].path_to_file} and {self.data[index].path_to_file} differ in:\n{expected} and {real}"
                        )

        return all_column_descriptions[0]

    def get_array(self) -> np.ndarray:
        """
        Creates a collection array of all individual file arrays.

        Returns
        -------
        A numpy array, representing the data of all input files.
        """
        return np.concatenate(
            [file.parameters.get_full_data_array() for file in self.data]
        )

    def get_processing_steps(self) -> list:
        """
        Checks the processing steps in the different files for consistency.
        Returns the steps of the first file, which should be the same as for
        all other files.

        Returns
        -------
        A list of ProcessingSteps.
        """
        individual_processing_steps = [
            file.processing_steps.modules for file in self.data
        ]
        for index, step_info in enumerate(individual_processing_steps):
            if step_info != individual_processing_steps[0]:
                message = f"The processing steps conducted on these files differ. First occurence between index 0 and {index}."
                warnings.warn(message)
                logger.warning(message)
        return individual_processing_steps[0]


class HexCollection(FileCollection):
    """
    Specific methods to work with collections of .hex files.

    Especially concerned with the detection of corresponding .XMLCON files.
    """

    def __init__(
        self,
        *args,
        xmlcon_pattern: str = "",
        path_to_xmlcons: Path | str = "",
        **kwargs,
    ):
        if len(args) < 3 and "file_suffix" not in kwargs:
            kwargs["file_suffix"] = "hex"
        # force only_metadata, as the hex data cannot be put into a DataFrame
        kwargs["only_metadata"] = True
        super().__init__(*args, **kwargs)
        if not xmlcon_pattern:
            xmlcon_pattern = self.pattern
        self.xmlcon_pattern = xmlcon_pattern
        self.path_to_xmlcons = (
            Path(path_to_xmlcons)
            if path_to_xmlcons
            else self.path_to_files.parent
        )
        self.xmlcons = self.get_xmlcons()

    def get_xmlcons(self) -> list[str]:
        """
        Returns all .xmlcon files found inside the root directory and its
        children, matching a given pattern.

        Does use the global sorting_key to attempt to also sort the xmlcons the
        same way.
        This is meant to be used in the future for a more specific hex-xmlcon
        matching.

        Returns
        -------
        A list of the found xmlcon filenames.
        """
        try:
            xmlcons = [
                Path(xmlcon_path).stem
                for xmlcon_path in sorted(
                    self.path_to_xmlcons.rglob(
                        f"*{self.xmlcon_pattern}*.XMLCON"
                    ),
                    key=self.sorting_key,
                )
            ]
        except (KeyError, IndexError):
            xmlcons = [
                Path(xmlcon_path).stem
                for xmlcon_path in self.path_to_xmlcons.rglob(
                    f"*{self.xmlcon_pattern}*.XMLCON"
                )
            ]
        return xmlcons
