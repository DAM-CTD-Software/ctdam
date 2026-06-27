import numpy as np

from ctdam.parser.parameter import Parameter
from ctdam.parser.quality_flags import SeaDataNetFlag
from ctdam.qc.spike_checks import SpikeLimit, apply_spike_check


class DummyCTDData(dict):
    """
    Minimal CTDData-like object for unit testing spike checks.
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


def test_apply_spike_check_flags_center_spike():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [10.0, 30.0, 10.0])

    limit = SpikeLimit(
        parameter_name="t090C",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 1
    assert np.array_equal(
        ctd_data["t090C"].flags,
        np.array([0, 3, 0], dtype=np.int8),
    )
    assert "test=temperature_spike" in ctd_data["t090C"].flag_history[1]


def test_apply_spike_check_does_not_flag_smooth_values():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [10.0, 10.1, 10.2])

    limit = SpikeLimit(
        parameter_name="t090C",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 0
    assert np.array_equal(
        ctd_data["t090C"].flags,
        np.array([0, 0, 0], dtype=np.int8),
    )


def test_apply_spike_check_does_not_flag_first_and_last_positions():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [99.0, 10.0, 99.0])

    limit = SpikeLimit(
        parameter_name="t090C",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 1

    # The middle value is flagged as a spike.
    assert ctd_data["t090C"].flags[1] == int(SeaDataNetFlag.PROBABLY_BAD)

    # First and last positions are not directly tested by the spike algorithm.
    assert ctd_data["t090C"].flags[0] == int(SeaDataNetFlag.NO_QC)
    assert ctd_data["t090C"].flags[2] == int(SeaDataNetFlag.NO_QC)


def test_apply_spike_check_returns_zero_for_short_parameter():
    ctd_data = DummyCTDData()
    ctd_data["t090C"] = make_parameter("t090C", [10.0, 20.0])

    limit = SpikeLimit(
        parameter_name="t090C",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 0


def test_apply_spike_check_returns_zero_if_parameter_missing():
    ctd_data = DummyCTDData()

    limit = SpikeLimit(
        parameter_name="t090C",
        threshold=1.0,
        test_name="temperature_spike",
    )

    changed = apply_spike_check(ctd_data, limit)

    assert changed == 0


def test_apply_spike_check_writes_reason_to_history():
    ctd_data = DummyCTDData()
    ctd_data["sal00"] = make_parameter("sal00", [7.0, 20.0, 7.0])

    limit = SpikeLimit(
        parameter_name="sal00",
        threshold=1.0,
        test_name="salinity_spike",
    )

    apply_spike_check(ctd_data, limit)

    assert "reason=spike threshold=1.0" in ctd_data["sal00"].flag_history[1]
