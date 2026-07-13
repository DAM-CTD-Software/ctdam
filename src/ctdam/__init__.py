import logging
import tomllib
from pathlib import Path

import ctdam.parser.custom_xarray_accessors

logger = logging.getLogger(__name__)

APPNAME='ctdam'
PARAMETER_NAME_MAPPING_FILE = Path(__file__).parent.joinpath(
    "parameter_name_mapping.toml"
)

if not PARAMETER_NAME_MAPPING_FILE.exists():
    PARAMETER_NAME_MAPPING_FILE.touch()
    logger.info(
        f"No sensor mapping file found in {PARAMETER_NAME_MAPPING_FILE}. Created a blank one."
    )

with open(PARAMETER_NAME_MAPPING_FILE, "rb") as file:
    PARAMETER_MAPPING = tomllib.load(file)
