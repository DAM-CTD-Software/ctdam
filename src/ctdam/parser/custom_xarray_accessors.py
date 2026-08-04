import importlib.metadata
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import gsw_xarray
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from ctdam import PARAMETER_MAPPING, SBS_NAME_MAPPING
from ctdam.parser.seabird_data_files import BottleLogFile
from ctdam.proc.modules.available_modules import map_proc_name_to_class
from ctdam.proc.workflow import Workflow

logger = logging.getLogger(__name__)


@xr.register_dataset_accessor("proc")
class ProcessingAccessor:
    def __init__(self, ds):
        self._ds = ds

    def module(self, name: str, arguments: dict = {}):
        try:
            module = map_proc_name_to_class(name)
        except KeyError:
            logger.error(f"Unknown module {name}, aborting.")
            return
        self._ds = module(self._ds, arguments=arguments)

    def workflow(
        self,
        modules: dict | list = [
            "loop_removal",
            "wildedit_geomar",
            "wfilter",
            "alignctd",
            "celltm",
            "binavg",
        ],
        other_settings: dict = {},
    ):
        if not "modules" in other_settings.keys():
            if isinstance(modules, list):
                modules = {k: {} for k in modules}
            other_settings["modules"] = modules
        Workflow(self._ds, other_settings)

    def last(self) -> str:
        try:
            last_module, _ = (
                self._ds.attrs["provenance_metadata"]
                .split("\n")[-2]
                .split("_", 1)
            )
        except Exception:
            last_module = ""
        return last_module


