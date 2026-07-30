import logging
import warnings
from typing import Tuple

import numpy as np
from scipy.signal import find_peaks, find_peaks_cwt, savgol_filter

logger = logging.getLogger(__name__)


def smoothing(x: np.ndarray) -> np.ndarray:
    """
    Basic filtering function for pressure values.

    Parameters
    ----------
    x: np.ndarray
        The pressure array

    Returns
    -------
    A smoothed pressure array.
    """
    size = x.shape[0]
    window_length = size // 40
    if window_length < 500:
        window_length = 500
    elif window_length > 2000:
        window_length = 2000
    for window in [
        window_length,
        window_length // 2,
        window_length // 10,
        size // 40,
        size // 100,
        25,
    ]:
        try:
            return savgol_filter(x, window_length=window, polyorder=3)
        except ValueError:
            continue
    return x


def get_cast_borders(
    pressure: np.ndarray,
    downcast_only: bool = True,
    min_size_factor: float = 0.01,
    min_soak_window: int = 100,
    max_fd_quotient: int = 6,
    prominence_divisor: int = 7,
    win_size_divisor: int = 500,
    min_velocity_quotient: int = 15,
    min_velocity: float = 0.045,
) -> dict:
    """
    Calculates start and end points of one CTD cast.

    Uses first (fd) and second derivatives (sd) for that.
    Relies on carefully fine-tuned parameters that are set as
    default values. These can be fit to any kind of CTD data.

    Parameters
    ----------
    pressure: np.ndarray
        Pressure array
    downcast_only: bool
        Whether to only work with downcast data (Default value = True)
    min_size_factor: float
        Factor to check final dataset size against (Default value = 0.01)
    min_soak_window: int
        Downcast_start: minimum size of soaking window (Default value = 100)
    max_fd_quotient: int
        Downcast_start: Cut-off of fd height (Default value = 6)
    prominence_divisor: int
        Downcast_start: Minimum size of sd peak prominence (Default value = 7)
    win_size_divisor: int
        Downcast_start: Search window size to check fd means (Default value = 500)
    min_velocity_quotient: int
        Downcast_start: Minimum velocity cut-off (Default value = 15)
    min_velocity: float
        Downcast_start: Minimum velocity cut-off (Default value = 0.045)

    Returns
    -------
    A dictionary holding the cast borders and fd and sd values for debugging.
    """

    out_dict = {}

    # calculate first and second derivative
    smoothed_pressure = smoothing(pressure)
    maximum_pressure_index = np.nanargmax(smoothed_pressure)
    pressure_to_max = smoothed_pressure[:maximum_pressure_index]

    try:
        first_derivative = smoothing(np.gradient(pressure_to_max) * 24)
    except ValueError:
        out_dict["down_start"] = 0
        out_dict["down_end"] = maximum_pressure_index
        return out_dict

    second_derivative = smoothing(np.gradient(first_derivative))

    down_start, out_dict["fd_minima"], out_dict["sd_maxima"] = (
        get_downcast_start(
            first_derivative,
            second_derivative,
            base_data_size=pressure.shape[0],
            min_soak_window=min_soak_window,
            max_fd_quotient=max_fd_quotient,
            prominence_divisor=prominence_divisor,
            win_size_divisor=win_size_divisor,
            min_velocity_quotient=min_velocity_quotient,
            min_velocity=min_velocity,
        )
    )
    down_end = get_downcast_end(
        smoothed_pressure, first_derivative, second_derivative
    )

    soak_start, soak_end = soaking_detection(pressure)

    final_down_start = combine_downcast_start(
        pressure=pressure,
        down_start=down_start,
        soak_end=soak_end,
        min_speed=min_velocity,
    )

    # last sanity check
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if (
            np.mean(first_derivative[down_start - 480 : down_start])
            > min_velocity * 2
        ):
            down_start = (
                out_dict["sd_maxima"][0]
                if len(out_dict["sd_maxima"]) > 0
                else 0
            )

    if (
        down_end - down_start < pressure.shape[0] * min_size_factor
        or down_end - down_start < 200
    ):
        warnings.warn(
            f"Found cast borders below the minimum cast size threshold of {pressure.shape[0] * min_size_factor}, defaulting to full cast size.",
            RuntimeWarning,
        )
        down_start = 0
        down_end = maximum_pressure_index

    out_dict["down_start"] = final_down_start
    out_dict["down_end"] = down_end

    if not downcast_only:
        out_dict["up_start"] = get_upcast_start(
            out_dict["down_end"], smoothed_pressure
        )
        out_dict["up_end"] = get_upcast_end(
            out_dict["down_end"], smoothed_pressure
        )

    return out_dict


