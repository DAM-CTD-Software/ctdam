import importlib.metadata
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ctdam.parser import CnvFile
from ctdam.parser.ctddata import CTDData
from ctdam.proc.utils import BinnedDataError

logger = logging.getLogger(__name__)


class Module(ABC):
    """
    An interface to implement new processing modules against.

    Is meant to perform and unify all the necessary work that is needed to
    streamline processing on Sea-Bird CTD data. Implementing classes should
    only overwrite the transformation method, that does the actual altering of
    the data. All other organizational overhead should be covered by this
    interface. This includes parsing to .cnv output with correct handling of
    the metadata header.
    """

    def __init__(self) -> None:
        self.parent_module = "ctdam"
        self.info = self.__doc__
        self.name = self.__class__.__name__.lower()

    def __call__(
        self,
        arguments: dict,
        default_values: dict = {},
        output_name: str | None = None,
    ) -> None | CnvFile | CTDData | pd.DataFrame | np.ndarray:
        if "file_suffix" in arguments:
            self.file_suffix = arguments.pop("file_suffix")
        else:
            self.file_suffix = False
        self.arguments = {**default_values, **arguments}
        self.output_name = output_name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.__str__()

    def add_processing_metadata(self):
        """
        Parses the module processing information into cnv-compliant metadata
        lines.

        These take on the form of {MODULE_NAME}_{KEY} = {VALUE} for every
        key-value pair inside of the given dictionary with the modules
        processing info.

        """
        # if isinstance(self.cnv, CnvFile):
        if hasattr(self, "processing_steps"):
            # general header for every module
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y.%m.%d %H:%M:%S"
            )
            try:
                version = (
                    f", v{importlib.metadata.version(self.parent_module)}"
                )
            except Exception:
                version = ""
            self.processing_steps.add_info(
                module=self.name,
                key="metainfo",
                value=f"{timestamp}, {self.parent_module} python package{version}",
            )
            for key, value in self.arguments.items():
                if key == "file_suffix":
                    continue
                self.processing_steps.add_info(
                    module=self.name,
                    key=key,
                    value=value,
                )
        else:
            logger.error(
                "Cannot write processing metainfo without any cnv source."
            )

    def load_file(self, file_path: Path) -> CnvFile:
        """
        Loads the target files information into an CnvFile instance.

        Parameters
        ----------
        file_path: Path :
            Path to the target file.

        Returns
        -------
        CnvFile object representing the file in the file system.

        """
        return CnvFile(file_path)

    @abstractmethod
    def to_cnv(self):
        pass


class ArrayModule(Module):
    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_values: dict = {},
        original_input_path: Path | str | None = None,
        bad_flag: float = -9.990e-29,
    ) -> None | CnvFile | CTDData:
        super().__call__(arguments, default_values, output_name)
        if original_input_path:
            self.original_input_path = Path(original_input_path)
        if isinstance(input, Path | str):
            self.ctd_data = CnvFile(
                input, create_dataframe=False
            ).to_ctd_data()
            self.original_input_path = Path(input)
        elif isinstance(input, CnvFile):
            self.ctd_data = input.to_ctd_data()
            self.original_input_path = input.path_to_file
        elif isinstance(input, CTDData):
            self.ctd_data = input
        else:
            raise TypeError(f"Incorrect input type: {type(input)}. Aborting.")
        self.processing_steps = self.ctd_data.processing_steps
        self.sample_rate = self.ctd_data.sample_rate
        self.bad_flag = bad_flag
        self.create_flag_array_if_missing()
        self.flags = self.ctd_data["flag"].data.astype(bool)
        self.ran_processing = self.transformation()
        try:
            self.ctd_data["flag"].data = self.flags.astype(float)
        except KeyError:
            pass
        if self.ran_processing:
            self.add_processing_metadata()
        if self.file_suffix:
            output = "cnv"
        if output.lower() in ("cnv", "file"):
            self.to_cnv()
        return self.ctd_data

    @abstractmethod
    def transformation(self) -> bool:
        pass

    def get_array(self) -> np.ndarray:
        return self.ctd_data.get_full_data_array()

    def get_data_size(self) -> int:
        return self.get_array().shape[0]

    def create_flag_array_if_missing(self):
        if self._check_parameter_existence("flag"):
            return
        self.ctd_data.create_parameter(
            data=np.zeros(self.get_data_size()), name="flag"
        )

    def handle_new_flags(self, new_flag_array: np.ndarray):
        # print out the number of flagged data rows
        new_flag_count = new_flag_array.sum()
        row_count = self.get_data_size()
        self.arguments["bad_rows"] = f"{new_flag_count} of {row_count} ({
            new_flag_count / row_count:1.2f})"
        # incorporate the new flags
        self.flags |= new_flag_array

    def check_whether_working_on_binned_data(self):
        if self.ctd_data.binned:
            raise BinnedDataError(
                file_name=self.ctd_data.file_name,
                step_name=self.name,
            )

    def _check_parameter_existence(
        self, parameter: str, shortname: bool = True
    ) -> bool:
        """
        Helper method to ensure parameter presence in input data before
        attempting the transformation.

        Parameters
        ----------
        parameter: str :
            The parameter to check for.

        Returns
        -------
        Whether the parameter is present inside of the cnv parameters or not.

        """
        if shortname:
            return parameter in self.ctd_data.parameters
        else:
            return parameter in [p.param for p in self.ctd_data]

    def to_cnv(self):
        if not self.ctd_data:
            return
        self.ctd_data.parameters.full_data_array = self.array
        if self.file_suffix:
            if self.output_name:
                output_name = Path(self.output_name)
                stem = output_name.stem
                self.output_name = output_name.with_stem(
                    stem + self.file_suffix
                )
            else:
                self.output_name = self.ctd_data.path_to_file.with_stem(
                    self.ctd_data.file_name + self.file_suffix
                )
        self.ctd_data.to_cnv(self.output_name)


