import logging
import tomllib
from pathlib import Path

import inspect
import gsw_xarray._function_utils as fu
import gsw_xarray._core as core
import gsw_xarray._accessor as acc

# workaround for bug in gsw_xarray v0.5.0
_orig_bind = fu.args_and_kwargs_to_kwargs

def _args_and_kwargs_to_kwargs_fixed(func, args, kwargs, add_defaults):
    """Patch: strip the phantom **kwargs entry that apply_defaults() injects
    for gsw functions whose signature ends in **kwargs (e.g. SA_from_SP)."""
    s = inspect.signature(func)
    catchall = {
        name for name, p in s.parameters.items()
        if p.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
    }
    result = _orig_bind(func, args, kwargs, add_defaults)
    for name in catchall:
        result.pop(name, None)
    return result

def _parameters_as_set_fixed(func):
    """Patch: don't treat the **kwargs catch-all itself as a real parameter."""
    s = inspect.signature(func)
    return {
        name for name, p in s.parameters.items()
        if p.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
    }

fu.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
core.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
acc.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
fu.parameters_as_set = _parameters_as_set_fixed
acc.parameters_as_set = _parameters_as_set_fixed

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
    try:
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

    except KeyError:
        continue
