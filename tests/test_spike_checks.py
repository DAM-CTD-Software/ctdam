import numpy as np

from ctdam.parser.parameter import Parameter
from ctdam.parser.quality_flags import SeaDataNetFlag
from ctdam.qc.spike_checks import SpikeLimit, apply_spike_check


class DummyCTDData(dict):
    """
    Minimal CTDData-like object for unit testing spike checks.
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


def test_apply_spike_check_flags_center_spike():
    ctd_data = DummyCTDData()
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [10.0, 30.0, 10.0])

    limit = SpikeLimit(
        parameter_name="dummy_temp",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(
        ctd_data["dummy_temp"].flags,
        np.array([0, 3, 0], dtype=np.int8),
    )
    assert "test=temperature_spike" in ctd_data["dummy_temp"].flag_history[1]


def test_apply_spike_check_flags_smooth_internal_value_as_probably_good():
    ctd_data = DummyCTDData()
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [10.0, 10.1, 10.2])

    limit = SpikeLimit(
        parameter_name="dummy_temp",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(
        ctd_data["dummy_temp"].flags,
        np.array([0, 2, 0], dtype=np.int8),
    )


def test_apply_spike_check_does_not_flag_first_and_last_positions():
    ctd_data = DummyCTDData()
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [99.0, 10.0, 99.0])

    limit = SpikeLimit(
        parameter_name="dummy_temp",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 1
    assert ctd_data["dummy_temp"].flags[1] == int(SeaDataNetFlag.PROBABLY_BAD)
    assert ctd_data["dummy_temp"].flags[0] == int(SeaDataNetFlag.NO_QC)
    assert ctd_data["dummy_temp"].flags[2] == int(SeaDataNetFlag.NO_QC)


def test_apply_spike_check_returns_zero_for_short_parameter():
    ctd_data = DummyCTDData()
    ctd_data["dummy_temp"] = make_parameter("dummy_temp", [10.0, 20.0])

    limit = SpikeLimit(
        parameter_name="dummy_temp",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 0
    assert np.array_equal(
        ctd_data["dummy_temp"].flags,
        np.array([0, 0], dtype=np.int8),
    )


def test_apply_spike_check_returns_zero_if_parameter_missing():
    ctd_data = DummyCTDData()

    limit = SpikeLimit(
        parameter_name="dummy_temp",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 0


def test_apply_spike_check_writes_reason_to_history():
    ctd_data = DummyCTDData()
    ctd_data["dummy_sal"] = make_parameter("dummy_sal", [7.0, 20.0, 7.0])

    limit = SpikeLimit(
        parameter_name="dummy_sal",
        threshold=1.0,
        test_name="salinity_spike",
    )

    apply_spike_check(ctd_data, limit)

    assert "value failed spike test" in ctd_data["dummy_sal"].flag_history[1]
    assert "threshold=1.0" in ctd_data["dummy_sal"].flag_history[1]


def test_parameter_instantiation_auto_applies_spike_check():
    parameter = make_parameter("t090C", [10.0, 30.0, 10.0])

    assert np.array_equal(
        parameter.flags,
        np.array([2, 3, 2], dtype=np.int8),
    )

    assert "test=temperature_range" in parameter.flag_history[0]
    assert "test=temperature_spike" in parameter.flag_history[1]