class DataFrameModule(Module):
    def __call__(
        self,
        input: Path | str | CnvFile | pd.DataFrame | np.ndarray,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
    ) -> None | CnvFile | pd.DataFrame | np.ndarray:
        super().__call__(arguments, output_name)
        if isinstance(input, Path | str):
            self.cnv = self.load_file(Path(input))
            self.df = self.cnv.df
        elif isinstance(input, CnvFile):
            self.cnv = input
            self.df = self.cnv.df
        elif isinstance(input, pd.DataFrame):
            self.cnv = None
            self.df = input
        else:
            raise TypeError(f"Incorrect input type: {type(input)}. Aborting.")
        self.df = self.transformation()
        self.add_processing_metadata()
        if output.lower() in ("cnv", "file"):
            self.to_cnv()
            return None
        elif output.lower() in ("internal", "cnvobject") and isinstance(
            self.cnv, CnvFile
        ):
            return self.cnv
        else:
            return self.df

    @abstractmethod
    def transformation(self) -> pd.DataFrame:
        """
        The actual data transformation on the CTD data.

        Needs to be implemented by the implementing classes.
        """
        df = self.df
        return df

    def _check_parameter_existence(self, parameter: str) -> bool:
        """
        Helper method to ensure parameter presence in input data before
        attempting the transformation.

        Parameters
        ----------
        parameter: str :
            The parameter to check for.

        Returns
        -------
        Whether the parameter is present inside of the cnv dataframe or not.

        """
        # ensure shortnames as column names
        self.df.meta.header_detail = "shortname"
        return parameter in self.df.columns

    def to_cnv(
        self,
        additional_data_columns: list[str] = [],
        custom_data_columns: list | None = None,
    ):
        """
        Writes the internal CnvFile instance to disk.

        Uses the CnvFile's output parser for that and organizes the different
        bits of information for that.

        Parameters
        ----------
        additional_data_columns: list[str] :
            A list of columns that in addition to the ones inside the original
            dataframe.
             (Default value = [])
        custom_data_columns: list | None :
            A list of coulumns that will exclusively used to select the data
            items for the output .cnv .
             (Default value = None)

        """
        if isinstance(self.cnv, CnvFile):
            if custom_data_columns:
                header_list = custom_data_columns
            else:
                header_list = [
                    header[self.cnv.df.meta.header_detail]
                    for header in list(self.cnv.df.meta.metadata.values())
                ]
            self.cnv.df = self.df
            self.cnv.to_cnv(
                file_name=self.output_name,
                header_list=[*header_list, *additional_data_columns],
            )
        else:
            logger.error("Cannot write to cnv without any cnv as source.")

    def to_csv(self):
        """Writes the dataframe as .csv to disk."""
        try:
            self.df.to_csv()
        except IOError as error:
            logger.error(f"Failed to write dataframe to csv: {error}")


class MissingParameterError(Exception):
    """A custom error to throw when necessary parameters are missing from the
    input .cnv file."""

    def __init__(self, step_name: str, parameter_name: str):
        super().__init__(
            f"Could not run processing step {
                step_name
            } due to a missing parameter: {parameter_name}"
        )
