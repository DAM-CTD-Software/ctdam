from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xarray as xr

from ctdam.qc.quality_flags import SeaDataNetFlag


@dataclass(frozen=True)
class RangeLimit:
    """Range limits for one CTD parameter."""

    parameter_name: str
    minimum: float | None = None
    maximum: float | None = None
    test_name: str = "range_check"


DEFAULT_RANGE_LIMITS: dict[str, RangeLimit] = {
    "pressure": RangeLimit(
        parameter_name="pressure",
        minimum=0.0,
        maximum=10000.0,
        test_name="pressure_range",
    ),
    "temperature": RangeLimit(
        parameter_name="temperature",
        minimum=-2.0,
        maximum=50.0,
        test_name="temperature_range",
    ),
    "conductivity": RangeLimit(
        parameter_name="conductivity",
        minimum=0.0,
        maximum=100.0,
        test_name="conductivity_range",
    ),
    "salinity": RangeLimit(
        parameter_name="salinity",
        minimum=0.0,
        maximum=60.0,
        test_name="salinity_range",
    ),
    "oxygen": RangeLimit(
        parameter_name="oxygen",
        minimum=0.0,
        maximum=300.0,
        test_name="oxygen_range",
    ),
    # 10% deviation from the 1.78 expected value
    "flow_meter": RangeLimit(
        parameter_name="flow_meter",
        minimum=1.6,
        maximum=1.95,
        test_name="flow_meter_range",
    ),
}


def apply_range_check_to_parameter(
    parameter: xr.DataArray,
    limit: RangeLimit | None = None,
) -> xr.DataArray:
    """
    Apply range QC to one xarray parameter.

    Passing values are flagged as 2 = probably good.
    Failing values are flagged as 4 = bad.
    Missing values are flagged as 9 = missing.
    """
    limit = limit or DEFAULT_RANGE_LIMITS.get(parameter.name)

    if limit is None:
        return xr.full_like(
            parameter,
            SeaDataNetFlag.NO_QC,
            dtype="i1",
        )

    missing = parameter.isnull()

    failed = xr.zeros_like(parameter, dtype=bool)

    if limit.minimum is not None:
        failed = failed | (parameter < limit.minimum)

    if limit.maximum is not None:
        failed = failed | (parameter > limit.maximum)

    flags = xr.full_like(
        parameter,
        SeaDataNetFlag.PROBABLY_GOOD,
        dtype="i1",
    )

    flags = flags.where(~failed, SeaDataNetFlag.BAD)
    flags = flags.where(~missing, SeaDataNetFlag.MISSING)

    return flags


def apply_range_check(
    ds: xr.Dataset,
    limit: RangeLimit,
) -> xr.DataArray | None:
    """Apply one range check to one parameter in an xarray Dataset."""
    if limit.parameter_name not in ds:
        return None

    return apply_range_check_to_parameter(
        ds[limit.parameter_name],
        limit,
    )


def apply_default_range_checks(
    ds: xr.Dataset,
    *,
    limits: dict[str, RangeLimit] | None = None,
) -> dict[str, xr.DataArray]:
    """Apply default range checks to matching parameters."""
    limits = limits or DEFAULT_RANGE_LIMITS

    results: dict[str, xr.DataArray] = {}

    for parameter_name, limit in limits.items():
        result = apply_range_check(ds, limit)

        if result is not None:
            results[parameter_name] = result

    return results


def apply_flow_meter_interval_check(
    ds: xr.Dataset,
    interval_seconds: float = 2.0,
    outlier_fraction: float = 0.30,
) -> xr.Dataset:
    """Set temperature, conductivity and oxygen QC to 4 in time windows
    where the fraction of bad flow_meter readings reaches the outlier_fraction.

    Each window starts at the next bad flow reading after the previous window.
    modify the dataset in place and return it.
    """

    flags = ds["flow_meter_qc"]
    time = ds["time"]

    # creates an array with false as defaults that are later turned true for the bad windows
    bad_windows = xr.zeros_like(flags, dtype=bool)

    if time.size == 0:
        return ds

    seconds = time.values - time.values[0]
    # for hex parsing because of different timestamp
    if np.issubdtype(time.dtype, np.datetime64):
        seconds = seconds / np.timedelta64(1, "s")

    # assign bad windows
    outliers = flags.values == 4
    next_start = 0

    if not outliers.any():
        return ds

    for start in np.flatnonzero(outliers):
        if start < next_start:
            continue
        end = np.searchsorted(seconds, seconds[start] + interval_seconds)
        if outliers[start:end].mean() >= outlier_fraction:
            bad_windows.values[start:end] = True
        next_start = end

    # change the parameters in the bad windows to bad
    if not bad_windows.values.any():
        return ds

    for parameter in ("temperature", "conductivity", "oxygen"):
        if parameter in ds:
            qc_name = f"{parameter}_qc"
            ds[qc_name][{"scan": bad_windows.values}] = 4

    return ds
