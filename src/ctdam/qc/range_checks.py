from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ctdam.parser.quality_flags import SeaDataNetFlag


@dataclass(frozen=True)
class RangeLimit:
    """
    Range limits for one CTD parameter.

    Values below minimum or above maximum are flagged.
    """

    parameter_name: str
    minimum: float | None = None
    maximum: float | None = None
    flag: SeaDataNetFlag = SeaDataNetFlag.BAD
    test_name: str = "range_check"


DEFAULT_RANGE_LIMITS: dict[str, RangeLimit] = {
    # Sea water pressure in dbar. Slight negative tolerance is allowed.
    "prDM": RangeLimit(
        parameter_name="prDM",
        minimum=-5.0,
        maximum=12000.0,
        test_name="pressure_range",
    ),

    # ITS-90 temperature in degree Celsius.
    "t090C": RangeLimit(
        parameter_name="t090C",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    ),
    "t190C": RangeLimit(
        parameter_name="t190C",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_2_range",
    ),

    # Practical salinity.
    "sal00": RangeLimit(
        parameter_name="sal00",
        minimum=0.0,
        maximum=42.0,
        test_name="salinity_range",
    ),
    "sal11": RangeLimit(
        parameter_name="sal11",
        minimum=0.0,
        maximum=42.0,
        test_name="salinity_2_range",
    ),

    # Oxygen in umol/kg. Negative values and very high values are suspicious.
    "sbox0Mm/Kg": RangeLimit(
        parameter_name="sbox0Mm/Kg",
        minimum=0.0,
        maximum=700.0,
        test_name="oxygen_range",
    ),
    "sbox1Mm/Kg": RangeLimit(
        parameter_name="sbox1Mm/Kg",
        minimum=0.0,
        maximum=700.0,
        test_name="oxygen_2_range",
    ),

    # Depth in metres.
    "depSM": RangeLimit(
        parameter_name="depSM",
        minimum=-5.0,
        maximum=12000.0,
        test_name="depth_range",
    ),
}


def apply_range_check(
    ctd_data,
    limit: RangeLimit,
) -> int:
    """
    Apply one range check to one parameter in a CTDData object.

    This function does not parse files and does not create a new dataset.
    It updates the existing Parameter flags and flag_history.

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

    mask = np.zeros(values.shape, dtype=bool)

    finite = np.isfinite(values)

    if limit.minimum is not None:
        mask |= finite & (values < limit.minimum)

    if limit.maximum is not None:
        mask |= finite & (values > limit.maximum)

    # Treat declared bad-flag values as missing/bad.
    bad_flag = getattr(parameter, "bad_flag", None)
    if bad_flag is not None:
        try:
            mask |= np.isclose(values, float(bad_flag), rtol=0.0, atol=1e-30)
        except (TypeError, ValueError):
            pass

    reason = _format_reason(limit)

    return parameter.update_flags(
        mask=mask,
        new_flag=limit.flag,
        test_name=limit.test_name,
        reason=reason,
    )


def apply_default_range_checks(
    ctd_data,
    *,
    limits: dict[str, RangeLimit] | None = None,
) -> dict[str, int]:
    """
    Apply default range checks to all matching parameters in a CTDData object.

    Returns
    -------
    dict[str, int]
        Mapping from parameter name to number of changed flags.
    """
    limits = limits or DEFAULT_RANGE_LIMITS

    results: dict[str, int] = {}

    for parameter_name, limit in limits.items():
        changed = apply_range_check(ctd_data, limit)
        results[parameter_name] = changed

    return results


def _format_reason(limit: RangeLimit) -> str:
    parts: list[str] = []

    if limit.minimum is not None:
        parts.append(f"min={limit.minimum}")

    if limit.maximum is not None:
        parts.append(f"max={limit.maximum}")

    return "outside allowed range: " + ", ".join(parts)


__all__ = [
    "RangeLimit",
    "DEFAULT_RANGE_LIMITS",
    "apply_range_check",
    "apply_default_range_checks",
]