@xr.register_dataset_accessor("add")
class InputAccessor:
    def __init__(self, ds):
        self._ds = ds

    def parameter(self, name: str, data: np.ndarray):
        if name in PARAMETER_MAPPING.keys():
            basic_name = name
            try:
                cf_name = PARAMETER_MAPPING[name]["cf"]["name"]
            except KeyError:
                return
        elif name in SBS_NAME_MAPPING.keys():
            basic_name = SBS_NAME_MAPPING[name]["base"]
            try:
                cf_name = SBS_NAME_MAPPING[name]["cf"]["name"]
            except KeyError:
                return
        else:
            return
        # no dual sensors or quality flags
        if basic_name in ["flag", "latitude", "longitude"]:
            self._ds[basic_name] = (
                ("scan",),
                data,
                {
                    "standard_name": cf_name,
                    "units": PARAMETER_MAPPING[basic_name]["cf"]["unit"],
                },
            )
            return
        ancillary_variable_name = f"{basic_name}_qc"
        if basic_name in self._ds.data_vars:
            try:
                data = np.stack([self._ds.get(basic_name).data, data], axis=-1)
                dims = ("scan", "sensor")
                ancillary_variable = np.zeros((len(data), 2), dtype="i1")
            except (ValueError, IndexError):
                logger.error(
                    f"Could not combine {basic_name} data: {self._ds.get(basic_name).data} and {data}"
                )
                dims = ("scan",)
                ancillary_variable = np.zeros((len(data)), dtype="i1")
        else:
            dims = ("scan",)
            ancillary_variable = np.zeros((len(data)), dtype="i1")

        self._ds[basic_name] = (
            dims,
            data,
            {
                "standard_name": cf_name,
                "units": PARAMETER_MAPPING[basic_name]["cf"]["unit"],
                "ancillary_variables": ancillary_variable_name,
            },
        )

        self._ds[ancillary_variable_name] = (
            dims,
            ancillary_variable,
            {
                "standard_name": "status_flag",
                "flag_values": np.array([0, 1, 2, 3, 4, 9], dtype="i1"),
                "flag_meanings": "no_qc good_data probably_good_data probably_bad_data bad_data missing_value",
            },
        )

    def bottles(
        self,
        file_path: Path | str = "",
        bl_file: BottleLogFile | None = None,
        bottle_capacity: int = 25,
    ):
        if not bl_file:
            if not file_path:
                try:
                    ctd_file = Path(self._ds.attrs["path_to_source_file"])
                    file_path = ctd_file.with_suffix(".bl")
                except KeyError:
                    logger.error("No input file path")
                    return

            try:
                bl_file = BottleLogFile(file_path)
            except Exception as error:
                logger.error(
                    f"Could not open {file_path} as .bl file: {error}"
                )
                return
        assert isinstance(bl_file, BottleLogFile)
        bl_info_array = np.zeros(self._ds.access.size())
        df = bl_file.df
        if "Cast" in self._ds.meta.custom().keys():
            df["Bottle ID"] = df["Bottle ID"].apply(
                self._calculate_global_bottle_id,
                args=(bottle_capacity,),
            )
            long_name = "bottle firing indicator (global Bottle ID)"
        else:
            long_name = "bottle firing indicator"
        for _, line in df.iterrows():
            bl_info_array[int(line.start_range) : int(line.end_range)] = line[
                "Bottle ID"
            ]
        self._ds["bottle_info"] = xr.DataArray(
            bl_info_array,
            dims="scan",
            attrs={
                "long_name": long_name,
                "flag_values": np.insert(df["Bottle ID"].values, 0, [0]),
                "flag_meanings": "no_bottle "
                + " ".join(
                    [f"bottle_{value}" for value in df["Bottle ID"].values]
                ),
            },
        )

    def _calculate_global_bottle_id(
        self,
        bottle_number: int,
        bottle_capacity: int,
    ) -> int:
        cast_number = int(self._ds.meta.custom()["Cast"])
        return bottle_capacity * (cast_number) + int(bottle_number)

    def processing_metadata(
        self,
        module: str,
        key: str,
        value: str,
    ):
        last_module = self._ds.proc.last()
        if last_module != module:
            # general header for every module
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y.%m.%d %H:%M:%S"
            )
            try:
                version = f", v{importlib.metadata.version('ctdam')}"
            except Exception:
                version = ""
            self._ds.attrs["provenance_metadata"] += (
                f"{module}_metainfo = {timestamp}, ctdam python version{version}\n"
            )

        self._ds.attrs["provenance_metadata"] += f"{module}_{key} = {value}\n"

    def teos10_vars(self, ds=None):
        """Compute common derived TEOS-10 variables from CTD base variables."""
        ds = ds if ds else self._ds
        # check variables
        try:
            _, _, _ = ds["pressure"], ds["temperature"], ds["salinity"]
        except KeyError as error:
            logger.error(f"Could not calculate basic TEOS-10 vars: {error}")
            return
        # create postional columns, if missing
        try:
            _, _ = ds["longitude"], ds["latitude"]
        except KeyError:
            if ds.attrs["position"]:
                shape = (self._ds.access.size(),)
                position = ds.attrs["position"]
                self.parameter("latitude", np.full(shape, position[0]))
                self.parameter("longitude", np.full(shape, position[1]))
            else:
                logger.error(
                    "Missing position information for absolute salinity calculcation."
                )
                return

        ds["absolute_salinity"] = self._ds.gsw.SA_from_SP()
        ds["conservative_temperature"] = self._ds.gsw.CT_from_t()
        ds["density"] = self._ds.gsw.sigma0()


@xr.register_dataset_accessor("meta")
class MetadataAccessor:
    def __init__(self, ds):
        self._ds = ds

    def provenance(self) -> dict:
        metadata_dict = {}
        for line in self._ds.attrs["provenance_metadata"].split("\n")[:-1]:
            name, metadata = line.split("_", 1)
            try:
                key, value = metadata.split("=", 1)
            except ValueError:
                if ":" in metadata:
                    key, value = metadata.split(":", 1)
                else:
                    continue
            if not name in metadata_dict.keys():
                metadata_dict[name] = {}
            metadata_dict[name][key.strip()] = value.strip()

        return metadata_dict

    def custom(self) -> dict:
        metadata_dict = {}
        for line in self._ds.attrs["custom_metadata"].split("\n")[:-1]:
            try:
                key, value = line.split("=", 1)
            except ValueError:
                if ":" in line:
                    key, value = line.split(":", 1)
                else:
                    continue
            metadata_dict[key.strip()] = value.strip()

        return metadata_dict


