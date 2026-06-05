import logging
import math
import warnings
from copy import copy
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from scipy.ndimage import convolve1d
from scipy.signal import butter, correlate, filtfilt, find_peaks
from scipy.signal.windows import boxcar, triang
from seabirdscientific import processing as sbs_proc

from ctdam.exceptions import MissingParameterError
from ctdam.parser import CnvFile, CTDData, Parameter
from ctdam.proc.module import ArrayModule

logger = logging.getLogger(__name__)


class LoopRemoval(ArrayModule):
    """Flags pressure loops caused by ship heave."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_values: dict = {
            "precut_period": 5,
            "cut_period": 10,
            "mean_speed_percent": 30,
            "delay": 2,
            "filter_order": 4,
            "use_jens": False,
        },
        **kwargs,
    ) -> None | CnvFile | CTDData:
        return super().__call__(
            input, arguments, output, output_name, default_values
        )

    def transformation(self) -> bool:
        """
        Calls the loop removal function and handles the resulting flag values
        for array truncation.

        Returns
        -------
        A boolean to indicate the success of the operation.

        """
        if not self._check_parameter_existence("prDM"):
            logger.error("Failed, not finding pressure")
            return False

        self.check_whether_working_on_binned_data()

        pressure = self.ctd_data["prDM"].data
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


class AlignCTD(ArrayModule):
    """
    Align the given parameter columns.

    Given a measurement parameter in parameters, the column will be shifted
    by either, a float amount that is given as value, or, by a calculated
    amount, using cross-correlation between the high-frequency components of
    the temperature and the target parameters.
    The returned numpy array will thus feature the complete CnvFile data,
    with the columns shifted to their correct positions.
    """

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_values: dict = {
            "Oxygen": 3,
            "minimum_correlation": 0.1,
            "default_shift": 3,
        },
        **kwargs,
    ) -> None | CnvFile | CTDData:
        return super().__call__(
            input, arguments, output, output_name, default_values
        )

    def transformation(self) -> bool:
        """
        Performs the base logic of distinguishing whether to use given values
        or compute a delay.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        self.check_whether_working_on_binned_data()
        return_value = False
        new_parameter_metadata = {}
        for key, value in self.handle_parameter_input(self.arguments).items():
            # key is something like oxygen1 or oxygen2
            # value is either None or a numerical value in string or other form
            target_parameters = [
                param
                for param in self.ctd_data.get_parameter_list()
                if (param.param.lower().startswith(key[:-1]))
                and (str(int(key[-1]) - 1) in param.name)
            ]
            # if there are no measurement parameters of the given key inside
            # the cnv file, remove the key from the input, to avoid printing
            # that key to the output files header
            if len(target_parameters) == 0:
                continue
            # if no shift value given, estimate it
            if not value:
                value, correlation_value = self.estimate_sensor_delay(
                    delayed_parameter=target_parameters[0],
                    margin=len(self.ctd_data.get_full_data_array()) // 4,
                )
                correlation_string = f", with PCC: {correlation_value}"
                if not self.check_correlation_result(
                    value,
                    correlation_value,
                    self.arguments["minimum_correlation"],
                ):
                    correlation_string = f", default value. Calculated delay: {str(float('{:.2f}'.format(value / self.sample_rate)))} PCC: {correlation_value}"
                    # set to a default value
                    value = self.arguments["default_shift"] * self.sample_rate
            else:
                # the input is in seconds, so we calculate a shift in rows
                value = float(value) * self.sample_rate
                correlation_string = ""

            if value > self.ctd_data.get_data_length():
                warnings.warn(
                    f"Data size of {self.ctd_data.get_data_length()} too small for shift of {value}. Skipping AlignCTD.",
                    category=RuntimeWarning,
                )
                return False

            # apply shift for all columns of the given parameter
            for parameter in target_parameters:
                # get the number of decimals to format the output in the same
                # way
                number_of_decimals = len(str(parameter.data[0]).split(".")[1])
                # do the shifting/alignment
                parameter.data = np.append(
                    parameter.data[int(value) :,].round(
                        decimals=number_of_decimals
                    ),
                    np.full((int(value),), self.bad_flag),
                )
                # format the output back to seconds
                new_parameter_metadata[parameter.name] = (
                    str(float("{:.2f}".format(value / self.sample_rate)))
                    + "s"
                    + correlation_string
                )
                try:
                    self.array = self.ctd_data.get_full_data_array()
                except IndexError as error:
                    logger.error(
                        f"AlignCTD failed for {self.ctd_data.path_to_file} while aligning {parameter}: {error}"
                    )
                    return_value = False
                    break
                # at least one column has been altered so we can give positive
                # feedback
                return_value = True
        self.arguments = new_parameter_metadata
        return return_value

    def estimate_sensor_delay(
        self,
        delayed_parameter: Parameter,
        margin: int = 240,
        shift_seconds: int = 10,
    ) -> Tuple[float, float]:
        """
        Estimate delay between a delayed parameter and temperature signals via
        cross-correlation of high-frequency components.

        Parameters
        ----------
        delayed_parameter : Parameter :
            The parameter whose delay shall be computed.
        margin : int
            A number of data points that are cutoff from both ends.
            (Default value = 240)
        shift_seconds : int
            Maximum time window to search for lag (Default value = 10 seconds).
        """
        temperature = self.find_corresponding_temperature(
            delayed_parameter
        ).data
        delayed_values = delayed_parameter.data
        assert len(temperature) == len(delayed_values)
        # remove edge effects (copying Gerds MATLAB software)
        while len(temperature) <= 2 * margin:
            margin = margin // 2

        t_shortened = np.array(temperature[margin:-margin])
        v_shortened = np.array(delayed_values[margin:-margin])

        if np.all(np.isnan(v_shortened)):
            return np.nan, np.nan

        # design Butterworth filter
        b, a = butter(3, 0.005)

        # smooth signals
        t_smoothed = filtfilt(b, a, t_shortened)
        v_smoothed = filtfilt(b, a, v_shortened)

        # high-frequency components
        t_high_freq = t_shortened - t_smoothed
        v_high_freq = v_shortened - v_smoothed

        # cross-correlation
        max_lag = int(shift_seconds * self.sample_rate)
        sign = self.get_correlation(delayed_parameter)
        corr = correlate(v_high_freq, t_high_freq * sign, mode="full")
        lags = np.arange(-len(t_high_freq) + 1, len(t_high_freq))
        lag_indices = np.where(np.abs(lags) <= max_lag)[0]

        # normalize correlation values
        norm_factor = np.sqrt(np.sum(v_high_freq**2) * np.sum(t_high_freq**2))
        corr_normalized = corr / norm_factor

        corr_segment = corr_normalized[lag_indices]
        lags_segment = lags[lag_indices]

        # restrict to only positive delays
        positive_indices = np.where(lags_segment > 0)[0]
        corr_segment_positive = corr_segment[positive_indices]

        peaks, props = find_peaks(
            corr_segment_positive, height=0.01, distance=5
        )

        # handle case, when no correlation can be found
        if len(peaks) == 0:
            return np.nan, np.nan

        # find lag with highest correlation
        best_index = int(np.argmax(props["peak_heights"]))

        return float(peaks[best_index]), float(
            "{:.2f}".format(props["peak_heights"][best_index])
        )

    def check_correlation_result(
        self,
        value: float,
        correlation_value: float,
        minimum_correlation: float = 0.1,
    ) -> bool:
        """
        Performs several checks on the delay outputed by
        estimate_sensor_delay and returns True, if the result is
        considered feasible.

        Parameters
        ----------
        value: float
            The value to check
        correlation_value: float
            The correlation value
        minimum_correlation: float
            The correlation to consider good (Default value = 0.1)

        Returns
        -------
        Whether the correlation is feasible or not.
        """
        if (value is np.nan) or (correlation_value is np.nan):
            return False
        value = value / self.sample_rate
        if correlation_value < minimum_correlation:
            return False
        if value < 1 or value > 6:
            return False
        return True

    def find_corresponding_temperature(
        self, parameter: Parameter
    ) -> Parameter:
        """
        Find the temperature values of the sensor that shared the same water
        mass as the input parameter.

        Parameters
        ----------
        parameter : Parameter :
            The parameter of interest.

        Returns
        -------
        Parameter instance of a temperature.
        """
        if "0" in parameter.name:
            return self.ctd_data["t090C"]
        elif "1" in parameter.name:
            return self.ctd_data["t190C"]
        else:
            raise MissingParameterError("AlignCTD", "Temperature")

    def get_correlation(self, parameter: Parameter) -> float:
        """
        Gives a number indicating the cross correlation type regarding the
        input parameter and the temperature.

        Basically distinguishes between positive correlation, 1, and anti-
        correlation, -1. This value is then used to alter the temperature
        values accordingly.

        Parameters
        ----------
        parameter : Parameter :
            The parameter to cross correlate with temperature.

        Returns
        -------
        A number indicating positive or negative correlation.
        """
        if parameter.metadata["name"].lower().startswith("oxygen"):
            return -1
        else:
            return 1

    def handle_parameter_input(self, input_dict: dict) -> dict:
        """
        Parse parameter input.

        Parameters
        ----------
        input_dict: dict
            The input arguments

        Returns
        -------
        The parsed arguments.
        """
        new_dict = {}
        all_parameter_names = [
            value["name"].lower()
            for value in self.ctd_data.get_metadata().values()
        ]
        for parameter_input, value in input_dict.items():
            # remove all non-alphanumeric characters
            parameter = (
                "".join(filter(str.isalnum, parameter_input)).lower().strip()
            )
            if parameter_input[-1] in ["1", "2"]:
                parameter = parameter[:-1]
                number = parameter_input[-1]
            else:
                number = None
            parameter_names = [
                name
                for name in all_parameter_names
                if name.startswith(parameter)
            ]
            # check, whether we are working with multiple sensors
            if "2" in [name[-1] for name in parameter_names]:
                # differentiate the different cases for 2 sensors
                # only parameter without sensor number information given
                if parameter.lower() in parameter_names and not number:
                    new_dict[f"{parameter}1"] = value
                    new_dict[f"{parameter}2"] = value
                # explicitly given sensor 1
                if parameter.lower() in parameter_names and number == "1":
                    new_dict[f"{parameter}1"] = value
                # explicitly given sensor 2
                if parameter.lower() in parameter_names and number == "2":
                    new_dict[f"{parameter}2"] = value
            else:
                # single sensor is easy, just use the value for sensor 1
                if not parameter[-1] == "2":
                    new_dict[f"{parameter}1"] = value
        return new_dict


