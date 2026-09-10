import re
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def _parse_sbe19(path_to_file: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path_to_file, sep="\t")

    pattern = re.compile(
        r"(-?\d+(?:\.\d+)?),\s*"
        r"(-?\d+(?:\.\d+)?),\s*"
        r"(-?\d+(?:\.\d+)?),\s*"
        r"(-?\d+(?:\.\d+)?)"
    )

    rows = []
    cast_id = -1

    for timestamp, raw_line in zip(df["timestamp"], df["raw_line"]):
        raw_line = str(raw_line)

        if "startnow" in raw_line.lower():
            cast_id += 1
            continue

        match = pattern.search(raw_line)

        if match is None or cast_id < 0:
            continue

        rows.append(
            (
                pd.Timestamp(timestamp),
                cast_id,
                *[float(value) for value in match.groups()],
            )
        )

    return pd.DataFrame(
        rows,
        columns=[
            "time",
            "cast_id",
            "temperature",
            "conductivity",
            "pressure",
            "voltage0",
        ],
    )


def read_sbe19(path_to_file: Path | str) -> xr.Dataset:
    path_to_file = Path(path_to_file)
    data = _parse_sbe19(path_to_file)
    time = (
        data["time"]
        .to_numpy(dtype="datetime64[ns]")
        .astype("int64")
        / 1e9
    )

    ds = xr.Dataset(
        coords={
            "scan": (
                "scan",
                np.arange(len(data)),
            ),
            "time": (
                "scan",
                time,
                {
                    "units": "seconds since 1970-01-01 00:00:00",
                    "calendar": "standard",
                    "standard_name": "time",
                },
            ),
        },
        attrs={
            "start_time": str(data["time"].iloc[0]),
            "position": "",
            "cruise": "",
            "station": "",
            "path_to_source_file": str(path_to_file),
            "sample_rate": "",
            "instrument_metadata": "Sea-Bird SBE 19plus V2",
            "custom_metadata": "",
            "sensor_metadata": "",
            "provenance_metadata": "",
        },
    )

    ds["cast_id"] = ("scan", data["cast_id"].to_numpy())
    ds.add.parameter("temperature", data["temperature"].to_numpy())
    ds.add.parameter("conductivity", data["conductivity"].to_numpy())
    ds.add.parameter("pressure", data["pressure"].to_numpy())

    ds["voltage0"] = (
        "scan",
        data["voltage0"].to_numpy(),
        {
            "long_name": "auxiliary sensor voltage channel 0",
            "units": "V",
        },
    )

    ds.add.processing_metadata(
        module="sbe19_to_xarray",
    )

    return ds