@xr.register_dataset_accessor("access")
class DataRetrievalAccessor:
    def __init__(self, ds):
        self._ds = ds

    def btl_info(self) -> xr.Dataset:
        ds = self._ds.set_coords("bottle_info")
        ds = ds.groupby("bottle_info").mean()
        ds = ds.drop_sel(bottle_info=0)
        return ds

    def spans(
        self, name: str | xr.DataArray, bad_flag: float = -9.990e-29
    ) -> Tuple:
        if isinstance(name, str):
            data_array = self._ds[name]
        else:
            data_array = name
        try:
            mx = np.ma.masked_array(data_array, mask=data_array == bad_flag)
            span = (np.nanmin(mx), np.nanmax(mx))
        except ValueError:
            span = (0, 0)
        return span

    def size(self) -> int:
        return self._ds.scan.size

    def sample_rate(self) -> float:
        # TODO: implement real parsing
        return 24

    def binned(self) -> bool:
        # TODO: implement real parsing
        return False

    def sensor_strand(self, strand="primary") -> xr.Dataset:
        if strand == 1 or strand == "1":
            strand = "primary"
        elif strand == 2 or strand == "2":
            strand = "secondary"
        sensor_vars = {}
        for name, da in self._ds.data_vars.items():
            if "sensor" in da.dims:
                sensor_vars[name] = da.sel(sensor=strand).drop_vars("sensor")
            else:
                sensor_vars[name] = da
        sensor_vars = xr.Dataset(
            sensor_vars,
            coords={
                k: v
                for k, v in self._ds.coords.items()
                if "sensor" not in self._ds[k].dims
                if k in self._ds.coords
            },
        )
        return sensor_vars

    def flattened_ds(
        self,
        ds=None,
        suffix_map={"primary": "", "secondary": "2"},
    ) -> xr.Dataset:
        """Turn (scan, sensor) variables into separate (scan,) variables, suffixed like Sea-Bird columns."""
        ds = ds if ds else self._ds
        flat_vars = {}
        for name, da in ds.data_vars.items():
            if not name in PARAMETER_MAPPING.keys():
                continue
            if "sensor" in da.dims:
                for sensor_val, suffix in suffix_map.items():
                    flat_vars[f"{name}{suffix}"] = da.sel(
                        sensor=sensor_val
                    ).drop_vars("sensor")
            else:
                flat_vars[name] = da
        ds_flat = xr.Dataset(
            flat_vars,
            coords={
                k: v
                for k, v in ds.coords.items()
                if "sensor" not in ds[k].dims
                if k in ds.coords
            },
        )
        return ds_flat

    def numpy_array(self, ds=None) -> np.ndarray:
        ds = ds if ds else self._ds
        ds_flat = self.flattened_ds(ds)
        return np.column_stack([ds_flat[var].values for var in ds_flat])

    def pandas_dataframe(self) -> pd.DataFrame:
        ds_flat = self.flattened_ds()
        return ds_flat.to_dataframe()


