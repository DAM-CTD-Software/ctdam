import logging
from pathlib import Path

import pytest

base_path = Path("sbs_data")
cnv_path = base_path.joinpath("cnv")
hex_path = base_path.joinpath("hex")
psa_path = base_path.joinpath("psa")
btl_path = base_path.joinpath("btl")
test_hex = hex_path.joinpath("EMB356_11-1.hex")
test_cnv = cnv_path.joinpath("EMB356_11-1.cnv")
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
        "--run_seabird",
        "-S",
        action="store_true",
        default=False,
        help="Whether to run seabird processing modules during the tests.",
    )
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
def run_seabird_modules(request) -> bool:
    """
    Makes the boolean flag of the command line option available to individual
    tests.
    """
    return request.config.getoption("--run_seabird")


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
    skip_non_seabird = pytest.mark.skip(reason="No seabird option given.")
    skip_long = pytest.mark.skip(reason="Test too long.")
    for item in items:
        if not config.getoption("--run_seabird"):
            if "seabird" in item.keywords:
                item.add_marker(skip_non_seabird)
        if not config.getoption("--run_long"):
            if "long" in item.keywords:
                item.add_marker(skip_long)


def check_and_remove_file(output_file: Path | str):
    output_file = Path(output_file)
    if output_file.exists():
        assert True
        output_file.unlink()
    else:
        logger.error(f"Could not find the expected file: {output_file}")
        assert False
