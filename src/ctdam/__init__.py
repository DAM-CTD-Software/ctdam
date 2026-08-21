import inspect
import warnings

from xarray.core.extensions import AccessorRegistrationWarning

warnings.filterwarnings("ignore", category=AccessorRegistrationWarning)

import gsw_xarray._accessor as acc
import gsw_xarray._core as core
import gsw_xarray._function_utils as fu

# tidy package imports
from ._settings import form_sbs_name_lookup, read_mapping_file


def __getattr__(name):
    if name == "PARAMETER_MAPPING":
        return read_mapping_file()
    elif name == "SBS_NAME_MAPPING":
        return form_sbs_name_lookup()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from .conv import get_cast_borders
from .entry.casts import Casts
from .entry.functions import plot, process
from .parser import parse

__all__ = [
    "Casts",
    "get_cast_borders",
    "parse",
    "plot",
    "process",
]

# workaround for bug in gsw_xarray v0.5.0
_orig_bind = fu.args_and_kwargs_to_kwargs


def _args_and_kwargs_to_kwargs_fixed(func, args, kwargs, add_defaults):
    """Patch: strip the phantom **kwargs entry that apply_defaults() injects
    for gsw functions whose signature ends in **kwargs (e.g. SA_from_SP)."""
    s = inspect.signature(func)
    catchall = {
        name
        for name, p in s.parameters.items()
        if p.kind
        in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
    }
    result = _orig_bind(func, args, kwargs, add_defaults)
    for name in catchall:
        result.pop(name, None)
    return result


def _parameters_as_set_fixed(func):
    """Patch: don't treat the **kwargs catch-all itself as a real parameter."""
    s = inspect.signature(func)
    return {
        name
        for name, p in s.parameters.items()
        if p.kind
        not in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
    }


fu.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
core.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
acc.args_and_kwargs_to_kwargs = _args_and_kwargs_to_kwargs_fixed
fu.parameters_as_set = _parameters_as_set_fixed
acc.parameters_as_set = _parameters_as_set_fixed