@xr.register_dataset_accessor("export")
class ExportAccessor:
    def __init__(self, ds):
        self._ds = ds

    def to_cnv(
        self,
        file_path: Path | str = "",
        reduced_header: bool = False,
        bad_flag=-9.990e-29,
    ):
        file_path = (
            Path(file_path)
            if file_path
            else self._ds.attrs["path_to_source_file"]
        )
        # create output format
        ds = self._ds.copy(deep=True)
        var_to_drop = []
        for var in ds.data_vars:
            if var not in PARAMETER_MAPPING.keys():
                var_to_drop.append(var)

        ds.drop_vars(var_to_drop)

        try:
            data = self._array2cnv(ds, bad_flag)
            header = self._create_cnv_header(ds, reduced_header, bad_flag)
        except ValueError as error:
            logger.error(f"Could not create cnv in {file_path}: {error}")
            return
        output_cnv_data = [*header, *data]
        # writing content out
        try:
            with open(
                file_path.with_suffix(".cnv"), "w", encoding="latin-1"
            ) as file:
                for line in output_cnv_data:
                    try:
                        file.write(line)
                    except TypeError:
                        logger.error(line)

        except IOError as error:
            logger.error(f"Could not write cnv file: {error}")

    def _create_cnv_header(
        self,
        ds: xr.Dataset,
        reduced_header: bool = False,
        bad_flag=-9.990e-29,
    ) -> list:
        """
        Re-creates the .cnv header.

        Parameters
        ----------
        parameters: Parameters | None
            A specific parameters instance or self.parameters
        reduced_header: bool
            Whether to build a streamlined non-cnv header (Default value = False)

        Returns
        -------
        A list representing the metadata header of a .cnv file.
        """
        sb9_info = (
            [
                f"* {data.strip()}{os.linesep}"
                for data in ds.attrs["instrument_metadata"].split("\n")
            ]
            if not reduced_header
            else []
        )
        data_table_description = self._form_data_table_info(
            ds,
            output_spans=not reduced_header,
            bad_flag=bad_flag,
        )
        system_utc = ds.attrs["instrument_metadata"].split("\n")[-2]
        custom_metadata = (
            [
                f"** {data}{os.linesep}"
                for data in ds.attrs["custom_metadata"].split("\n")
            ]
            if not reduced_header
            else []
        )
        sensor_data = (
            [
                f"# {data}{os.linesep}"
                for data in ds.attrs["sensor_metadata"].split("\n")
            ]
            if not reduced_header
            else []
        )
        processing_info = (
            [
                f"# {data.strip()}{os.linesep}"
                for data in ds.attrs["provenance_metadata"].split("\n")
            ]
            if not reduced_header
            else []
        )
        header = [
            *sb9_info[:-2],
            *custom_metadata[:-1],
            f"* {system_utc.strip()}{os.linesep}",
            *[f"# {data}" for data in data_table_description],
            *sensor_data[:-1],
            *processing_info[:-1],
            f"# file_type = ascii{os.linesep}",
            f"*END*{os.linesep}",
        ]
        return header

    def _form_data_table_info(
        self,
        ds,
        output_spans: bool = True,
        bad_flag=-9.990e-29,
    ) -> list:
        """
        Recreates the data table metadata.

        These can be column names and spans and uses the stuctured
        dictionaries these values were stored in.

        Parameters
        ----------
        output_spans: bool
            Whether to recreate data spans (Default value = True)

        Returns
        -------
        A list that represents the data table metadata
        """
        new_table_info = []
        spans = []
        # 'data table stats'
        ds_flat = self._ds.access.flattened_ds(ds)
        index = 0
        for name in ds_flat:
            data_array = ds_flat[name]
            # 'data tables names'
            # check whether second sensor
            if name[-1] == "2":
                sensor = "secondary"
                name = name[:-1]
            else:
                sensor = "primary"
            try:
                parameter = PARAMETER_MAPPING[name]["seabird"]
            except KeyError:
                continue
            unit = ds[name].units.replace("/", "")
            if unit in parameter.keys():
                metadata = parameter[unit][sensor]
            elif "primary" in parameter.keys():
                metadata = parameter[sensor]
            else:
                metadata = parameter

            new_table_info.append(
                f"name {index} = {metadata['shortname']}: {metadata['longinfo']}{os.linesep}"
            )

            # 'data table spans'
            if output_spans:
                span = self._ds.access.spans(data_array, bad_flag)
                output_format = self._set_output_format(name)
                try:
                    spans.append(
                        f"span {index} = {output_format.format(span[0])}, {output_format.format(span[1])}{os.linesep}"
                    )
                except ValueError:
                    spans.append(f"span {index} = None, None")
            index += 1
        new_table_info.insert(0, f"nquan = {index}{os.linesep}")
        new_table_info.insert(
            1, f"nvalues = {data_array.shape[0]}{os.linesep}"
        )
        new_table_info.insert(2, f"units = specified{os.linesep}")
        return [*new_table_info, *spans, *self._extra_data_table_desc(ds)]

    def _extra_data_table_desc(
        self,
        ds: xr.DataArray,
    ) -> list:
        """
        A helper method for .cnv header generation.

        Parameters
        ----------
        data_table_description: list
            Data table information from parameters
        system_utc: str
            The system time

        Returns
        -------
        A list representing the data table desc in a metadata header of a .cnv file.
        """
        out_list = []
        nmea_time = [
            line
            for line in ds.attrs["instrument_metadata"].split("\n")
            if line.startswith("NMEA UTC")
        ]
        if nmea_time:
            start_time_string = f"{nmea_time[0].split('=')[1].strip()} [NMEA time, first data scan.]"
        else:
            start_time_string = "unknown"

        out_list = [
            # f"# interval = {self.bin_unit}: {1 / self.sample_rate:1.7f}{os.linesep}",
            f"interval = seconds: 0.0416667{os.linesep}",
            f"start_time = {start_time_string}{os.linesep}",
            f"bad_flag = -9.990e-29{os.linesep}",
        ]

        return out_list

    def _array2cnv(
        self,
        ds: xr.Dataset,
        bad_flag=-9.990e-29,
    ) -> list:
        """
        Parse the xarray data into .cnv data format.


        Parameters
        ----------
        parameters: Parameters | None
            A specific parameters instance or self.parameters
        bad_flag :
            The value to use to indicate bad values (Default value = -9.990e-29)

        Returns
        -------
        A list that represents the .cnv data format.
        """
        result = []
        ds = ds.fillna(bad_flag)
        output_formats = [self._set_output_format(var) for var in ds]

        full_array = self._ds.access.numpy_array(ds)

        for row in full_array:
            formatted_row = [
                output_format.format(elem)[:10].rjust(11)
                for elem, output_format in zip(row, output_formats)
            ]
            formatted_row = "".join(formatted_row)
            result.append(formatted_row + os.linesep)
        return result

    def _sort_parameters(
        self,
        ds,
        top: list = [
            "depSM",
            "prDM",
            "t090C",
            "t190C",
            "sal00",
            "sal11",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "flECO-AFL",
            "turbWETntu0",
            "par",
            "spar",
        ],
        bottom: list = [
            "gsw_densityA0",
            "gsw_densityA1",
            "gsw_saA0",
            "gsw_saA1",
            "gsw_ctA0",
            "gsw_ctA1",
            "sbeox0ML/L",
            "sbeox1ML/L",
            "c0mS/cm",
            "c1mS/cm",
            "latitude",
            "longitude",
            "flag",
        ],
    ) -> dict:
        """
        Allows sorting of parameter instances for output reasons.

        Parameters
        ----------
        top: list
            The parameters to fix to the top
        bottom: list
            The parameters to fix to the bottom

        Returns
        -------
        A dictionary of the sorted parameters.
        """
        # ensure parameters at the top
        new_data = {}
        for shortname in top:
            for param in self.data.values():
                if shortname == param.name:
                    new_data[shortname] = param

        # ensure parameters at the bottom
        bottom_data = {}
        for shortname in bottom:
            for param in self.data.values():
                if shortname == param.name:
                    bottom_data[shortname] = param

        for param in self.data.values():
            if param.name not in [*top, *bottom]:
                new_data[param.name] = param

        self.data = {**new_data, **bottom_data}
        return self.data

    def _set_output_format(self, name) -> str:
        """Sets a parameter-specific number format."""
        if name in ["flag"]:
            decimal_digits = 0
        elif name in [
            "time",
            "pressure",
            "oxygen",
            "depth",
        ]:
            decimal_digits = 3
        elif name in ["latitude", "longitude"]:
            decimal_digits = 5
        elif name == "conductivity":
            decimal_digits = 6
        else:
            decimal_digits = 4
        return f"{{:.{decimal_digits}f}}"


