import shutil
import sys
from pathlib import Path

from ctdam.parser.parameter import Parameter
from ctdam.parser.processing_steps import CnvProcessingSteps


def default_seabird_exe_path() -> Path:
    """Creates a platform-dependent default path to the Sea-Bird exes."""
    exe_path = "Program Files (x86)/Sea-Bird/SBEDataProcessing-Win32/"
    if sys.platform.startswith("win"):
        path_prefix = Path("C:/")
    else:
        path_prefix = Path.home().joinpath(".wine/drive_c")
    return path_prefix.joinpath(exe_path)


def is_directly_measured_value(parameter: Parameter) -> bool:
    """
    Returns whether a parameter has been measured via a sensor or is calculated.
    """
    value_list = [
        "Pressure",
        "Conductivity",
        "Temperature",
        "Oxygen",
        "PAR/Irradiance",
        "SPAR",
        "Fluorescence",
        "Turbidity",
    ]
    return parameter.metadata["name"] in value_list


def get_alignment_delay_and_correlation_values(
    processing_info: CnvProcessingSteps,
) -> list:
    """
    Finds the two numerical values in the processing output produced by the
    custom alignment tool. These are extracted separately for each sensor and
    sorted inside of list[tuple] structure.
    """
    output = []
    sensor = 1
    for step in processing_info:
        if step.name == "alignctd":
            for param, value in step.metadata.items():
                if str(sensor - 1) not in param:
                    continue
                # catch files that have used Sea-Bird align or were run with a
                # pre-set value, these are not interesting for this extraction
                try:
                    delay, metainfo = value.split(",")
                except ValueError:
                    continue
                sensor_tuple = (delay.strip()[:-1], metainfo.strip()[-4:])
                output.append(sensor_tuple)
                sensor += 1
            if sensor > 2:
                break

    return output


def fill_file_type_dir(file_type_dir: Path, file: Path, copy: bool = True):
    """
    Copies the target input and output files into individual type
    directories.

    A 'file type directory' is a directory that is meant to collect all
    the file of the same file extension that accumulate over multiple
    processings. For typical Sea-Bird processings you usually end up with
    something like this:

    root-dir
        - hex
        - cnv
        - XMLCON
        - btl
        - bl
        - hdr

    Parameters
    ----------
    file: Path

    copy: bool
            (Default value = True)

    Returns
    -------

    """
    file_dir = file_type_dir.joinpath(file.suffix.strip("."))
    if not file_dir.exists():
        file_dir.mkdir(parents=True)
    new_path = file_dir.joinpath(file.name)
    if copy:
        try:
            shutil.copyfile(file, new_path)
        except shutil.SameFileError:
            pass
    else:
        file.rename(new_path)


class BinnedDataError(Exception):
    """A custom error to throw when binned data has been detected."""

    def __init__(self, file_name: str, step_name: str):
        super().__init__(
            f"{step_name} cannot be applied to binned data in {file_name}"
        )