class WFilter(ArrayModule):
    """Apply a signal processing filter to certain data columns."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_values: dict = {
            "Pressure": {
                "window_type": "gaussian",
                "window_width": 20,
                "half_width": 0.415,
                "offset": 0,
            },
            "Temperature": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "Conductivity": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "Salinity": {
                "window_type": "gaussian",
                "window_width": 24,
                "half_width": 0.5,
                "offset": 0,
            },
            "Oxygen": {
                "window_type": "gaussian",
                "window_width": 48,
                "half_width": 1,
                "offset": 0,
            },
            "Fluorescence": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "Turbidity": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "PAR": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "SPAR": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
            "FlowMeter": {
                "window_type": "median",
                "window_width": 5,
                "half_width": 1,
                "offset": 0,
            },
        },
        **kwargs,
    ) -> None | CnvFile | CTDData:
        self.default_values = default_values
        return super().__call__(input, arguments, output, output_name)

    def transformation(self) -> bool:
        """
        Calls window_filter method and handles argument display.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        general_kwargs = {
            "flags": self.flags,
            "sample_interval": 1 / self.sample_rate,
            "exclude_flags": False,
            "flag_value": self.bad_flag,
        }
        # sanitize user input
        iter_arguments = copy(self.arguments)
        for key, value in iter_arguments.items():
            self.arguments[key.replace(" ", "").lower()] = value
            self.arguments.pop(key)
        new_arguments = {}
        for param in self.ctd_data.parameters.get_parameter_list():
            try:
                specific_kwargs = self.default_values[param.param]
            except KeyError:
                specific_kwargs = {}
            if param.param.lower() in self.arguments:
                # use default values of SPAR, to allow the user to not set all
                # 4 values that are necessary to run a wfilter
                specific_kwargs = self.default_values["SPAR"]
                for key, value in self.arguments[param.param.lower()].items():
                    if key == "window_type":
                        value = value.lower()
                    specific_kwargs[key] = value
            if specific_kwargs:
                with warnings.catch_warnings(action="ignore"):
                    param.data = self.window_filter(
                        data_in=param.data,
                        **general_kwargs,
                        **specific_kwargs,
                    )
                new_arguments[param.param] = ", ".join(
                    [str(value) for value in specific_kwargs.values()]
                )

        self.arguments = new_arguments

        return True

    def window_filter(
        self,
        data_in: np.ndarray,
        flags: np.ndarray,
        window_type: str,
        window_width: int,
        sample_interval: float,
        half_width: float = 1.0,
        offset: float = 0.0,
        exclude_flags: bool = False,
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
        if exclude_flags:
            data = np.where(flags == flag_value, np.nan, data)

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


class CellTM(ArrayModule):
    """Fix cell thermal mass errors of the conductivity sensors."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_mapping: dict = {
            "sbe9": (0.03, 7.0),
            "sbe19": (0.04, 8.0),
        },
        **kwargs,
    ) -> None | CnvFile | CTDData:
        self.cell_tm_param_mapping = default_mapping
        return super().__call__(input, arguments, output, output_name)

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
                    if key in self.ctd_data.header[0].lower().replace(" ", ""):
                        self.alpha, self.beta = self.cell_tm_param_mapping[key]

            except KeyError:
                logger.error(
                    f"No cell_tm parameters for instrument {self.ctd_data.header[0][:-10]}. No cell thermal mass correction applied."
                )
            else:
                self.arguments["alpha"] = self.alpha
                self.arguments["beta"] = self.beta
        for param in [p for p in self.ctd_data if p.param == "Conductivity"]:
            # check availability of temperature in this sensor strand
            if param.sensor_number == 1:
                temperature_name = "t090C"
            else:
                temperature_name = "t190C"
            temperature = self.ctd_data[temperature_name].data
            if not self._check_parameter_existence(temperature_name):
                logger.error(
                    f"Missing temperature for sensor strand {param.sensor_number}"
                )
                return False

            # enforce correct conductivity unit
            if param.unit == "mS/cm":
                conductivity = param.data / 10.0
            elif param.unit == "S/m":
                conductivity = param.data
            else:
                logger.error(
                    f"Unknown conductivity unit {param.unit}. Aborting."
                )
                return False
            # seabirds celltm cannot handle nans, setting so bad flag value
            temperature = np.nan_to_num(temperature, nan=self.bad_flag)
            param.data[param.data == self.bad_flag] = np.nan
            corrected_conductivity = sbs_proc.cell_thermal_mass(
                temperature_C=temperature,
                conductivity_Sm=conductivity,
                amplitude=self.alpha,
                time_constant=1 / self.beta,
                sample_interval=1 / self.sample_rate,
            )

            if param.unit == "mS/cm":
                param.data = corrected_conductivity * 10
            elif param.unit == "S/m":
                param.data = corrected_conductivity

        return True


class BinAvg(ArrayModule):
    """Bin data points in pressure or time bins."""

    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self,
        input: Path | str | CnvFile | CTDData,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        default_values: dict = {
            "bin_variable": "prDM",
            "bin_size": 1,
            "cast_type": "down",
        },
        **kwargs,
    ) -> None | CnvFile | CTDData:
        self.name = "binning"
        return super().__call__(
            input, arguments, output, output_name, default_values
        )

    def transformation(self) -> bool:
        """
        Calls own_bin_average and reset sample rate.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        self.check_whether_working_on_binned_data()
        self.ctd_data.drop_flagged_rows()
        for param in self.ctd_data:
            param.data = np.nan_to_num(param.data, nan=self.bad_flag)

        dataset = {param.name: param.data for param in self.ctd_data}
        try:
            array_data = self.own_bin_average(
                data=dataset,
                flag_value=self.bad_flag,
                **self.arguments,
            )
        except Exception as error:
            logger.error(
                f"Could not bin {self.ctd_data.path_to_file}: {error}"
            )
            return False
        for name, data in array_data.items():
            for param in self.ctd_data:
                if param.name == name:
                    param.data = data
        if float(self.arguments["bin_size"]) >= 1:
            number_of_decimals = 0
        else:
            number_of_decimals = len(
                str(float(self.arguments["bin_size"])).split(".")[1]
            )
        if self.arguments["bin_variable"] == "prDM":
            self.ctd_data.calculate_depth(decimals=number_of_decimals)

        # set new sample rate
        self.ctd_data.set_sample_rate(
            float(self.arguments["bin_size"]),
            self.ctd_data[self.arguments["bin_variable"]].metadata["unit"],
        )

        return True

    def own_bin_average(
        self,
        data: Dict[str, np.ndarray],
        bin_variable: str,
        bin_size: float,
        min_scans: int = 0,
        max_scans: int = 999999,
        cast_type: str = "down",
        flag_value: float = -9.99e-29,
        include_scan_count: bool = True,
        linear_interpolation: bool = False,
    ) -> Dict[str, np.ndarray]:
        """
        Optimized bin average using a vectorized approach on numpy arrays.

        Refactored with claude.

        Parameters
        ----------
        data: Dict[str, np.ndarray] :
            The input data
        bin_variable: str
            The parameter to bin
        bin_size: float
            The size of the individual bins
        min_scans: int
            The minimum number of scans per bin (Default value = 1)
        max_scans: int
            The maximum number of scans per bin (Default value = 999999)
        cast_type: str
            Downcast, upcast or both (Default value = "down")
        flag_value: float
            The value to use as bad flag (Default value = -9.99e-29)
        include_scan_count: bool
            Whether to create column that holds scan count of each bin (Default value = True)
        linear_interpolation: bool
            If True, fills in missing bins by linearl interpolation

        Returns
        -------
        A dictionary of column names and binned data.
        """
        n_rows = len(data[bin_variable])

        # --- 1. Remove flagged rows ---
        valid_mask = np.ones(n_rows, dtype=bool)
        for arr in data.values():
            valid_mask &= arr != flag_value
        filtered_data = {col: arr[valid_mask] for col, arr in data.items()}
        control = filtered_data[bin_variable]
        n_valid = len(control)
        if n_valid == 0:
            return {col: np.array([]) for col in data.keys()}

        # --- 2. Find the peak (max of bin variable) ---
        peak_idx = int(np.nanargmax(control))

        # --- 3. Build a fixed grid from 0 to max, stepping by bin_size ---
        #    Each bin centre sits at: 0, bin_size, 2*bin_size, ...
        #    A point belongs to whichever centre it is closest to.
        # Assign each point to its nearest bin centre (integer index into bin_centers)
        bin_labels = np.round(control / bin_size).astype(
            int
        )  # == argmin of |control - bin_centers|

        # --- 4. Split into downcast / upcast with non-colliding labels ---
        down_labels = bin_labels[:peak_idx]  # exclude peak
        up_labels = bin_labels[peak_idx:]  # peak belongs to upcast only

        # Offset upcast labels so they never collide with downcast labels
        offset = int(bin_labels.max()) + 1
        up_labels_offset = offset + (int(bin_labels[peak_idx]) - up_labels)

        all_labels = np.concatenate(
            [down_labels, up_labels_offset]
        )  # peak counted once via upcast

        # --- 5. Apply cast-type filter ---
        indices = np.arange(n_valid)
        if cast_type == "down":
            keep = indices <= peak_idx
        elif cast_type == "up":
            keep = indices >= peak_idx
        else:  # "both" or anything else
            keep = np.ones(n_valid, dtype=bool)

        all_labels = all_labels[keep]
        filtered_data = {col: arr[keep] for col, arr in filtered_data.items()}

        if len(all_labels) == 0:
            return {col: np.array([]) for col in data.keys()}

        # --- 6. Map arbitrary label integers → compact 0-based indices ---
        _, inverse = np.unique(all_labels, return_inverse=True)

        bin_counts = np.bincount(inverse)
        valid_bin_mask = (bin_counts >= min_scans) & (bin_counts <= max_scans)
        if not valid_bin_mask.any():
            return {col: np.array([]) for col in data.keys()}

        point_valid = valid_bin_mask[inverse]
        inverse_filt = inverse[point_valid]
        filtered_data = {
            col: arr[point_valid] for col, arr in filtered_data.items()
        }
        bin_counts_filt = bin_counts[valid_bin_mask]

        _, inverse_filt = np.unique(inverse_filt, return_inverse=True)
        n_bins = len(bin_counts_filt)

        # --- 7. Compute per-bin averages ---
        results = {}
        for col_name, arr in filtered_data.items():
            if col_name == "flag":
                flag_sums = np.bincount(
                    inverse_filt,
                    weights=(arr == flag_value).astype(float),
                    minlength=n_bins,
                )
                results[col_name] = np.where(
                    flag_sums == bin_counts_filt, flag_value, 0.0
                )
            else:
                bin_sums = np.bincount(
                    inverse_filt, weights=arr, minlength=n_bins
                )
                results[col_name] = bin_sums / bin_counts_filt

        # --- 8. Overwrite bin_variable with fixed grid centres ---
        # Recover the unique label per bin (first occurrence is fine since all
        # points in a bin share the same label after re-compaction)
        unique_labels = np.unique(
            all_labels[point_valid]
        )  # one label per bin, sorted
        if cast_type in ("down", "both"):
            # downcast labels are just bin_labels directly → centre = label * bin_size
            bin_centres = unique_labels * bin_size
        else:
            # upcast labels were offset: label = offset + (peak_label - original_label)
            # → original_label = offset + peak_label - label → centre = original_label * bin_size
            peak_label = int(np.round(control[peak_idx] / bin_size))
            bin_centres = (offset + peak_label - unique_labels) * bin_size
        results[bin_variable] = bin_centres.astype(float)
        if include_scan_count:
            results["nbin"] = bin_counts_filt

        # --- 9. (Optional) linearly interpolate between bins with a gap ---
        if linear_interpolation:
            dense_grid = np.arange(
                bin_centres[0], bin_centres[-1] + bin_size, bin_size
            )
            for col in list(results):
                results[col] = np.interp(dense_grid, bin_centres, results[col])
            results[bin_variable] = dense_grid

        return results
