import logging
import re
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr

from ctdam.utils import coordinates_to_float

logger = logging.getLogger(__name__)

mapping = {
    "press": "pressure",
    "temp": "temperature",
    "cond": "conductivity",
    "do_ml": "oxygen",
    "salin": "salinity",
    "intd": "timeU",
    "long": "longitude",
    "lat": "latitude",
}


def sst2xarray(input_path: Path | str, delimiter: str = " ") -> xr.Dataset:
    """
    Read CTD data from an SST .TOB data file and create an Xarray Dataset.

    Parses SST .TOB files directly into a common Xarray structure with:
    - "scan" dimension for each measurement row
    - Data variables incl. metadata
    - Provenance and common metadata tracking

    Based on a MATLAB script written by Johanna Grote and Jens Faber.

    Parameters
    ----------
    input_path : Path | str
        The path to the .TOB file
    delimiter : str, optional
        The data file delimiter (default: " ")

    Returns
    -------
    xr.Dataset
        An Xarray Dataset containing the CTD data with dimensions, coordinates,
        data variables, and provenance metadata.
    """

    nr_hl = 0  # total header lines
    nr_simi = 0  # semicolon-only line counter
    nr_dl = 0  # number of data lines
    sst_ids = []

    with Path(input_path).open("r", encoding="latin-1") as fileID:
        while nr_simi < 4:
            rline = fileID.readline()
            if not rline:
                break
            rline = rline.rstrip("\n").rstrip("\r")

            if rline and rline[0] == ";":
                nr_simi += 1

            if "Lines :" in rline:
                colon_pos = rline.index(":")
                nr_dl = int(float(rline[colon_pos + 1 :].strip()))

            elif nr_simi == 2:
                parts = rline.split(delimiter)
                sst_ids = [p for p in parts if p not in (";", " ", "", "\t")]
                output_data = np.full((nr_dl, len(sst_ids)), np.nan)

            nr_hl += 1

        # Read raw data (after header)
        fileID.seek(0)
        for _ in range(nr_hl):
            fileID.readline()

        raw_rows = []
        for line in fileID:
            line = line.rstrip("\n").rstrip("\r")
            tokens = [t for t in line.split(delimiter) if t != ""]
            if tokens:
                raw_rows.append(tokens)

    # Build raw_data as list-of-lists indexed [row][col]
    # Pad / trim rows to n_vars
    raw_data = []
    for row in raw_rows:
        if len(row) >= len(sst_ids):
            raw_data.append(row[: len(sst_ids)])

    n_vars = len(sst_ids)

    # Detect date / time columns and fill data array
    time_ind = None
    date_ind = None
    date_format = None

    last_row = raw_data[-1] if raw_data else [""] * n_vars

    for ind in range(n_vars):
        cell = last_row[ind] if ind < len(last_row) else ""

        if re.search(r"\d{2}:\d{2}:\d{2}", cell):
            time_ind = ind
        elif re.search(r"\d{2}/\d{2}/\d{4}", cell):
            date_ind = ind
            date_format = "Typ_1"
        elif re.search(r"\d{2}\.\d{2}\.\d{4}", cell):
            date_ind = ind
            date_format = "Typ_2"
        elif re.search(r"\d{2}-\d{2}-\d{4}", cell):
            date_ind = ind
            date_format = "Typ_3"
        elif re.search(r"\d{4}-\d{2}-\d{2}", cell):
            date_ind = ind
            date_format = "Typ_4"
        elif cell[-1] in ("N", "S", "E", "W"):
            try:
                output_data[:, ind] = np.full(
                    nr_dl, coordinates_to_float(cell)
                )
            except ValueError:
                pass

        else:
            col_vals = []
            for row in raw_data:
                try:
                    col_vals.append(
                        float(row[ind]) if ind < len(row) else np.nan
                    )
                except (ValueError, IndexError):
                    col_vals.append(np.nan)
            output_data[: len(col_vals), ind] = col_vals

    # Combine date + time into a unix timestamp
    fmt_map = {
        "Typ_1": ("%d/%m/%Y", "%H:%M:%S"),
        "Typ_2": ("%d.%m.%Y", "%H:%M:%S"),
        "Typ_3": ("%d-%m-%Y", "%H:%M:%S"),
        "Typ_4": ("%Y-%m-%d", "%H:%M:%S"),
    }

    if date_ind is not None:
        dates = [
            row[date_ind] if date_ind < len(row) else "00/00/0000"
            for row in raw_data
        ]
    else:
        dates = ["00/00/0000"] * nr_dl
        warnings.warn("No date in exported data, times will be corrupt")

    if time_ind is not None:
        date_fmt, time_fmt = fmt_map[date_format]
        combined_fmt = date_fmt + time_fmt

        serial_times = []
        for i, row in enumerate(raw_data):
            date_str = dates[i]
            time_str = row[time_ind] if time_ind < len(row) else "00:00:00"
            try:
                dt = datetime.strptime(date_str + time_str, combined_fmt)
                serial_times.append(dt.timestamp())
            except ValueError:
                serial_times.append(np.nan)

        output_data[: len(serial_times), time_ind] = serial_times
    else:
        warnings.warn("No time given in data set")

    # Drop the separate date column (its info is merged into the time column)
    if date_ind is not None and time_ind is not None:
        output_data = np.delete(output_data, date_ind, axis=1)
        del sst_ids[date_ind]

    output_data = np.array(output_data).T
    data_vars = {}

    scan_index = np.arange(len(output_data[0]))

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={
            "scan": scan_index,
        },
    )

    _add_parameters(output_data, sst_ids, mapping, ds, logger)
    _add_metadata(ds, input_path, date_format)
    return ds


def _add_parameters(output_data, sst_ids, mapping, ds, logger):
    """Add parameters, coordinates, and position attributes to dataset."""
    position = [None, None]

    for array, sst_name in zip(output_data, sst_ids):
        try:
            parameter_name = mapping[sst_name.lower()]

            # Add parameter (skip latitude/longitude)
            if parameter_name not in ("latitude", "longitude"):
                ds.add.parameter(parameter_name, array)

            # Handle time coordinate
            if parameter_name == "timeU":
                ds.coords["time"] = array
                ds.attrs["start_time"] = array[0]

            # Extract position
            if parameter_name == "latitude":
                position[0] = float(array[0])
            elif parameter_name == "longitude":
                position[1] = float(array[0])

        except KeyError:
            logger.debug(f"{sst_name} had no successful mapping.")

    ds.attrs["position"] = tuple(position)
    ds.add.parameter("flag", np.zeros(len(output_data[0])))


def _add_metadata(ds, input_path, date_format):
    """Add metadata to dataset."""
    ds.attrs["provenance_metadata"] = ""

    ds.add.processing_metadata(
        module="sst_parser",
        key="source_file",
        value=str(input_path),
    )

    if date_format is not None:
        ds.add.processing_metadata(
            module="sst_parser",
            key="date_format_detected",
            value=date_format,
        )

    # Initialize mostly empty metadata fields
    metadata_fields = {
        "cruise": "",
        "station": "",
        "path_to_source_file": str(input_path),
        "sample_rate": "",
        "instrument_metadata": "",
        "custom_metadata": "",
        "sensor_metadata": "",
    }

    for key, value in metadata_fields.items():
        ds.attrs[key] = value