@xr.register_dataset_accessor("qc")
class QCAccessor:
    def __init__(self, ds):
        self._ds = ds

    def _flag_var(self, var):
        return self._ds[var].attrs["ancillary_variables"]

    def set_flag(self, var, flag_value, where):
        """Flag values matching a boolean mask, leaving data untouched."""
        qc_var = self._flag_var(var)
        self._ds[qc_var] = self._ds[qc_var].where(~where, flag_value)
        return self._ds

    def edit_value(self, var, new_value, where, flag_value=4):
        """Correct/despike a value and flag it in the same call."""
        qc_var = self._flag_var(var)
        self._ds[var] = self._ds[var].where(~where, new_value)
        self._ds[qc_var] = self._ds[qc_var].where(~where, flag_value)
        return self._ds

    def masked(self, var, keep_flags=(1, 2)):
        """Return the data with bad-flagged points as NaN."""
        qc_var = self._flag_var(var)
        return self._ds[var].where(self._ds[qc_var].isin(keep_flags))

    def check_sensor_agreement(self, var, threshold, flag_value=3):
        """Flag scans where primary/secondary sensors diverge beyond threshold."""
        diff = abs(
            self._ds[var].sel(sensor="primary")
            - self._ds[var].sel(sensor="secondary")
        )
        bad = diff > threshold
        qc_var = self._flag_var(var)
        self._ds[qc_var].loc[dict(sensor="primary")] = (
            self._ds[qc_var].sel(sensor="primary").where(~bad, flag_value)
        )
        self._ds[qc_var].loc[dict(sensor="secondary")] = (
            self._ds[qc_var].sel(sensor="secondary").where(~bad, flag_value)
        )
        return self._ds

    def best_estimate(self, var, prefer="primary", keep_flags=(1, 2)):
        """Pick primary unless flagged bad, falling back to secondary."""
        primary = self._ds[var].sel(sensor="primary")
        secondary = self._ds[var].sel(sensor="secondary")
        primary_qc = self._ds[self._flag_var(var)].sel(sensor=prefer)
        return primary.where(primary_qc.isin(keep_flags), secondary)


