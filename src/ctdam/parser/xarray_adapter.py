from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


def ctddata_to_xarray(
    ctd_data,
    *,
    scan_dim: str = "scan",
    include_flags: bool = True,
) -> xr.Dataset:
    """
    Convert an existing ctdam CTDData object to an xarray.Dataset.

    This function does not parse raw files. It only converts the already parsed
    ctdam object model into xarray.
    """
    scan_size = _get_scan_size(ctd_data)
    scan = np.arange(scan_size, dtype=np.int64)

    ds = xr.Dataset(coords={scan_dim: scan})

    for parameter in ctd_data:
        name = str(parameter.name)
        values = np.asarray(parameter.data)

        if values.ndim == 0:
            values = np.full(scan_size, values.item())

        if values.shape[0] != scan_size:
            continue

        ds[name] = xr.DataArray(
            values,
            dims=(scan_dim,),
            coords={scan_dim: scan},
            attrs=_parameter_attrs(parameter),
        )

        if include_flags and getattr(parameter, "flags", None) is not None:
            flag_name = f"{name}_flag"
            ds[flag_name] = xr.DataArray(
                np.asarray(parameter.flags),
                dims=(scan_dim,),
                coords={scan_dim: scan},
                attrs={
                    "long_name": f"Quality flag for {name}",
                    "parameter": name,
                    "flag_convention": "SeaDataNet",
                },
            )

        if (
            include_flags
            and getattr(parameter, "flag_history", None) is not None
        ):
            history_name = f"{name}_flag_history"
            ds[history_name] = xr.DataArray(
                np.asarray(parameter.flag_history, dtype=object),
                dims=(scan_dim,),
                coords={scan_dim: scan},
                attrs={
                    "long_name": f"Quality flag history for {name}",
                    "parameter": name,
                },
            )

    ds.attrs.update(_ctddata_attrs(ctd_data))

    return ds


def _get_scan_size(ctd_data) -> int:
    """
    Infer scan length from the first one-dimensional parameter.
    """
    for parameter in ctd_data:
        values = np.asarray(parameter.data)

        if values.ndim == 1:
            return int(values.shape[0])

    raise ValueError("Could not infer scan dimension length from CTDData.")


def _parameter_attrs(parameter) -> dict[str, Any]:
    attrs: dict[str, Any] = {}

    metadata = getattr(parameter, "metadata", {})

    if isinstance(metadata, dict):
        for key, value in metadata.items():
            attrs[str(key)] = _safe_attr_value(value)

    attrs.setdefault("source_name", getattr(parameter, "name", ""))
    attrs.setdefault("units", getattr(parameter, "unit", ""))

    return attrs


def _ctddata_attrs(ctd_data) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "source": "ctdam CTDData",
    }

    path = getattr(ctd_data, "path_to_file", None)

    if path is not None:
        attrs["source_path"] = str(path)
        attrs["source_file_name"] = Path(str(path)).name

    return attrs


def _safe_attr_value(value: Any) -> Any:
    if value is None:
        return ""

    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"

    if isinstance(value, (str, int, float, np.integer, np.floating)):
        return value

    return str(value)


__all__ = ["ctddata_to_xarray"]
