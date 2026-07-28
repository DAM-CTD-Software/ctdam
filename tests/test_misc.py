import pytest

from ctdam.utils import create_event_string, read_event_name


@pytest.mark.parametrize(
    ("input_name", "expected_output"),
    [
        ("EMB346_082-01", "EMB346_082-01"),
        ("msm123-011_02", "MSM123_011-02"),
        ("M42-52-1", "M42_052-01"),
        ("So308-2_008_3", "SO308_2_008-03"),
    ],
)
def test_event_name_parsing(input_name, expected_output):
    cruise, station = read_event_name(input_name)
    assert create_event_string(cruise, station) == expected_output
