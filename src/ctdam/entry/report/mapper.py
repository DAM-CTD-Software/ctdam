import json
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd
import xarray as xr

from ctdam.utils import read_event_name

logger = logging.getLogger(__name__)


def dship_event_mapper(
    casts: List[xr.Dataset],
    path_to_action_log: Path | str,
    tolerance: int = 300,
    action_log_start_time_name: str = "Device Operation Start",
    action_log_event_name: str = "Device Operation",
    manual_action_log_tuple: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]] | None:
    # load the action_log
    if manual_action_log_tuple:
        action_log_start_times = manual_action_log_tuple
    elif Path(path_to_action_log).suffix == ".json":
        with open(path_to_action_log) as file:
            action_log = json.load(file)
        # find the start points of the action_log entries
        action_log_casts = [
            action
            for action in action_log
            if action["Action"] == "in the water"
        ]
        # create tuples of start time and Event label for matching
        action_log_start_times = [
            (
                action[action_log_start_time_name],
                action[action_log_event_name],
            )
            for action in action_log_casts
        ]
    else:
        try:
            action_log = pd.read_csv(
                path_to_action_log, delimiter="\t", encoding="latin-1"
            )
        except Exception:
            logger.error(
                f"Could not open action log file: {path_to_action_log}"
            )
            return
        action_log = action_log[action_log["Abbreviation"] == "CTD-RO"]
        action_log = action_log[["Date/Time", "Event label"]]
        action_log_start_times = list(
            action_log.itertuples(index=False, name=None)
        )

    for cast in casts:
        if cast.attrs["station"]:
            event_names = [
                read_event_name(event)[1]
                for _, event in action_log_start_times
            ]
            if cast.attrs["station"] in event_names:
                event_index = event_names.index(cast.station)
                del action_log_start_times[event_index]
            continue
        # create the mapping using an inner join
        matched_times = inner_join_times(
            dship_times=action_log_start_times,
            start_time=cast.attrs["start_time"],
            tolerance=tolerance,
        )
        matched_events = [event for _, event in matched_times]
        if len(matched_events) > 1:
            warnings.warn(
                f"Found more than one matching dship time for {cast.file_name}"
            )
            break
        elif len(matched_events) == 1:
            cast.attrs["station"] = matched_events[0]
            action_log_start_times.remove(matched_times[0])

    return action_log_start_times


def _parse_time(time_str: datetime | str) -> datetime:
    """Parse a time string into a datetime object."""
    if isinstance(time_str, datetime):
        return time_str
    try:
        return datetime.strptime(time_str, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                logger.error(f"Could not parse time string: {time_str}")
                return datetime.now()


def _find_best_match(
    dship_time: datetime,
    start_time: datetime,
    tolerance: int = 120,
) -> datetime | None:
    """Find the closest time match within a given tolerance in seconds."""
    start_time = _parse_time(start_time)
    try:
        diff = abs((dship_time - start_time).total_seconds())
    except TypeError:
        logger.error(f"Not the correct time format: {start_time}")
        return None
    if diff <= tolerance:
        best_match = start_time
    else:
        best_match = None
    return best_match


def inner_join_times(
    dship_times: list[tuple[str, str]],
    start_time: datetime,
    tolerance: int = 120,
):
    """Performs an inner join on the two time tuples to generate a mapping
    of Event code to cast number. With that mapping, the pandas DataFrame
    can be extended with an Event column. The difficulty of this task
    arises from the missing pm or am information in the DSHIP data dump.
    That makes it necessary to perform the match twice, ones with the
    original times and ones with the 12h-shifted times."""
    matched_pairs = []
    for time_str, event_str in dship_times:
        original_time = _parse_time(time_str)
        if original_time.hour == 12:
            adjusted_time = original_time - timedelta(hours=12)
        else:
            adjusted_time = original_time + timedelta(hours=12)

        # Try to match with the original time
        best_match = _find_best_match(original_time, start_time, tolerance)

        # If no match found, try with the adjusted time
        if not best_match:
            best_match = _find_best_match(adjusted_time, start_time, tolerance)

        if best_match:
            matched_pairs.append((time_str, event_str))
    return matched_pairs
