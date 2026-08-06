import logging
from abc import ABC, abstractmethod

import numpy as np
import xarray as xr

from ctdam.exceptions import BinnedDataError

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

    Parameters
    ----------
    input: Path | str | CnvFile | CTDData
        The data input
    arguments: dict = {}
        The arguments to run the module with
    default_values: dict
        The default arguments, if any
    """

    bad_flag: float = -9.990e-29

    def __init__(self) -> None:
        self.parent_module = "ctdam"
        self.info = self.__doc__
        self.name = self.__class__.__name__.lower()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {},
    ) -> xr.Dataset:
        self.arguments = {**default_values, **arguments}
        self.ds = ds
        self.sample_rate = self.ds.access.sample_rate
        self.create_flag_array_if_missing()
        self.flags = self.ds.flag.data.astype(bool)
        self.ran_processing = self.transformation()
        if len(self.flags) > 0:
            self.ds.flag.data = self.flags.astype(float)
        if self.ran_processing:
            self.add_processing_metadata()
        return self.ds

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
        for key, value in self.arguments.items():
            self.ds.add.processing_metadata(
                module=self.name,
                key=key,
                value=value,
            )

    @abstractmethod
    def transformation(self) -> bool:
        pass

    def create_flag_array_if_missing(self):
        """Check flag array presence and create, if not found."""
        if self._check_parameter_existence("flag"):
            return
        self.ds.add.parameter(data=np.zeros(self.ds.access.size), name="flag")

    def handle_new_flags(self, new_flag_array: np.ndarray):
        """
        Write number of flagged rows to metadata info and concatenate flags.

        Parameters
        ----------
        new_flag_array : np.ndarray
            The array of new flags
        """
        # print out the number of flagged data rows
        new_flag_count = new_flag_array.sum()
        row_count = self.ds.access.size
        self.arguments["bad_rows"] = f"{new_flag_count} of {row_count} ({
            new_flag_count / row_count:1.2f})"
        # incorporate the new flags
        self.flags |= new_flag_array

    def check_whether_working_on_binned_data(self):
        """Raise error when working with binned data."""
        if self.ds.access.binned:
            raise BinnedDataError(
                file_name=self.ds.attrs["path_to_source_file"],
                step_name=self.name,
            )

    def _check_parameter_existence(self, parameter: str) -> bool:
        """
        Helper method to ensure parameter presence in input data before
        attempting the transformation.

        Parameters
        ----------
        parameter: str
            The parameter to check for.

        Returns
        -------
        Whether the parameter is present inside of the cnv parameters or not.

        """
        return parameter in self.ds
