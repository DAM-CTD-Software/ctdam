import logging
import tomllib
from pathlib import Path


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


SBS_NAME_MAPPING = {}

for name, parameter in PARAMETER_MAPPING.items():
    if not "seabird" in parameter.keys():
        continue
    if "primary" in parameter["seabird"]:
        SBS_NAME_MAPPING[parameter["seabird"]["primary"]["shortname"]] = {
            "base": name,
            "cf": parameter["cf"]["name"],
        }
        SBS_NAME_MAPPING[
            parameter["seabird"]["secondary"]["shortname"]
        ] = {
            "base": name,
            "cf": parameter["cf"]["name"],
        }
    else:
        try:
            SBS_NAME_MAPPING[parameter["seabird"]["shortname"]] = {
                "base": name,
                "cf": parameter["cf"]["name"],
            }
        except KeyError:
            # different seabird units present
            for unit in parameter["seabird"]:
                SBS_NAME_MAPPING[
                    parameter["seabird"][unit]["primary"]["shortname"]
                ] = {
                    "base": name,
                    "cf": parameter["cf"]["name"],
                }

                SBS_NAME_MAPPING[
                    parameter["seabird"][unit]["secondary"]["shortname"]
                ] = {
                    "base": name,
                    "cf": parameter["cf"]["name"],
                }

