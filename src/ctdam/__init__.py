import inspect
import warnings
from xarray.core.extensions import AccessorRegistrationWarning

warnings.filterwarnings("ignore", category=AccessorRegistrationWarning)

import gsw_xarray._accessor as acc
import gsw_xarray._core as core
import gsw_xarray._function_utils as fu

# tidy package imports
from ._settings import APPNAME, form_sbs_name_lookup, read_mapping_file


def __getattr__(name):
    if name == "PARAMETER_MAPPING":
        return read_mapping_file()
    elif name == "SBS_NAME_MAPPING":
        return form_sbs_name_lookup()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from .conv import (
    get_cast_borders,
    get_potential_density,
    oxygen_mlperl_to_umolperkg,
    oxygen_mlperl_to_umolperl,
    oxygen_umolperkg_to_umolperl,
    oxygen_umolperl_to_umolperkg,
)
from .parser import (
    BottleFile,
    BottleLogFile,
    Casts,
    CnvFile,
    HexFile,
    XMLCONFile,
    read_cnv,
    read_ctd_data,
    read_hex,
)
from .proc import (
    Workflow,
    fill_file_type_dir,
    is_directly_measured_value,
    process,
)
from .vis import basic_bokeh_plot, create_main_html, cruise_plots

__all__ = [
    "get_cast_borders",
    "oxygen_umolperkg_to_umolperl",
    "oxygen_mlperl_to_umolperkg",
    "oxygen_mlperl_to_umolperl",
    "oxygen_umolperkg_to_umolperl",
    "oxygen_umolperl_to_umolperkg",
    "get_potential_density",
    "Casts",
    "read_ctd_data",
    "read_cnv",
    "read_hex",
    "CnvFile",
    "HexFile",
    "BottleFile",
    "BottleLogFile",
    "XMLCONFile",
    "process",
    "is_directly_measured_value",
    "fill_file_type_dir",
    "Workflow",
    "cruise_plots",
    "create_main_html",
    "basic_bokeh_plot",
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