def get_downcast_end(
    smoothed_pressure: np.ndarray,
    first_derivative: np.ndarray,
    second_derivative: np.ndarray,
) -> int:
    """
    Gets the downcast end point of a given cast.

    Either returns the first pressure index, that is 2 dbar below the
    global pressure maximum or the second derivative maximum between the first
    derivative minimum and the end point.

    Parameters
    ----------
    smoothed_pressure: np.ndarray
        Filtered pressure array
    first_derivative: np.ndarray
        All first derivatives of pressure
    second_derivative: np.ndarray
        All second derivatives of pressure
    Returns
    -------
    The index of the end of the downcast.
    """
    maximum_pressure_index = np.nanargmax(smoothed_pressure)
    pressure_border = [
        index
        for index, value in enumerate(smoothed_pressure)
        if value > (smoothed_pressure[maximum_pressure_index] - 2)
    ]

    if pressure_border:
        lower_pressure_border = pressure_border[0]
    else:
        min_fd_index = np.nanargmin(first_derivative)
        max_sd_index = np.nanargmax(second_derivative[min_fd_index:])
        lower_pressure_border = max_sd_index + min_fd_index

    try:
        min_sd_index = np.nanargmin(second_derivative[lower_pressure_border:])
    except Exception:
        return int(maximum_pressure_index)
    return int(min_sd_index + lower_pressure_border)


def get_downcast_start(
    first_derivative: np.ndarray,
    second_derivative: np.ndarray,
    base_data_size: int,
    min_soak_window: int = 100,
    max_fd_quotient: int = 6,
    prominence_divisor: int = 7,
    win_size_divisor: int = 500,
    min_velocity_quotient: int = 15,
    min_velocity: float = 0.045,
) -> Tuple[int, list, list]:
    """
    Gets the downcast start of a given cast, removing soaking/waiting time.

    Returns the index from where the CTD begins to continuously move downward.


    Parameters
    ----------
    first_derivative: np.ndarray
        All first derivatives of pressure
    second_derivative: np.ndarray
        All second derivatives of pressure
    base_data_size: int
        The size of the original pressure array
    min_soak_window: int
        Minimum size of soaking window (Default value = 100)
    max_fd_quotient: int
        Cut-off of fd height (Default value = 6)
    prominence_divisor: int
        Minimum size of sd peak prominence (Default value = 7)
    win_size_divisor: int
        Search window size to check fd means (Default value = 500)
    min_velocity_quotient: int
        Minimum velocity cut-off (Default value = 15)
    min_velocity: float
        Minimum velocity cut-off (Default value = 0.045)

    Returns
    -------
    The index of the start of the downcast.
    """
    max_fd = np.nanmax(first_derivative)

    # detect fluctuations in decent rate
    # if none found, set downcast start point to 0
    prominent_minimum = 0
    all_fd_minima = list(reversed(find_peaks_cwt(-first_derivative, 24)))
    all_maxima = []
    window_half = min_soak_window // 2
    for minimum in all_fd_minima:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if (
                np.mean(
                    first_derivative[
                        minimum - window_half : minimum + window_half
                    ]
                )
                < -max_fd / max_fd_quotient
            ):
                all_maxima.append(minimum)
                prominent_minimum = minimum

    down_start = 0
    all_sd_maxima = []

    if prominent_minimum:
        first_derivative = first_derivative[prominent_minimum:]
        all_sd_maxima = find_peaks(
            second_derivative[prominent_minimum:],
            prominence=np.nanmax(second_derivative[prominent_minimum:])
            / prominence_divisor,
        )[0]

        search_window = base_data_size // win_size_divisor

        for maximum in sorted(all_sd_maxima):
            mean = np.nanmean(
                first_derivative[maximum : maximum + search_window]
            )
            if mean > max_fd / min_velocity_quotient:
                down_start = maximum + prominent_minimum
                break
            for i in range(search_window * 7):
                index = maximum + i
                if index < len(first_derivative):
                    if first_derivative[index] > 0:
                        mean = np.nanmean(
                            first_derivative[index : index + search_window]
                        )
                        if mean > min_velocity:
                            down_start = index + prominent_minimum
                            break
            if down_start:
                break

    return (
        int(down_start),
        all_maxima,
        [maxi + prominent_minimum for maxi in all_sd_maxima],
    )


def get_upcast_start(ind_dc_end: int, smooth_velo: np.ndarray) -> int | None:
    """
    The start point of the upcast.


    Parameters
    ----------
    ind_dc_end: int
        The index of the downcast end point
    smooth_velo: np.ndarray
        The filtered pressure array

    Returns
    -------
    Index of upcast start point.
    """
    upcast_velo_mean = np.mean(smooth_velo[ind_dc_end : len(smooth_velo)])
    for i in range(ind_dc_end, len(smooth_velo)):
        if smooth_velo[i] < upcast_velo_mean * 0.5:
            return i
    logger.warning("Could not find the upcast start.")
    return None


def get_upcast_end(ind_dc_end: int, smooth_velo: np.ndarray) -> int | None:
    """
    The end point of the upcast.


    Parameters
    ----------
    ind_dc_end: int
        The index of the downcast end point
    smooth_velo: np.ndarray
        The filtered pressure array

    Returns
    -------
    Index of upcast end point.
    """
    upcast_velo_mean = np.mean(smooth_velo[ind_dc_end : len(smooth_velo)])
    for i in range(len(smooth_velo) - 1, ind_dc_end, -1):
        if smooth_velo[i] < upcast_velo_mean * 0.5:
            return i
    logger.warning("Could not find the upcast end.")
    return None


