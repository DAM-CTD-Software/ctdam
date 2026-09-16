import logging
import tomllib
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

APPNAME = "ctdam"
PARAMETER_NAME_MAPPING_FILE = Path(__file__).parent.joinpath(
    "parameter_name_mapping.toml"
)

if not PARAMETER_NAME_MAPPING_FILE.exists():
    PARAMETER_NAME_MAPPING_FILE.touch()
    logger.info(
        f"No sensor mapping file found in {PARAMETER_NAME_MAPPING_FILE}. Created a blank one."
    )


@lru_cache(maxsize=1)
def read_mapping_file() -> dict:
    with open(PARAMETER_NAME_MAPPING_FILE, "rb") as file:
        return tomllib.load(file)


@lru_cache(maxsize=1)
def form_sbs_name_lookup() -> dict:
    out_dict = {}
    for name, parameter in read_mapping_file().items():
        if not "seabird" in parameter.keys():
            continue
        try:
            if "primary" in parameter["seabird"]:
                out_dict[parameter["seabird"]["primary"]["shortname"]] = {
                    "base": name,
                    "cf": parameter["cf"]["name"],
                }
                out_dict[parameter["seabird"]["secondary"]["shortname"]] = {
                    "base": name,
                    "cf": parameter["cf"]["name"],
                }
            else:
                try:
                    out_dict[parameter["seabird"]["shortname"]] = {
                        "base": name,
                        "cf": parameter["cf"]["name"],
                    }
                except KeyError:
                    # different seabird units present
                    for unit in parameter["seabird"]:
                        out_dict[
                            parameter["seabird"][unit]["primary"]["shortname"]
                        ] = {
                            "base": name,
                            "cf": parameter["cf"]["name"],
                        }

                        out_dict[
                            parameter["seabird"][unit]["secondary"][
                                "shortname"
                            ]
                        ] = {
                            "base": name,
                            "cf": parameter["cf"]["name"],
                        }

        except KeyError:
            continue
    return out_dict
