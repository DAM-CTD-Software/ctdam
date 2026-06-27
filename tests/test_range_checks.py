import numpy as np

from ctdam.parser.parameter import Parameter
from ctdam.parser.quality_flags import SeaDataNetFlag
from ctdam.qc.range_checks import RangeLimit, apply_range_check


class DummyCTDData(dict):
    """
    Minimal CTDData-like object for unit testing range checks.
    """
    pass


def make_parameter(name: str, values) -> Parameter:
    metadata = {
        "shortname": name,
        "name": name,
        "unit": "",
        "longinfo": name,
    }

    return Parameter(
        data=np.array(values, dtype=float),
        metadata=metadata,
    )


def test_apply_range_check_flags_values_below_minimum():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [-3.0, 10.0, 11.0])

    limit = RangeLimit(
        parameter_name="t090C",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(ctd_data["t090C"].flags, np.array([4, 0, 0], dtype=np.int8))
    assert "test=temperature_range" in ctd_data["t090C"].flag_history[0]


def test_apply_range_check_flags_values_above_maximum():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [10.0, 41.0, 11.0])

    limit = RangeLimit(
        parameter_name="t090C",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(ctd_data["t090C"].flags, np.array([0, 4, 0], dtype=np.int8))


def test_apply_range_check_flags_bad_flag_values():
    ctd_data = DummyCTDData()
    ctd_data["sbox0Mm/Kg"] = make_parameter(
        "sbox0Mm/Kg",
        [300.0, -9.990e-29, 301.0],
    )

    limit = RangeLimit(
        parameter_name="sbox0Mm/Kg",
        minimum=0.0,
        maximum=700.0,
        test_name="oxygen_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(
        ctd_data["sbox0Mm/Kg"].flags,
        np.array([0, 4, 0], dtype=np.int8),
    )


def test_apply_range_check_returns_zero_if_parameter_missing():
    ctd_data = DummyCTDData()

    limit = RangeLimit(
        parameter_name="t090C",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 0


def test_apply_range_check_writes_reason_to_history():
    ctd_data = DummyCTDData()
    ctd_data["sal00"] = make_parameter("sal00", [7.0, 99.0])

    limit = RangeLimit(
        parameter_name="sal00",
        minimum=0.0,
        maximum=42.0,
        test_name="salinity_range",
    )

    apply_range_check(ctd_data, limit)

    assert "reason=outside allowed range" in ctd_data["sal00"].flag_history[1]
    assert "max=42.0" in ctd_data["sal00"].flag_history[1]