from .air_pressure_correction import AirPressureCorrection
from .bottle_file import BottleFile
from .detect_cast_borders import CastBorders
from .geomar_wildedit import WildeditGEOMAR
from .gsw_functions import GSWFunction
from .seabird_functions import AlignCTD, BinAvg, CellTM, LoopRemoval, WFilter

available_modules = [
    AirPressureCorrection,
    AlignCTD,
    BinAvg,
    BottleFile,
    CastBorders,
    CellTM,
    LoopRemoval,
    WFilter,
    WildeditGEOMAR,
]

proc_name_mapper = {}
for module in available_modules:
    for name in module().names:
        proc_name_mapper[name.lower()] = module


def map_proc_name_to_class(module: str):
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
    if module.lower() in proc_name_mapper.keys():
        return proc_name_mapper[module]()
    else:
        try:
            return GSWFunction(module)
        except AttributeError:
            raise ValueError(
                f"Module {module} is not a known processing module."
            )
