from __future__ import annotations

from dataclasses import dataclass

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
