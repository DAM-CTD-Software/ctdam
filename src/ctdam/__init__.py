import logging
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

logger = logging.getLogger(__name__)

APPNAME = "ctdam"
SENSOR_MAPPING_FILE = Path(__file__).parent.joinpath(
    "conv", "sensor_mapping.toml"
)

if not SENSOR_MAPPING_FILE.exists():
    SENSOR_MAPPING_FILE.touch()
    logger.info(
        f"No sensor mapping file found in {SENSOR_MAPPING_FILE}. Created a blank one."
    )

with open(SENSOR_MAPPING_FILE, "rb") as file:
    SENSOR_MAPPING = tomllib.load(file)
