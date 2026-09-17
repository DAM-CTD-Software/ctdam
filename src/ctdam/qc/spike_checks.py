from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xarray as xr

from ctdam.qc.quality_flags import SeaDataNetFlag


@dataclass(frozen=True)
class SpikeLimit:
    """
    Spike-test settings for one parameter.
    """

    parameter_name: str
    threshold: float
    test_name: str = "spike_check"


DEFAULT_SPIKE_LIMITS: dict[str, SpikeLimit] = {
    "temperature": SpikeLimit(
        parameter_name="temperature",
        threshold=0.5,
        test_name="temperature_spike",
    ),
    "salinity": SpikeLimit(
        parameter_name="salinity",
        threshold=0.2,
        test_name="salinity_spike",
    ),
    "oxygen": SpikeLimit(
        parameter_name="oxygen",
        threshold=20.0,
        test_name="oxygen_spike",
    ),
}


def apply_spike_check_to_parameter(
    parameter: xr.DataArray,
    limit: SpikeLimit | None = None,
) -> xr.DataArray:
    """
    Apply neighbour-based spike QC to one xarray parameter.

    Internal tested non-spike values are flagged as 2 = probably good.
    Spike values are flagged as 3 = probably bad.
    Missing values are flagged as 9 = missing.

    The first and last values are not tested by this spike algorithm.
    """
    limit = limit or DEFAULT_SPIKE_LIMITS.get(parameter.name)

    if limit is None:
        return xr.full_like(
            parameter,
            SeaDataNetFlag.NO_QC,
            dtype="i1",
        )

    try:
        values = np.asarray(parameter.data, dtype=float)
    except (TypeError, ValueError):
        return xr.full_like(
            parameter,
            SeaDataNetFlag.MISSING,
            dtype="i1",
        )

    if values.shape[0] < 3:
        return xr.full_like(
            parameter,
            SeaDataNetFlag.NO_QC,
            dtype="i1",
        )

    finite = np.isfinite(values)
    declared_bad = _is_declared_bad_flag(
        values,
        parameter.attrs.get("bad_flag"),
    )

    missing_mask = ~finite | declared_bad

    previous_values = values[:-2]
    center_values = values[1:-1]
    next_values = values[2:]

    previous_valid = finite[:-2] & ~declared_bad[:-2]
    center_valid = finite[1:-1] & ~declared_bad[1:-1]
    next_valid = finite[2:] & ~declared_bad[2:]

    internal_testable = previous_valid & center_valid & next_valid

    neighbour_mean = (previous_values + next_values) / 2.0
    spike_size = np.abs(center_values - neighbour_mean)

    internal_spike = internal_testable & (spike_size > limit.threshold)
    internal_pass = internal_testable & ~internal_spike

    spike_mask = np.zeros(values.shape, dtype=bool)
    pass_mask = np.zeros(values.shape, dtype=bool)

    spike_mask[1:-1] = internal_spike
    pass_mask[1:-1] = internal_pass

    flags = np.full(
        values.shape,
        SeaDataNetFlag.NO_QC,
        dtype=np.int8,
    )

    flags[pass_mask] = SeaDataNetFlag.PROBABLY_GOOD
    flags[spike_mask] = SeaDataNetFlag.PROBABLY_BAD
    flags[missing_mask] = SeaDataNetFlag.MISSING

    return xr.DataArray(
        flags,
        dims=parameter.dims,
        coords=parameter.coords,
        name=parameter.name,
    )


def apply_spike_check(
    ds: xr.Dataset,
    limit: SpikeLimit,
) -> xr.DataArray | None:
    """Apply one spike check to one parameter in an xarray Dataset."""
    if limit.parameter_name not in ds:
        return None

    return apply_spike_check_to_parameter(
        ds[limit.parameter_name],
        limit,
    )


def apply_default_spike_checks(
    ds: xr.Dataset,
    *,
    limits: dict[str, SpikeLimit] | None = None,
) -> dict[str, xr.DataArray]:
    """Apply default spike checks to matching parameters."""
    limits = limits or DEFAULT_SPIKE_LIMITS

    results: dict[str, xr.DataArray] = {}

    for parameter_name, limit in limits.items():
        result = apply_spike_check(ds, limit)

        if result is not None:
            results[parameter_name] = result

    return results


def _is_declared_bad_flag(values: np.ndarray, bad_flag) -> np.ndarray:
    if bad_flag is None:
        return np.zeros(values.shape, dtype=bool)

    try:
        flag = float(bad_flag)
    except (TypeError, ValueError):
        return np.zeros(values.shape, dtype=bool)

    return np.isclose(values, flag, rtol=0.0, atol=1e-30)
