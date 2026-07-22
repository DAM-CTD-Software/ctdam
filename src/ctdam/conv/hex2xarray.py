import logging
from pathlib import Path

import ctdproc
import xarray as xr

logger = logging.getLogger(__name__)


def decode_hex(
    hex: Path | str,
    downcast_only: bool = True,
    **kwargs,
) -> xr.Dataset:
    """
    Convert a Sea-Bird HEX file into an xarray.Dataset.

    The corresponding XMLCON file must be located in the same directory
    as the HEX file.

    Parameters
    ----------
    hex : Path | str
        Path to the HEX file.

    downcast_only : bool, optional
        Whether only the downcast should be returned.
        This is currently not implemented; the complete cast is returned.

    **kwargs
        Reserved for future processing options.

    Returns
    -------
    xr.Dataset
        Calibrated CTD data as an xarray.Dataset.

    Raises
    ------
    FileNotFoundError
        If the HEX file does not exist.

    RuntimeError
        If ctdproc cannot convert the HEX file.
    """
    hex_path = Path(hex)

    if not hex_path.is_file():
        raise FileNotFoundError(
            f"Could not find HEX file: {hex_path}"
        )

    if hex_path.suffix.lower() != ".hex":
        raise ValueError(
            f"Expected a .hex file, got: {hex_path}"
        )

    if downcast_only:
        logger.warning(
            "downcast_only is not implemented yet. "
            "Returning the complete cast."
        )

    try:
        dataset = ctdproc.io.CTDx(hex_path)
    except Exception as error:
        message = (
            f"Could not convert HEX file {hex_path}: {error}"
        )
        logger.error(message)
        raise RuntimeError(message) from error

    return dataset