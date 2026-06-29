import logging
import re
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np

from ctdam.parser.ctddata import CTDData
from ctdam.parser.ctdmetadata import CTDMetadata
from ctdam.parser.parameter import Parameters

logger = logging.getLogger(__name__)

mapping = {
    "press": "Pressure",
    "temp": "Temperature",
    "cond": "Conductivity",
    "do_ml": "Oxygen",
    "salin": "Salinity",
    "intd": "timeU",
    "long": "longitude",
    "lat": "latitude",
}


def sst2ctddata(input_path: Path | str, delimiter: str = " ") -> CTDData:
    """
    Read CTD data from an SST .TOB data file and create a CTDData instance.

    Based on a MATLAB script written by Johanna Grote and Jens Faber.

    Parameters
    ----------
    input_path: Path | str
        The path to the .TOB file

    delimiter: str
        The data file delimiter

    Returns
    -------
    A CTDData object that holds the CTD data from the .TOB file
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
        elif "N" in cell:
            try:
                lat = float(cell.replace("N", ""))
                output_data[:, ind] = np.full(nr_dl, lat)
            except ValueError:
                pass
        elif "E" in cell:
            try:
                lon = float(cell.replace("E", ""))
                output_data[:, ind] = np.full(nr_dl, lon)
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

    # Create the Parameters instance for CTDData
    output_data = np.array(output_data).T

    parameters = Parameters([], [], True)

    for array, sst_name in zip(output_data, sst_ids):
        try:
            parameter_name = mapping[sst_name.lower()]
            parameters.create_parameter(
                data=array,
                name=parameter_name,
            )
        except Exception:
            logger.debug(f"{sst_name} had no succesfull mapping.")

    # basic data initialisation
    parameters.sample_rate = parameters.get_sample_rate()
    parameters.create_parameter(
        data=np.zeros(parameters.get_data_length()), name="flag"
    )
    parameters.calculate_depth()

    return CTDData(
        parameters=parameters,
        metadata_source=CTDMetadata(
            metadata_source=input_path,
        ),
    )
