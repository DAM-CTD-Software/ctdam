import logging
import warnings
from copy import copy
from typing import Dict

import numpy as np
import xarray as xr
from scipy.ndimage import convolve1d
from scipy.signal import butter, filtfilt
from scipy.signal.windows import boxcar, triang
from seabirdscientific import processing as sbs_proc

from ctdam import PARAMETER_MAPPING
from ctdam.exceptions import MissingParameterError
from ctdam.proc.module import Module

logger = logging.getLogger(__name__)


class LoopRemoval(Module):
    """Flags pressure loops caused by ship heave."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {},
    ) -> xr.Dataset:
        return super().__call__(ds, arguments, default_values)

    def transformation(self) -> bool:
        """
        Calls the loop removal function and handles the resulting flag values
        for array truncation.

        Returns
        -------
        A boolean to indicate the success of the operation.

        """
        if not self._check_parameter_existence("pressure"):
            raise MissingParameterError(self.name, "pressure")

        self.check_whether_working_on_binned_data()

        pressure = self.ds.pressure.data
        use_jens = self.arguments.pop("use_jens", False)

        if use_jens:
            flag_array = self.jens_loop_removal(
                pressure=pressure,
                sample_interval=1 / self.sample_rate,
                **self.arguments,
            )
        else:
            flag_array = self.time_dependent_loop_removal(
                pressure=pressure, delta=0.01
            )

        self.handle_new_flags(flag_array)

        return True

    def time_dependent_loop_removal(
        self,
        pressure: np.ndarray,
        delta: float,
    ) -> np.ndarray:
        """
        Flag samples where pressure does not increase strictly with time.
        Optionally leaves some room for minor fluctuations.

        A sample is flagged when its pressure does not surpass the maximum
        pressure of every previous measurement (excluding possible minor fluctuations).

        Note take time itself is not required as an arugment as each entry is taken at a discrete timestep
        i.e. relative time can be easily induced

        Parameters

        ----------
        pressure: np.ndarray
            Array of vertical axis values
        delta: float
            Value that take minor fluctuations into account
        """
        flag_bool = np.zeros(len(pressure), dtype=bool)
        current_max = pressure[0]
        for i in range(1, len(pressure)):
            if pressure[i] <= current_max - delta:
                flag_bool[i] = True
            else:
                current_max = pressure[i]
        return flag_bool

    def jens_loop_removal(
        self,
        pressure: np.ndarray,
        sample_interval: float,
        precut_period: int = 5,
        cut_period: int = 10,
        mean_speed_percent: int = 20,
        delay: int = 2,
        filter_order: int = 4,
    ):
        """
        Flag loops in CTD data caused by ship heave.
        Credit: Dr. Jens Faber, IOW.

        Parameters
        ----------
        pressure: np.ndarray
            Array of vertical axis values
        sample_interval: float
            The interval the data has been sampled with
        precut_period: int
            Cutoff period for the pressure (Default value = 5)
        cut_period: int
            Cutoff period for the main filter (Default value = 10)
        mean_speed_percent: int
            Percentage of filtered velocity to use as a threshold (Default value = 20)
        delay: int
            Delay (Default value = 2)
        filter_order: int
            Order of the Butterworth filter (Default value = 4)
        """
        warnings.warn(
            "LoopRemoval is still in an experimental state. Be cautious with the results."
        )
        # Compute vertical velocity
        velocity = np.gradient(pressure) / sample_interval

        # Pre-filtering: Low-pass Butterworth filter
        b, a = butter(
            filter_order, 2 * sample_interval / precut_period, btype="low"
        )
        # Pad the signal
        velocity_padded = np.pad(velocity, (3, 3), mode="edge")
        velocity_filt_pre = filtfilt(b, a, velocity_padded)
        # Remove padding
        velocity_filt_pre = velocity_filt_pre[3:-3]

        # Main filtering: Low-pass Butterworth filter
        b, a = butter(
            filter_order, 2 * sample_interval / cut_period, btype="low"
        )
        # Pad the signal
        velocity_padded = np.pad(velocity_filt_pre, (3, 3), mode="edge")
        velocity_filt = filtfilt(b, a, velocity_padded)
        # Remove padding
        velocity_filt = velocity_filt[3:-3]

        # Flag data where velocity is below the threshold
        flag_bool = velocity < (velocity_filt * mean_speed_percent / 100)

        # Shift the flag array to account for delay
        sample_shift = int(round(delay / sample_interval))
        flag_bool = np.roll(flag_bool, sample_shift)
        # Ensure no flags are set before the delay
        flag_bool[:sample_shift] = False

        return flag_bool


class AlignCTD(Module):
    """
    Align the given parameter columns.
    """

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {"oxygen": 3},
    ) -> xr.Dataset:
        return super().__call__(ds, arguments, default_values)

    def transformation(self) -> bool:
        self.check_whether_working_on_binned_data()
        return_value = True
        for name, value in self.arguments.items():
            value *= self.ds.access.sample_rate
            self.ds[name] = self.ds[name].shift(scan=value)
        return return_value


class WFilter(Module):
    """Apply a signal processing filter to certain data columns."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {
            "pressure": {
                "window_type": "gaussian",
                "window_width": 20,
                "half_width": 0.415,
                "offset": 0,
            },
            "temperature": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "conductivity": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "salinity": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "oxygen": {
                "window_type": "gaussian",
                "window_width": 48,
                "half_width": 1,
                "offset": 0,
            },
            "fluorescence": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "turbidity": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "par": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "spar": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "flowmeter": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
        },
    ) -> xr.Dataset:
        self.default_values = default_values
        return super().__call__(ds, arguments)

    def transformation(self) -> bool:
        """
        Calls window_filter method and handles argument display.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        general_kwargs = {
            "sample_interval": 1 / self.sample_rate,
            "flag_value": self.bad_flag,
        }
        # sanitize user input
        iter_arguments = copy(self.arguments)
        for key, value in iter_arguments.items():
            self.arguments[key.replace(" ", "").lower()] = value
            self.arguments.pop(key)
        new_arguments = {}
        ds = self.ds.copy(deep=True)
        for param, da in ds.data_vars.items():
            try:
                specific_kwargs = self.default_values[param]
            except KeyError:
                specific_kwargs = {}
            if param in self.arguments:
                # use default values of SPAR, to allow the user to not set all
                # 4 values that are necessary to run a wfilter
                specific_kwargs = self.default_values["spar"]
                for key, value in self.arguments[param].items():
                    if key == "window_type":
                        value = value.lower()
                    specific_kwargs[key] = value
            if specific_kwargs:
                # handle dual-sensor case
                if "sensor" in da.dims:
                    for i in [0, 1]:
                        with warnings.catch_warnings(action="ignore"):
                            ds[param].values[:, i] = self.window_filter(
                                data_in=ds[param].values[:, i],
                                **general_kwargs,
                                **specific_kwargs,
                            )

                else:
                    with warnings.catch_warnings(action="ignore"):
                        ds[param].values = self.window_filter(
                            data_in=ds[param].values,
                            **general_kwargs,
                            **specific_kwargs,
                        )
                new_arguments[param] = ", ".join(
                    [str(value) for value in specific_kwargs.values()]
                )

        self.arguments = new_arguments
        self.ds = ds

        return True

    def window_filter(
        self,
        data_in: np.ndarray,
        window_type: str,
        window_width: int,
        sample_interval: float,
        half_width: float = 1.0,
        offset: float = 0.0,
        flag_value: float = -9.99e-29,
    ) -> np.ndarray:
        """
        Filters a dataset by convolving it with an array of weights.

        The available window filter types are boxcar, cosine, triangle,
        gaussian, and median. Refer to the SeaSoft data processing manual
        version 7.26.8, page 108.

        Parameters
        ----------
        data_in: np.ndarray
            Data to be filtered.
        flags: np.ndarray
            Flagged data defined by loop edit.
        window_type: str
            The filter type (boxcar, cosine, triangle, gaussian, or median).
        window_width: int
            Width of the window filter (must be odd).
        sample_interval: float
            Sample interval of the dataset.
        half_width: float
            Width of the Gaussian curve. (Default value = 1.0)
        offset: float
            Shifts the center point of the Gaussian. (Default value = 0.0)
        exclude_flags: bool
            Exclude flagged values from the dataset. (Default value = False)
        flag_value: float
            The flag value in flags. (Default value = -9.99e-29)

        Returns
        -------
        A numpy array of the convolution of data_in and the window filter.
        """
        # Convert flags to NaN for processing
        data = np.where(data_in == flag_value, np.nan, data_in)

        # Define the window filter
        window_start = -(window_width - 1) // 2
        window_end = (window_width - 1) // 2 + 1

        if window_type == "boxcar":
            window = boxcar(window_width)
        elif window_type == "cosine":
            n = np.arange(window_start, window_end)
            window = np.cos((n * np.pi) / (window_width + 1))
        elif window_type == "triangle":
            window = triang(window_width)
        elif window_type == "gaussian":
            phase = offset / sample_interval
            scale = np.log(2) * (2 * sample_interval / half_width) ** 2
            n = np.arange(window_start, window_end)
            window = np.exp(-((n - phase) ** 2) * scale)
        elif window_type == "median":
            pass
        else:
            logger.warning(
                f"No known window_type: {window_type}. Skipping wfilter."
            )
            return data

        padding_size = window_width // 2

        # Pad data for convolution
        data_valid = np.nan_to_num(data)
        data_padded = np.pad(
            data_valid,
            padding_size,
            mode="edge",
        )

        # Handle NaN values: replace with 0 for convolution, then mask later
        nan_mask = np.isnan(data_padded)
        data_filled = np.where(nan_mask, 0, data_padded)

        # Convolve using SciPy's convolve1d (handles edge cases better)
        if window_type == "median":
            # For median, use a sliding window approach (no direct vectorization)
            data_out = np.array(
                [
                    np.nanmedian(data_padded[i : i + window_width])
                    for i in range(len(data))
                ]
            )
        else:
            # Normalize the window
            window_normalized = window / np.sum(window)

            # Convolve
            conv_result = convolve1d(
                data_filled,
                window_normalized,
                mode="constant",
                origin=-(window_width // 2),
            )

            # Restore NaN values where they were in the original data
            data_out = np.where(
                nan_mask[padding_size:-padding_size],
                np.nan,
                conv_result[padding_size:-padding_size],
            )

        return data_out


class CellTM(Module):
    """Fix cell thermal mass errors of the conductivity sensors."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_mapping: dict = {
            "sbe9": (0.03, 7.0),
            "sbe19": (0.04, 8.0),
        },
    ) -> xr.Dataset:
        self.cell_tm_param_mapping = default_mapping
        return super().__call__(ds, arguments)

    def transformation(self) -> bool:
        """
        Call Sea-Birds cell-termal-mass function and convert unit.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        if "alpha" in self.arguments and "beta" in self.arguments:
            self.alpha = self.arguments["alpha"]
            self.beta = self.arguments["beta"]
        else:
            try:
                for key in self.cell_tm_param_mapping:
                    if key in self.ds.attrs["instrument_metadata"].split("\n")[
                        0
                    ].lower().replace(" ", ""):
                        self.alpha, self.beta = self.cell_tm_param_mapping[key]

            except KeyError:
                logger.error(
                    f"No cell_tm parameters for instrument {self.ds.attrs['instrument_metadata'][0][:-10]}. No cell thermal mass correction applied."
                )
            else:
                self.arguments["alpha"] = self.alpha
                self.arguments["beta"] = self.beta
        for index, strand in enumerate(
            [self.ds.access.sensor_strand(number) for number in [1, 2]]
        ):
            if not "conductivity" in strand:
                continue
            # check availability of temperature in this sensor strand
            if not "temperature" in strand:
                continue

            # enforce correct conductivity unit
            unit = strand.conductivity.units
            if unit == "mS/cm":
                conductivity = strand.conductivity / 10.0
            elif unit == "S/m":
                conductivity = strand.conductivity
            else:
                logger.error(f"Unknown conductivity unit {unit}. Aborting.")
                return False
            # seabirds celltm cannot handle nans, setting so bad flag value
            temperature = np.nan_to_num(strand.temperature, nan=self.bad_flag)
            conductivity[conductivity == self.bad_flag] = np.nan
            corrected_conductivity = sbs_proc.cell_thermal_mass(
                temperature_C=temperature,
                conductivity_Sm=conductivity,
                amplitude=self.alpha,
                time_constant=1 / self.beta,
                sample_interval=1 / self.sample_rate,
            )

            if unit == "mS/cm":
                corrected_conductivity *= 10
            self.ds.conductivity.data[:, index - 1] = corrected_conductivity

        return True


class BinAvg(Module):
    """Bin data points in pressure or time bins."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {
            "bin_variable": "pressure",
            "bin_size": 1,
        },
    ) -> xr.Dataset:
        return super().__call__(ds, arguments, default_values)

    def transformation(self) -> bool:
        self.check_whether_working_on_binned_data()
        ds = self.ds.where(self.ds["flag"] == 0.0, drop=True)
        self.flags = []

        bin_variable = self.arguments["bin_variable"]
        bin_size = self.arguments["bin_size"]

        try:
            unit = PARAMETER_MAPPING[bin_variable]["cf"]["unit"]
        except KeyError as error:
            logger.error(f"Unknown bin_variable {bin_variable!r}: {error}")
            return False

        if bin_variable not in self.ds.variables:
            logger.error(
                f"Could not bin {self.ds.attrs.get('path_to_source_file')}: "
                f"bin variable {bin_variable!r} not present "
                f"(available: {sorted(self.ds.variables)})"
            )
            return False

        bin_coord = f"{bin_variable}_bins"
        try:
            ds[bin_coord] = np.round(ds[bin_variable] / bin_size) * bin_size
            ds = ds.set_coords(bin_coord)
            ds = ds.groupby(bin_coord).mean()
            drop_cols = [
                c
                for c in (bin_variable, f"{bin_variable}_qc", "flag")
                if c in ds.variables
            ]
            ds = ds.drop_vars(drop_cols)
        except Exception as error:
            logger.exception(
                f"Could not bin {self.ds.attrs.get('path_to_source_file')}: {error}"
            )
            return False
        ds.attrs["sample_rate"] = f"{bin_size} {unit}"
        self.ds = ds
        return True
