import logging
from pathlib import Path

import pytest
from numpy.testing import assert_array_equal

from ctdam.parser.read_ctd_data import parse

base_path = Path("sbs_data")
cnv_path = base_path.joinpath("cnv")
hex_path = base_path.joinpath("hex")
psa_path = base_path.joinpath("psa")
btl_path = base_path.joinpath("btl")
test_hex = hex_path.joinpath("EMB356_11-1.hex")
test_cnv = cnv_path.joinpath("EMB356_11-1.cnv")
test_btl = btl_path.joinpath("EMB394_096-01_CTD_0088.btl")
proc_template = {
    "input": "",
    "output_type": "internal",
    "modules": {
        "wildedit_geomar": {},
        "wfilter": {},
        "alignctd": {},
        "celltm": {},
        "binavg": {},
    },
}

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """
    Adds a command line option to pytest that controls the skipping of code
    that runs seabird processing modules.
    """
    parser.addoption(
        "--run_long",
        "-L",
        action="store_true",
        default=False,
        help="Whether to run tests for the long cnvs as well.",
    )
    parser.addoption(
        "--create_files",
        "-F",
        action="store_true",
        default=False,
        help="Whether to write cnv files to disk.",
    )


@pytest.fixture
def run_long_tests(request) -> bool:
    """
    Makes the boolean flag of the command line option available to individual
    tests.
    """
    return request.config.getoption("--run_long")


@pytest.fixture
def create_files(request) -> bool:
    """
    Makes the boolean flag of the command line option available to individual
    tests.
    """
    return request.config.getoption("--create_files")


def pytest_collection_modifyitems(config, items):
    skip_long = pytest.mark.skip(reason="Test too long.")
    for item in items:
        if not config.getoption("--run_long"):
            if "long" in item.keywords:
                item.add_marker(skip_long)


@pytest.fixture(params=cnv_path.glob("*.cnv"))
def ds(request):
    return parse(request.param)


def check_and_remove_file(output_file: Path | str):
    output_file = Path(output_file)
    if output_file.exists():
        assert True
        output_file.unlink()
    else:
        logger.error(f"Could not find the expected file: {output_file}")
        assert False


def assert_different_np_array(array1, array2, ds=None):
    # ds only added for debugging reasons
    try:
        assert_array_equal(array1, array2)
    except AssertionError:
        assert True
    else:
        assert False
