from pathlib import Path


from ctdam.proc.module import Module

from ctdam.proc.modules.air_pressure_correction import AirPressureCorrection

from ctdam.proc.modules.geomar_wildedit import WildeditGEOMAR
from ctdam.proc.modules.gsw_functions import GSWFunction
from ctdam.proc.modules.seabird_functions import (
    AlignCTD,
    BinAvg,
    CellTM,
    LoopRemoval,
    WFilter,
)
from ctdam.proc.utils import default_seabird_exe_path

mapper = {
    "airpressure": AirPressureCorrection(),
    "alignctd": AlignCTD(),
    "binavg": BinAvg(),
    "celltm": CellTM(),
    "loop_removal": LoopRemoval(),
    "wfilter": WFilter(),
    "wildedit_geomar": WildeditGEOMAR(),
}


def map_proc_name_to_class(module: str) -> Module:
    """
    Sets and maps the known processing modules to their respective
    module classes.

    Parameters
    ----------
    module : str
        Name of the module, that is being used inside the config.

    Returns
    -------
    A corresponding Module class.
    """
    if module.lower() in mapper.keys():
        return mapper[module.lower()]
    else:
        return GSWFunction(module)


def get_list_of_custom_exes(
    path_to_custom_exe_dir: Path | str | None = None,
) -> list[str]:
    """
    Get the paths to custom processing executables.

    Parameters
    ----------
    path_to_custom_exe_dir: Path | str | None
        The directory path were the .exes are stored in (Default value = None)

    Returns
    -------
    A list of paths.
    """
    if isinstance(path_to_custom_exe_dir, Path | str):
        return [exe.stem for exe in Path(path_to_custom_exe_dir).glob("*.exe")]
    else:
        return []


def get_list_of_installed_seabird_modules() -> list[str]:
    """Return paths of installed Sea-Bird processing modules."""
    seabird_path = default_seabird_exe_path()
    return [str(file.stem)[:-1] for file in seabird_path.glob("*W.exe")]


def get_dict_of_available_processing_modules(
    path_to_custom_exe_dir: Path | str | None = None,
) -> dict:
    """
    Collects all available processing modules in one dictionary.

    Parameters
    ----------
    path_to_custom_exe_dir: Path | str | None
        Path to custom executables (Default value = None)

    Returns
    -------
    A dictionary with all processing modules.
    """
    proc_dict = {
        "custom": [
            *list(mapper.values()),
            *get_list_of_custom_exes(path_to_custom_exe_dir),
        ],
        "seabird_exes": get_list_of_installed_seabird_modules(),
        # **processing_functions,
    }
    return proc_dict
