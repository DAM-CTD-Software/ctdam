import shutil
import sys
from pathlib import Path


def default_seabird_exe_path() -> Path:
    """Creates a platform-dependent default path to the Sea-Bird exes."""
    exe_path = "Program Files (x86)/Sea-Bird/SBEDataProcessing-Win32/"
    if sys.platform.startswith("win"):
        path_prefix = Path("C:/")
    else:
        path_prefix = Path.home().joinpath(".wine/drive_c")
    return path_prefix.joinpath(exe_path)


def is_directly_measured_value(parameter: str) -> bool:
    """
    Returns whether a parameter has been measured via a sensor or is calculated.
    """
    value_list = [
        "pressure",
        "conductivity",
        "temperature",
        "oxygen",
        "par/irradiance",
        "spar",
        "fluorescence",
        "turbidity",
    ]
    return parameter in value_list


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
