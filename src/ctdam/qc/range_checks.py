from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ctdam.qc.quality_flags import SeaDataNetFlag


@dataclass(frozen=True)
class RangeLimit:
    """
    Range limits for one CTD parameter.

    Values inside the valid range are flagged as probably good.
    Values slightly outside the valid range but inside the error margin are
    flagged as probably bad.
    Values outside the range and margin are flagged as bad.
    """

    parameter_name: str
    minimum: float | None = None
    maximum: float | None = None
    error_margin: float = 0.0
    test_name: str = "range_check"


DEFAULT_RANGE_LIMITS: dict[str, RangeLimit] = {
    "prDM": RangeLimit(
        parameter_name="prDM",
        minimum=0.0,
        maximum=10000.0,
        error_margin=1.0,
        test_name="pressure_range",
    ),
    "t090C": RangeLimit(
        parameter_name="t090C",
        minimum=-2.0,
        maximum=50.0,
        error_margin=0.5,
        test_name="temperature_range",
    ),
    "t190C": RangeLimit(
        parameter_name="t190C",
        minimum=-2.0,
        maximum=50.0,
        error_margin=0.5,
        test_name="temperature_2_range",
    ),
    "c0mS/cm": RangeLimit(
        parameter_name="c0mS/cm",
        minimum=0.0,
        maximum=100.0,
        error_margin=0.1,
        test_name="conductivity_range",
    ),
    "c1mS/cm": RangeLimit(
        parameter_name="c1mS/cm",
        minimum=0.0,
        maximum=100.0,
        error_margin=0.1,
        test_name="conductivity_2_range",
    ),
    "sal00": RangeLimit(
        parameter_name="sal00",
        minimum=0.0,
        maximum=60.0,
        error_margin=0.05,
        test_name="salinity_range",
    ),
    "sal11": RangeLimit(
        parameter_name="sal11",
        minimum=0.0,
        maximum=60.0,
        error_margin=0.05,
        test_name="salinity_2_range",
    ),
    "sbox0Mm/Kg": RangeLimit(
        parameter_name="sbox0Mm/Kg",
        minimum=0.0,
        maximum=300.0,
        error_margin=5.0,
        test_name="oxygen_range",
    ),
    "sbox1Mm/Kg": RangeLimit(
        parameter_name="sbox1Mm/Kg",
        minimum=0.0,
        maximum=300.0,
        error_margin=5.0,
        test_name="oxygen_2_range",
    ),
}


def apply_range_check_to_parameter(
    parameter,
    limit: RangeLimit | None = None,
) -> int:
    """
    Apply range QC to one Parameter.

    Passing values are flagged as 2 = probably good.
    Values outside the range but inside the error margin are flagged as
    3 = probably bad.
    Values outside the range and error margin are flagged as 4 = bad.
    Missing or declared bad-fill values are flagged as 9 = missing.
    """
    limit = limit or DEFAULT_RANGE_LIMITS.get(parameter.name)

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

    finite = np.isfinite(values)
    declared_bad = _is_declared_bad_flag(
        values,
        getattr(parameter, "bad_flag", None),
    )

    valid = finite & ~declared_bad
    missing_mask = ~finite | declared_bad

    error_margin = max(float(limit.error_margin), 0.0)

    probably_bad_mask = np.zeros(values.shape, dtype=bool)
    bad_mask = np.zeros(values.shape, dtype=bool)

    if limit.minimum is not None:
        probably_bad_mask |= (
            valid
            & (values < limit.minimum)
            & (values >= limit.minimum - error_margin)
        )
        bad_mask |= valid & (values < limit.minimum - error_margin)

    if limit.maximum is not None:
        probably_bad_mask |= (
            valid
            & (values > limit.maximum)
            & (values <= limit.maximum + error_margin)
        )
        bad_mask |= valid & (values > limit.maximum + error_margin)

    pass_mask = valid & ~probably_bad_mask & ~bad_mask

    changed = 0

    changed += parameter.update_flags(
        mask=pass_mask,
        new_flag=SeaDataNetFlag.PROBABLY_GOOD,
        test_name=limit.test_name,
        reason=(
            f"value passed range test: min={limit.minimum}, "
            f"max={limit.maximum}, error_margin={error_margin}"
        ),
    )

    changed += parameter.update_flags(
        mask=probably_bad_mask,
        new_flag=SeaDataNetFlag.PROBABLY_BAD,
        test_name=limit.test_name,
        reason=(
            f"value inside range error margin: min={limit.minimum}, "
            f"max={limit.maximum}, error_margin={error_margin}"
        ),
    )

    changed += parameter.update_flags(
        mask=bad_mask,
        new_flag=SeaDataNetFlag.BAD,
        test_name=limit.test_name,
        reason=(
            f"value failed range test beyond error margin: "
            f"min={limit.minimum}, max={limit.maximum}, "
            f"error_margin={error_margin}"
        ),
    )

    changed += parameter.update_flags(
        mask=missing_mask,
        new_flag=SeaDataNetFlag.MISSING,
        test_name=limit.test_name,
        reason="missing value or declared bad-fill value",
    )

    return changed


def apply_range_check(
    ctd_data,
    limit: RangeLimit,
) -> int:
    """
    Apply one range check to one parameter in a CTDData object.
    """
    if limit.parameter_name not in ctd_data:
        return 0

    return apply_range_check_to_parameter(
        ctd_data[limit.parameter_name],
        limit,
    )


def apply_default_range_checks(
    ctd_data,
    *,
    limits: dict[str, RangeLimit] | None = None,
) -> dict[str, int]:
    """
    Apply default range checks to all matching parameters in a CTDData object.
    """
    limits = limits or DEFAULT_RANGE_LIMITS

    results: dict[str, int] = {}

    for parameter_name, limit in limits.items():
        results[parameter_name] = apply_range_check(ctd_data, limit)

    return results


def _is_declared_bad_flag(values: np.ndarray, bad_flag) -> np.ndarray:
    if bad_flag is None:
        return np.zeros(values.shape, dtype=bool)

    try:
        flag = float(bad_flag)
    except (TypeError, ValueError):
        return np.zeros(values.shape, dtype=bool)

    return np.isclose(values, flag, rtol=0.0, atol=1e-30)
