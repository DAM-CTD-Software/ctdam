import numpy as np

from ctdam.parser.parameter import Parameter
from ctdam.qc.quality_flags import SeaDataNetFlag
from ctdam.qc.range_checks import RangeLimit, apply_range_check


class DummyCTDData(dict):
    """
    Minimal CTDData-like object for unit testing range checks.
    """


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
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [-3.0, 10.0, 11.0])

    limit = RangeLimit(
        parameter_name="dummy_temp",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 3
    assert np.array_equal(
        ctd_data["dummy_temp"].flags,
        np.array([4, 2, 2], dtype=np.int8),
    )
    assert "test=temperature_range" in ctd_data["dummy_temp"].flag_history[0]
    assert "failed range test" in ctd_data["dummy_temp"].flag_history[0]


def test_apply_range_check_flags_values_above_maximum():
    ctd_data = DummyCTDData()
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [10.0, 41.0, 11.0])

    limit = RangeLimit(
        parameter_name="dummy_temp",
        minimum=-2.5,
        maximum=40.0,
        test_name="temperature_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 3
    assert np.array_equal(
        ctd_data["dummy_temp"].flags,
        np.array([2, 4, 2], dtype=np.int8),
    )


def test_apply_range_check_flags_bad_flag_values_as_missing():
    ctd_data = DummyCTDData()
    ctd_data["dummy_oxygen"] = make_parameter(
        "dummy_oxygen",
        [300.0, -9.990e-29, 301.0],
    )

    limit = RangeLimit(
        parameter_name="dummy_oxygen",
        minimum=0.0,
        maximum=700.0,
        test_name="oxygen_range",
    )

    changed = apply_range_check(ctd_data, limit)

    assert changed == 3
    assert np.array_equal(
        ctd_data["dummy_oxygen"].flags,
        np.array([2, 9, 2], dtype=np.int8),
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
    ctd_data["dummy_sal"] = make_parameter("dummy_sal", [7.0, 99.0])

    limit = RangeLimit(
        parameter_name="dummy_sal",
        minimum=0.0,
        maximum=42.0,
        test_name="salinity_range",
    )

    apply_range_check(ctd_data, limit)

    assert "value failed range test" in ctd_data["dummy_sal"].flag_history[1]
    assert "max=42.0" in ctd_data["dummy_sal"].flag_history[1]


def test_parameter_instantiation_auto_applies_range_check():
    parameter = make_parameter("t090C", [10.0, 99.0, -3.0])

    assert np.array_equal(
        parameter.flags,
        np.array([2, 4, 4], dtype=np.int8),
    )

    assert "test=temperature_range" in parameter.flag_history[0]
    assert "passed range test" in parameter.flag_history[0]

    assert "test=temperature_range" in parameter.flag_history[1]
    assert "failed range test" in parameter.flag_history[1]


def test_parameter_instantiation_flags_missing_values_as_9():
    parameter = make_parameter("sbox0Mm/Kg", [250.0, -9.990e-29, np.nan])

    assert parameter.flags[0] == int(SeaDataNetFlag.PROBABLY_GOOD)
    assert parameter.flags[1] == int(SeaDataNetFlag.MISSING)
    assert parameter.flags[2] == int(SeaDataNetFlag.MISSING)