@xr.register_dataset_accessor("vis")
class PlotAccessor:
    def __init__(self, ds):
        self._ds = ds

    def profile(self, var, sensor=None, qc_mask=True, ax=None, **kwargs):
        """Plot var vs pressure, oceanographic convention (pressure down)."""
        ax = ax or plt.gca()
        da = self._ds[var]

        if "sensor" in da.dims:
            if sensor is not None:
                da = da.sel(sensor=sensor)
            else:
                for s in self._ds.sensor.values:
                    self._ds.vis.profile(
                        var, sensor=s, ax=ax, qc_mask=qc_mask, **kwargs
                    )
                ax.invert_yaxis()
                ax.legend()
                return ax

        if qc_mask:
            da = self._ds.qc.masked(var)

        ax.plot(da, self._ds.pressure, **kwargs)
        ax.invert_yaxis()
        ax.set_xlabel(
            f"{da.attrs.get('long_name', var)} ({da.attrs.get('units', '')})"
        )
        ax.set_ylabel("Pressure (dbar)")
        return ax

    def flagged(self, var, ax=None):
        """Highlight good vs flagged points."""
        ax = ax or plt.gca()
        good = self._ds[self._ds.qc._flag_var(var)].isin([1, 2])
        ax.plot(
            self._ds[var].where(good), self._ds.pressure, ".", label="good"
        )
        ax.plot(
            self._ds[var].where(~good),
            self._ds.pressure,
            "x",
            color="C3",
            label="flagged",
        )
        ax.invert_yaxis()
        ax.legend()
        return ax