def soaking_detection(
    pressure: np.ndarray,
    min_speed: float = 0.04,
    window_size: int = 140,
    negative_speed_threshold: float = -2.5,
    plateau_pressure_delta: float = 1.0,
) -> tuple[int, int]:
    """
    The start and end of the soaking window.


    Parameters
    ----------
    pressure: np.ndarray
        Pressure Array
    min_speed: float
        Minimum speed that the movement of the cast is considered singificant for the detection of the downcast
    window_size: int
        Size of window that needs to be positive (min_speed) for the detection of the downcast
    negative_speed_treshhold: float
        Treshold for when the movement of the cast is considered to be going actively up
    plateau_pressure_delta: float
        Minimum increase in pressure required before the cast is considered to have left the plateau after an upward movement.

    Returns
    -------
    Tuple with start and end point of the soaking.
    """

    smoothed = smoothing(pressure)

    if len(smoothed) < 2:
        return 0, 0

    speed = np.gradient(smoothed) * 24

    max_idx = np.nanargmax(smoothed)
    smoothed = smoothed[:max_idx]
    speed = speed[:max_idx]

    if len(speed) < window_size:
        return 0, 0

    # detecting 'bumps' where ctd gets pulled up before downcast starts
    search_start = 0

    for i in range(0, len(speed) - window_size + 1):
        window = speed[i : i + window_size]

        negative = np.mean(window < negative_speed_threshold)

        if negative >= 0.7:
            search_start = i + window_size

    # skip plateau
    start_search = search_start

    if search_start > 0:
        plateau_level = smoothed[search_start]

        while (
            start_search < len(smoothed)
            and smoothed[start_search] < plateau_level + plateau_pressure_delta
        ):
            start_search += 1

        start_search = max(search_start, start_search - window_size)

    # searching for stable downcast
    stable_start = None

    for i in range(start_search, len(speed) - window_size + 1):
        window = speed[i : i + window_size]

        positives = np.mean(window > min_speed)
        mean_speed = np.nanmean(window)

        if positives >= 0.9 and mean_speed > min_speed:
            stable_start = i
            break

    if stable_start is None:
        return 0, 0

    # specieal case: cast starts directly at 0
    if stable_start <= 5:
        soak_end = 0
    else:
        soak_end = stable_start + window_size

    soak_end = min(soak_end, len(speed) - 1)

    return 0, int(soak_end)


def soaking_removal(
    data,
    pressure: np.ndarray,
    **kwargs,
):
    """
    Removes the soaking phase from any array-like data using pressure and soaking_detection.
    """

    _, soak_end = soaking_detection(pressure, **kwargs)

    return data[soak_end:]


def combine_downcast_start(
    pressure: np.ndarray,
    down_start: int,
    soak_end: int,
    min_speed: float = 0.045,
    window_size: int = 120,
) -> int:
    """
    Combines the results of soaking_detection() and get_downcast_start().

    Parameters
    ----------
    pressure: np.ndarray
        Pressure array.
    down_start: int
        Downcast start index determined by get_downcast_start().
    soak_end: int
        End index of the soaking period determined by soaking_detection().
    min_speed: float
        Minimum speed that the movement of the cast is considered
        significant for the detection of the downcast.
    window_size: int
        Size of the window that must satisfy the minimum speed criterion
        when checking for a stable downcast.

    Returns
    -------
    The final downcast start index.
    """

    smoothed = smoothing(pressure)

    if len(smoothed) < 2:
        return int(soak_end)

    speed = np.gradient(smoothed) * 24
    max_idx = int(np.nanargmax(smoothed))

    down_start = int(down_start)
    soak_end = int(soak_end)

    if down_start <= 0 or down_start >= max_idx:
        return soak_end

    if abs(down_start - soak_end) <= 300:
        return down_start

    total_pressure_gain = smoothed[max_idx] - smoothed[0]

    if total_pressure_gain <= 0:
        return soak_end

    depth_fraction = (smoothed[down_start] - smoothed[0]) / total_pressure_gain

    if depth_fraction > 0.50:
        return soak_end

    if down_start > soak_end:
        pressure_gain_before_down_start = (
            smoothed[down_start] - smoothed[soak_end]
        )

        if pressure_gain_before_down_start > 10.0:
            return soak_end

        pressure_gain_fraction = (
            pressure_gain_before_down_start / total_pressure_gain
        )

        if pressure_gain_fraction > 0.10:
            return soak_end

    end = min(down_start + window_size, len(speed))
    speed_window = speed[down_start:end]

    if len(speed_window) < 2:
        return soak_end

    positive_fraction = np.mean(speed_window > min_speed)
    mean_speed = np.nanmean(speed_window)

    if positive_fraction < 0.6 or mean_speed < min_speed:
        return soak_end

    return down_start
