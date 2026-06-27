from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ctdam.parser.quality_flags import SeaDataNetFlag


@dataclass(frozen=True)
class SpikeLimit:
    """
    Spike-test settings for one parameter.

    A point is flagged when it strongly differs from its neighbouring values.
    """

    parameter_name: str
    threshold: float
    flag: SeaDataNetFlag = SeaDataNetFlag.PROBABLY_BAD
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


def apply_spike_check(
    ctd_data,
    limit: SpikeLimit,
) -> int:
    """
    Apply a simple neighbour-based spike check to one parameter.

    For each internal point i, compare value[i] with the average of its
    neighbours value[i-1] and value[i+1].

    The first and last points are not tested because they do not have two
    neighbours.

    Returns
    -------
    int
        Number of values whose flag was changed.
    """
    parameter_name = limit.parameter_name

    if parameter_name not in ctd_data:
        return 0

    parameter = ctd_data[parameter_name]
    values = np.asarray(parameter.data, dtype=float)

    if values.size < 3:
        return 0

    mask = np.zeros(values.shape, dtype=bool)

    previous_values = values[:-2]
    center_values = values[1:-1]
    next_values = values[2:]

    neighbour_mean = (previous_values + next_values) / 2.0
    spike_size = np.abs(center_values - neighbour_mean)

    finite = (
        np.isfinite(previous_values)
        & np.isfinite(center_values)
        & np.isfinite(next_values)
    )

    internal_mask = finite & (spike_size > limit.threshold)

    mask[1:-1] = internal_mask

    reason = f"spike threshold={limit.threshold}"

    return parameter.update_flags(
        mask=mask,
        new_flag=limit.flag,
        test_name=limit.test_name,
        reason=reason,
    )


def apply_default_spike_checks(
    ctd_data,
    *,
    limits: dict[str, SpikeLimit] | None = None,
) -> dict[str, int]:
    """
    Apply default spike checks to all matching parameters.

    Returns
    -------
    dict[str, int]
        Mapping from parameter name to number of changed flags.
    """
    limits = limits or DEFAULT_SPIKE_LIMITS

    results: dict[str, int] = {}

    for parameter_name, limit in limits.items():
        results[parameter_name] = apply_spike_check(ctd_data, limit)

    return results


__all__ = [
    "SpikeLimit",
    "DEFAULT_SPIKE_LIMITS",
    "apply_spike_check",
    "apply_default_spike_checks",
]
