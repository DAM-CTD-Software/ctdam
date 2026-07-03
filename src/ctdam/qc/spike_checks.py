from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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
    "t090C": SpikeLimit(
        parameter_name="t090C",
        threshold=0.5,
        test_name="temperature_spike",
    ),
    "t190C": SpikeLimit(
        parameter_name="t190C",
        threshold=0.5,
        test_name="temperature_2_spike",
    ),
    "sal00": SpikeLimit(
        parameter_name="sal00",
        threshold=0.2,
        test_name="salinity_spike",
    ),
    "sal11": SpikeLimit(
        parameter_name="sal11",
        threshold=0.2,
        test_name="salinity_2_spike",
    ),
    "sbox0Mm/Kg": SpikeLimit(
        parameter_name="sbox0Mm/Kg",
        threshold=20.0,
        test_name="oxygen_spike",
    ),
    "sbox1Mm/Kg": SpikeLimit(
        parameter_name="sbox1Mm/Kg",
        threshold=20.0,
        test_name="oxygen_2_spike",
    ),
}


def apply_spike_check_to_parameter(
    parameter,
    limit: SpikeLimit | None = None,
) -> int:
    """
    Apply neighbour-based spike QC to one Parameter.

    Internal tested non-spike values are flagged as 2 = probably good.
    Spike values are flagged as 3 = probably bad.
    Missing or declared bad-fill values are flagged as 9 = missing.

    The first and last values are not tested by this spike algorithm.
    """
    limit = limit or DEFAULT_SPIKE_LIMITS.get(parameter.name)

    if limit is None:
        return 0

    try:
        values = np.asarray(parameter.data, dtype=float)
    except (TypeError, ValueError):
        mask = np.ones(len(parameter), dtype=bool)
        return parameter.update_flags(
            mask=mask,
            new_flag=SeaDataNetFlag.MISSING,
            test_name=limit.test_name,
            reason="could not convert to numeric values",
        )

    if values.size < 3:
        return 0

    finite = np.isfinite(values)
    declared_bad = _is_declared_bad_flag(
        values,
        getattr(parameter, "bad_flag", None),
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

    changed = 0

    changed += parameter.update_flags(
        mask=pass_mask,
        new_flag=SeaDataNetFlag.PROBABLY_GOOD,
        test_name=limit.test_name,
        reason=f"value passed spike test: threshold={limit.threshold}",
    )

    changed += parameter.update_flags(
        mask=spike_mask,
        new_flag=SeaDataNetFlag.PROBABLY_BAD,
        test_name=limit.test_name,
        reason=f"value failed spike test: threshold={limit.threshold}",
    )

    changed += parameter.update_flags(
        mask=missing_mask,
        new_flag=SeaDataNetFlag.MISSING,
        test_name=limit.test_name,
        reason="missing value or declared bad-fill value",
    )

    return changed


def apply_spike_check(
    ctd_data,
    limit: SpikeLimit,
) -> int:
    """
    Apply one spike check to one parameter in a CTDData object.
    """
    if limit.parameter_name not in ctd_data:
        return 0

    return apply_spike_check_to_parameter(
        ctd_data[limit.parameter_name], limit
    )


def apply_default_spike_checks(
    ctd_data,
    *,
    limits: dict[str, SpikeLimit] | None = None,
) -> dict[str, int]:
    """
    Apply default spike checks to all matching parameters.
    """
    limits = limits or DEFAULT_SPIKE_LIMITS

    results: dict[str, int] = {}

    for parameter_name, limit in limits.items():
        results[parameter_name] = apply_spike_check(ctd_data, limit)

    return results


def _is_declared_bad_flag(values: np.ndarray, bad_flag) -> np.ndarray:
    if bad_flag is None:
        return np.zeros(values.shape, dtype=bool)

    try:
        flag = float(bad_flag)
    except (TypeError, ValueError):
        return np.zeros(values.shape, dtype=bool)

    return np.isclose(values, flag, rtol=0.0, atol=1e-30)
