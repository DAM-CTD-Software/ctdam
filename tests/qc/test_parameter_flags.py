import numpy as np
import pytest

from ctdam.parser.parameter import Parameter
from ctdam.qc.quality_flags import SeaDataNetFlag


def make_parameter() -> Parameter:
    metadata = {
        "shortname": "dummy",
        "name": "Dummy parameter",
        "unit": "",
        "longinfo": "Dummy parameter",
    }

    return Parameter(
        data=np.array([1.0, 2.0, 99.0]),
        metadata=metadata,
    )


def test_parameter_initializes_flags_on_instantiation():
    parameter = make_parameter()

    assert parameter.has_flags()
    assert np.array_equal(parameter.flags, np.array([0, 0, 0], dtype=np.int8))
    assert np.array_equal(
        parameter.flag_history, np.array(["", "", ""], dtype=object)
    )


def test_parameter_initialize_flags_does_not_overwrite_by_default():
    parameter = make_parameter()
    parameter.flags[0] = int(SeaDataNetFlag.BAD)

    result = parameter.initialize_flags()

    assert result is False
    assert parameter.flags[0] == int(SeaDataNetFlag.BAD)


def test_parameter_initialize_flags_can_overwrite():
    parameter = make_parameter()
    parameter.flags[0] = int(SeaDataNetFlag.BAD)

    result = parameter.initialize_flags(overwrite=True)

    assert result is True
    assert np.array_equal(parameter.flags, np.array([0, 0, 0], dtype=np.int8))


def test_parameter_update_flags_changes_selected_values():
    parameter = make_parameter()

    changed = parameter.update_flags(
        mask=parameter.data > 40,
        new_flag=SeaDataNetFlag.BAD,
        test_name="manual_range",
        reason="above maximum",
    )

    assert changed == 1
    assert np.array_equal(parameter.flags, np.array([0, 0, 4], dtype=np.int8))


def test_parameter_update_flags_creates_history_entry():
    parameter = make_parameter()

    parameter.update_flags(
        mask=parameter.data > 40,
        new_flag=SeaDataNetFlag.BAD,
        test_name="manual_range",
        reason="above maximum",
    )

    assert parameter.flag_history[0] == ""
    assert parameter.flag_history[1] == ""
    assert "test=manual_range" in parameter.flag_history[2]
    assert "old=0" in parameter.flag_history[2]
    assert "new=4" in parameter.flag_history[2]
    assert "reason=above maximum" in parameter.flag_history[2]


def test_parameter_update_flags_rejects_wrong_mask_length():
    parameter = make_parameter()

    with pytest.raises(ValueError):
        parameter.update_flags(
            mask=np.array([True, False]),
            new_flag=SeaDataNetFlag.BAD,
            test_name="bad_mask",
        )


def test_parameter_update_flags_does_not_downgrade_existing_bad_flag():
    parameter = make_parameter()

    parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.BAD,
        test_name="range_check",
    )

    changed = parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.PROBABLY_BAD,
        test_name="spike_check",
    )

    assert changed == 0
    assert parameter.flags[2] == int(SeaDataNetFlag.BAD)
    assert "test=range_check" in parameter.flag_history[2]
    assert "test=spike_check" not in parameter.flag_history[2]


def test_parameter_update_flags_can_upgrade_existing_flag():
    parameter = make_parameter()

    parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.PROBABLY_BAD,
        test_name="spike_check",
    )

    changed = parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.BAD,
        test_name="range_check",
    )

    assert changed == 1
    assert parameter.flags[2] == int(SeaDataNetFlag.BAD)
    assert "test=spike_check" in parameter.flag_history[2]
    assert "test=range_check" in parameter.flag_history[2]


def test_parameter_update_flags_overwrite_can_downgrade():
    parameter = make_parameter()

    parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.BAD,
        test_name="range_check",
    )

    changed = parameter.update_flags(
        mask=np.array([False, False, True]),
        new_flag=SeaDataNetFlag.PROBABLY_BAD,
        test_name="manual_overwrite",
        overwrite=True,
    )

    assert changed == 1
    assert parameter.flags[2] == int(SeaDataNetFlag.PROBABLY_BAD)
    assert "test=manual_overwrite" in parameter.flag_history[2]
