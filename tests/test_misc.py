import pytest
from conftest import cnv_path, test_btl

from ctdam.parser.seabird_data_files import BottleFile
from ctdam.utils import create_event_string, read_event_name
from ctdam.vis.visualize import plot


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


def test_bottle_reading():
    btl = BottleFile(test_btl)
    btl.selecting_rows()
    assert not "Statistic" in btl.df.columns


def test_plotting_entry_function(tmp_path):
    plot(
        input=cnv_path,
        output_directory=tmp_path,
        filter="EMB",
        show_html=False,
        use_multiprocessing=False,
    )
    assert (
        len(list(cnv_path.glob("EMB*.cnv")))
        == len(list(tmp_path.glob("*.html"))) - 1
    )
