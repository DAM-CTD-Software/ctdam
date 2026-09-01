from __future__ import annotations

import importlib.metadata
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from ctdam import PARAMETER_MAPPING, SBS_NAME_MAPPING
from ctdam.exceptions import BinnedDataError
from ctdam.parser.seabird_data_files import BottleLogFile
from ctdam.proc.modules import (
    available_modules,
    map_proc_name_to_class,
    proc_name_mapper,
)
from ctdam.proc.workflow import Workflow
from ctdam.vis.visualize import basic_bokeh_plot

logger = logging.getLogger(__name__)


@xr.register_dataset_accessor("ctd")
class CTDAccessor:
    """
    CTD-specific tools for processing, data manipulation and plotting.

    This accessor should be the main way of interaction with ctd data,
    after loading it into a cf-compliant xarray dataset.

    Available sub-accessors are proc, add, meta, get, export, qc and vis.
    To e.g. bin your dataset you could run
    bin_ds = ds.ctd.proc.module("binavg")
    """

    def __init__(self, ds):
        self._ds = ds

    @property
    def proc(self) -> ProcessingAccessor:
        """Collection of processing specific functions on datasets."""
        return ProcessingAccessor(self._ds)

    @property
    def add(self) -> InputAccessor:
        """Functions for additional input to the dataset."""
        return InputAccessor(self._ds)

    @property
    def meta(self) -> MetadataAccessor:
        """Access CTD-specific metadata."""
        return MetadataAccessor(self._ds)

    @property
    def get(self) -> DataRetrievalAccessor:
        """Retrieve data information."""
        return DataRetrievalAccessor(self._ds)

    @property
    def export(self) -> ExportAccessor:
        """Write the dataset to disk in various formats."""
        return ExportAccessor(self._ds)

    @property
    def qc(self) -> QCAccessor:
        """Assess the quality of the data."""
        return QCAccessor(self._ds)

    @property
    def vis(self) -> PlotAccessor:
        """Visualize data."""
        return PlotAccessor(self._ds)


@xr.register_dataset_accessor("proc")
class ProcessingAccessor:
    """Collection of processing specific functions on datasets."""

    def __init__(self, ds):
        self._ds = ds

    def __getattr__(self, name):
        if name in proc_name_mapper:
            return proc_name_mapper[name]()(self._ds)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(proc_name_mapper.keys()))

    @property
    def available_modules(self):
        return [
            f"{m().names[0]}: {m().info.strip().replace('\n', ' ')}"
            for m in available_modules
        ]

    def module(self, name: str, arguments: dict = {}):
        """
        Apply processing module to the dataset.

        Parameters
        ----------
        name: str :
            The name of the module, needs to be in 'available_modules'

        arguments: dict :
            The arguments to run the module with
        """
        try:
            module = map_proc_name_to_class(name)
        except KeyError:
            logger.error(f"Unknown module {name}, aborting.")
            return
        self._ds = module(self._ds, arguments=arguments)
        return self._ds

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
        """
        Run a full processing workflow on the dataset

        Parameters
        ----------
        modules: dict | list :
            The individual modules to run

        other_settings: dict :
            Additional processing workflow settings
        """
        if not "modules" in other_settings.keys():
            if isinstance(modules, list):
                modules = {k: {} for k in modules}
            other_settings["modules"] = modules
        wf = Workflow(self._ds, other_settings)
        self._ds = wf.output
        return wf.output

    @property
    def last(self) -> str:
        """Returns the name of the last processing module applied."""
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
    """Functions for additional input to the dataset."""

    def __init__(self, ds):
        self._ds = ds

    def parameter(self, name: str, data: np.ndarray):
        """
        Create a new parameter inside of this dataset.

        Will take care of the naming and attribute metadata. Will create an
        additional quality flag column for the parameter.

        Parameters
        ----------
        name: str :
            The name of the parameter

        data: np.ndarray :
            The data of the new parameter
        """
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
        """
        Add bottle closing information to the dataset.

        Given a corresponding .bl file, the indices of the individual bottle
        closing times will be added as a new 'bottle_info' column to the
        dataset.

        Parameters
        ----------
        file_path: Path | str :
            The path to the .bl file
        bl_file: BottleLogFile | None :
            An instance of BottleLogFile with the target .bl file
        bottle_capacity: int :
            The number of water bottles attached to the rosette. Used in
            global bottle ID calculcation.
        """
        if not bl_file:
            if not file_path:
                try:
                    file_path = Path(self._ds.attrs["path_to_source_file"])
                except KeyError:
                    logger.error("No input file path")
                    return

            if Path(file_path).is_dir():
                file_path = (
                    Path(file_path)
                    / Path(self._ds.attrs["path_to_source_file"]).stem
                )
            try:
                bl_file = BottleLogFile(Path(file_path).with_suffix(".bl"))
            except Exception as error:
                logger.error(
                    f"Could not open {file_path} as .bl file: {error}"
                )
                return
        assert isinstance(bl_file, BottleLogFile)
        bl_info_array = np.zeros(self._ds.access.size)
        df = bl_file.df.copy()
        if "Cast" in self._ds.meta.custom.keys():
            df["Bottle ID"] = df["Bottle ID"].apply(
                self._calculate_global_bottle_id,
                args=(bottle_capacity,),
            )
            long_name = "bottle firing indicator (global Bottle ID)"
        else:
            long_name = "bottle firing indicator"

        for _, line in df.iterrows():
            mask = (self._ds.scan >= int(line.start_range)) & (
                self._ds.scan < int(line.end_range)
            )

            bl_info_array[mask] = line["Bottle ID"]

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
        """
        Returns the global bottle ID.

        Used at IOW to have reliable identifiers for all water bottles
        throughout a cruise. The calculcation is as follows:
            Bottle Capacity * Cast Number + Bottle Number
        """
        cast_number = int(self._ds.meta.custom["Cast"])
        return bottle_capacity * (cast_number) + int(bottle_number)

    def processing_metadata(
        self,
        module: str,
        key: str = "",
        value: str = "",
    ):
        """
        Adds provenance metadata to the dataset.

        Each data editing information will find its way in here. Its inspired
        by Sea-Birds line-by-line processing module information metadata
        storage. Each module will be stored with one line of general
        information, followed by the individual modules run parameters.

        Parameters
        ----------
        module: str :
            The name of the processing module
        key: str :
            The name of the parameter
        value: str :
            The value corresponding to the parameter
        """
        last_module = self._ds.proc.last
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
                f"{module}_metainfo = {timestamp}, ctdam python package{version}{os.linesep}"
            )

        if key and value:
            self._ds.attrs["provenance_metadata"] += (
                f"{module}_{key} = {value}\n"
            )

    def teos10_vars(self, ds=None):
        """
        Compute common derived TEOS-10 variables from CTD base variables.

        Parameters
        ----------
        ds :
            The dataset to edit. Defaults to self._ds
        """
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
                shape = (self._ds.access.size,)
                position = ds.attrs["position"]
                self.parameter("latitude", np.full(shape, position[0]))
                self.parameter("longitude", np.full(shape, position[1]))
            else:
                logger.error(
                    "Missing position information for absolute salinity calculcation."
                )
                return

        standard_names = [
            ds[c].attrs["standard_name"]
            for c in ds.data_vars
            if "standard_name" in ds[c].attrs.keys()
        ]

        if not "sea_water_absolute_salinity" in standard_names:
            ds["absolute_salinity"] = self._ds.gsw.SA_from_SP()
        if not "sea_water_conservative_temperature" in standard_names:
            ds["conservative_temperature"] = self._ds.gsw.CT_from_t()
        if not "sea_water_sigma_t" in standard_names:
            ds["density"] = self._ds.gsw.sigma0()


@xr.register_dataset_accessor("meta")
class MetadataAccessor:
    """Access CTD-specific metadata."""

    def __init__(self, ds):
        self._ds = ds

    @property
    def provenance(self) -> dict:
        """Returns provenance metadata as dictionary."""
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

    @property
    def custom(self) -> dict:
        """Returns custom metadata as dictionary."""
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
    """Retrieve data information."""

    def __init__(self, ds):
        self._ds = ds

    @property
    def btl_info(self) -> xr.Dataset:
        """Returns a new dataset equicalent to Sea-Birds .btl file."""
        ds = self._ds.set_coords("bottle_info")
        ds = ds.reset_coords("time")
        ds = ds.groupby("bottle_info").mean()
        ds = ds.drop_sel(bottle_info=0)
        return ds

    @property
    def path(self) -> Path:
        try:
            file_path = Path(self._ds.attrs["path_to_source_file"])
        except KeyError:
            file_path = Path("")
        return file_path

    def spans(
        self, name: str | xr.DataArray, bad_flag: float = -9.990e-29
    ) -> Tuple:
        """
        Returns the data limits of the given parameter.

        Parameters
        ----------
        name: str | xr.DataArray :
            The parameter

        bad_flag: float :
            The bad flag value to ignore

        Returns
        -------
        A Tuple holding the two limits
        """
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

    @property
    def size(self) -> int:
        """Returns the number of data rows inside this dataset."""
        dims = [k for k in self._ds.sizes.keys() if k != "sensor"]
        if len(dims) > 0:
            return self._ds.sizes[dims[0]]
        else:
            raise ValueError("Missing dimensions in dataset")

    @property
    def sample_rate(self) -> int:
        """Returns the sample rate of the current dataset."""
        if "sample_rate" in self._ds.attrs and self._ds.attrs["sample_rate"]:
            sample_rate = self._ds.attrs["sample_rate"]
            try:
                sample_rate = int(sample_rate)
            except Exception:
                sample_rate = int(sample_rate.split()[0])
            return sample_rate

        try:
            return int(np.round(1 / np.mean(np.diff(self._ds.time.data))))
        except Exception:
            return 24

    @property
    def bin_unit(self) -> str:
        """Returns the unit this dataset is binned in."""
        if "sample_rate" in self._ds.attrs and self._ds.attrs["sample_rate"]:
            sample_rate = self._ds.attrs["sample_rate"]
            try:
                sample_rate = int(sample_rate)
            except Exception:
                return sample_rate.split()[1]

        return ""

    @property
    def binned(self) -> bool:
        """Returns whether this dataset is binned or not."""
        return bool(self._ds.access.bin_unit)

    def sensor_strand(self, strand="primary") -> xr.Dataset:
        """
        Selects one of two sensor strands.

        The data of the other strand will be dropped.

        Parameters
        ----------
        strand :
            The name of the strand, 'primary' or 'secondary'

        Returns
        -------
        A new dataset with only the selected strand
        """
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
        """
        Turn (scan, sensor) variables into separate (scan,) variables.

        Parameters
        ----------
        ds :
            The target dataset, default is self._ds
        suffix_map :
            Internal name to sensor number mapping

        Returns
        -------
        A new dataset that holds only variables with 1D arrays
        """
        ds = ds if ds else self._ds
        # check, whether already flattened
        if not "sensor" in ds.coords:
            return ds
        flat_vars = {}
        for name, da in ds.data_vars.items():
            if (
                not name in PARAMETER_MAPPING.keys()
                and not name == "bottle_info"
            ):
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
            attrs=self._ds.attrs,
        )
        return ds_flat

    def numpy_array(self, ds=None) -> np.ndarray:
        """
        Returns a numpy representation of this dataset.

        Parameters
        ----------
        ds :
            The target dataset, default self._ds
        """
        ds = ds if ds else self._ds
        ds_flat = self.flattened_ds(ds)
        return np.column_stack([ds_flat[var].values for var in ds_flat])

    @property
    def pandas_dataframe(self) -> pd.DataFrame:
        """Returns a pandas DataFrame representation of this dataset."""
        ds_flat = self.flattened_ds()
        return ds_flat.to_dataframe()


@xr.register_dataset_accessor("export")
class ExportAccessor:
    """Write the dataset to disk in various formats."""

    def __init__(self, ds):
        self._ds = ds

    def to_cnv(
        self,
        file_path: Path | str = "",
        reduced_header: bool = False,
        bad_flag=-9.990e-29,
    ):
        """
        Write to Sea-Bird-compliant .cnv format.

        Parameters
        ----------
        file_path: Path | str :
            The path to the new file.
        reduced_header: bool :
            Whether to use a reduced metadata header.
        bad_flag :
            The value to consider as bad flag.
        """
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
        parameters : Parameters | None
            A specific parameters instance or self.parameters
        reduced_header : bool
            Whether to build a streamlined non-cnv header (Default value = False)
        ds: xr.Dataset :

        reduced_header: bool :
             (Default value = False)
        bad_flag :
             (Default value = -9.990e-29)

        Returns
        -------
        A list with the individual metadata header lines.
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
        ds :
            The dataset to target
        output_spans: bool :
            Whether to recreate data spans (Default value = True)
        bad_flag :
            The values to consider as bad flag

        Returns
        -------
        A list representing the data table information
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
        ds: xr.DataArray :
            The dataset to target

        Returns
        -------
        A list representing data table statistics
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
            f"# interval = {ds.access.bin_unit}: {1 / ds.access.sample_rate:1.7f}{os.linesep}",
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
        ds: xr.Dataset :
            The dataset to target
        bad_flag :
            The value to use to indicate bad values (Default value = -9.990e-29)

        Returns
        -------
        A list representing the data table inside a .cnv file
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

    def _set_output_format(self, name) -> str:
        """
        Sets a parameter-specific number format.

        Parameters
        ----------
        name :
            The name of the parameter

        Returns
        -------
        The string format
        """
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

    def to_btl(
        self,
        output_path: Path | str = "",
        bl_path: Path | str = "",
        output_statistics: Literal["avg", "all"] = "all",
        bottle_capacity: int = 25,
    ):
        """
        Creates a custom bottle file or seabird bottle file, given a .cnv and .bl file.
        SeaBirdBtlFile is the default output. To get the OwnBtlFile instead use "arguments={"output_format": "own",}"

        OwnBtlFile:
        The resulting file strongly adheres to the format of a regular .btl file.
        Specifically, the header is the same, only the data table features a
        different format. Its a 11-character wide tsv, as a cnv data table. In
        contrast to a .btl, only average values are used.

        In general, this custom bottle file (.obtl) can be generated at any time
        during the CTD processing. This improves over the standard Sea-Bird variant
        that allows this only during .cnv creation using Datcnv. With the .obtl
        file one can ensure the very same data quality from a .cnv file inside a
        bottle file.

        SeaBirdBtlFile:
        Default Case that returns a .btl using a .cnv and a .bl file

        Parameters
        ----------
        output_path: Path | str :
            The path to store the .btl file to
        bl_path: Path | str :
            The source path of the .bl file
        output_statistics: Literal["avg", "all"] :
            The type of output to produce
        bottle_capacity: int :
            The number of bottles attached at the rosette
        """
        file_path = Path(self._ds.attrs["path_to_source_file"])
        self.bl_path = bl_path
        self.output_statistics = output_statistics
        self.bottle_capacity = bottle_capacity
        if not "bottle_info" in self._ds.data_vars:
            self._ds.add.bottles(bl_path)
            # if bl file not found, stop here
            if not "bottle_info" in self._ds.data_vars:
                return

        if self._ds.access.binned:
            raise BinnedDataError(
                file_name=str(file_path),
                step_name="bottlefile",
            )

        ds = self._ds.copy(deep=True)
        ds.add.processing_metadata("bottlefile")
        cnv_header = self._create_cnv_header(ds)

        btl_file = "".join(
            [
                line
                for line in cnv_header
                if not line.startswith(
                    ("# name", "# span", "# nquan", "# nvalues", "# units")
                )
            ]
        )

        btl_file += self._create_table_header(ds)

        output_path = (
            (Path(output_path) / file_path.stem).with_suffix(".btl")
            if output_path
            else file_path.with_suffix(".btl")
        )

        with open(output_path, "w") as file:
            file.write(btl_file.rstrip("\n"))

        return btl_file.rstrip("\n")

    def _add_whitespace(self, data, space: int = 11):
        """Returns a btl-file compliant data cell."""
        return (space - len(str(data))) * " " + str(data)

    def _create_table_header(self, ds) -> str:
        """
        Builds the .btl file string.

        Parameters
        ----------
        ds :
            The dataset to target

        Returns
        -------
        A string representing the output .btl file
        """
        if self.output_statistics == "all":
            ds = ds.access.flattened_ds()
            line_1 = ""
            line_2 = ""

            line_1 += self._add_whitespace("Btl_Posn")
            line_2 += self._add_whitespace("Btl_ID")

            line_1 += self._add_whitespace("Date")
            line_2 += self._add_whitespace("Time")
        else:
            ds = self._ds.access.btl_info
            ds = ds.access.flattened_ds()
            line_1 = ""
            line_1 += self._add_whitespace("Btl_ID")
            line_1 += self._add_whitespace("Time")

        for variable_name, _ in ds.data_vars.items():
            if variable_name in ["time", "bottle_info"]:
                continue
            try:
                sbs_name = PARAMETER_MAPPING[variable_name]["seabird"][
                    "shortname"
                ]
            except KeyError:
                try:
                    if variable_name.endswith("2"):
                        sbs_name = PARAMETER_MAPPING[variable_name[:-1]][
                            "seabird"
                        ]["secondary"]["shortname"]
                    else:
                        sbs_name = PARAMETER_MAPPING[variable_name]["seabird"][
                            "primary"
                        ]["shortname"]
                except KeyError:
                    ds = ds.drop_vars(variable_name)
                    continue
            if sbs_name in self._get_required_parameters():
                line_1 += self._add_whitespace(sbs_name.capitalize())
            else:
                ds = ds.drop_vars(variable_name)

        if self.output_statistics == "all":
            line_2 += " " * (len(line_1) - len(line_2))

            return line_1 + "\n" + line_2 + "\n" + self._original_table(ds)
        else:
            return line_1 + "\n" + self._short_table(ds)

    def _original_table(self, ds: xr.Dataset) -> str:
        """Creates the standard .btl file with 4 rows per bottle."""
        out = ""
        for bottle_id in list(ds.bottle_info.attrs["flag_values"]):
            if bottle_id == 0:
                continue
            data = ds.where(ds.bottle_info == bottle_id, drop=True)
            data = data.drop_vars("bottle_info")
            values = data.to_array().T
            timestamp = datetime.fromtimestamp(float(np.mean(data.time)))

            statistics = {
                "avg": np.nanmean(values, axis=0),
                "sdev": np.nanstd(values, axis=0),
                "min": np.nanmin(values, axis=0),
                "max": np.nanmax(values, axis=0),
            }

            rows = ""

            for i, statistic_name in enumerate(["avg", "sdev", "min", "max"]):
                line = ""

                if i == 0:
                    line += self._add_whitespace(
                        bottle_id % self.bottle_capacity
                    )
                    line += self._add_whitespace(
                        timestamp.strftime("%b %d %Y"), 12
                    )
                elif i == 1:
                    line += self._add_whitespace(bottle_id)
                    line += self._add_whitespace(
                        timestamp.strftime("%H:%M:%S"), 12
                    )
                else:
                    line += self._add_whitespace("")
                    line += self._add_whitespace("", 12)

                for value in statistics[statistic_name]:
                    line += self._add_whitespace(self._format_btl_value(value))

                line += self._add_whitespace(f"({statistic_name})")
                rows += line + "\n"

            out += rows
        return out

    def _format_btl_value(self, value: float) -> str:
        """Returns formatted data values."""
        if np.isnan(value):
            return "nan"

        if abs(value) != 0 and (abs(value) < 0.001 or abs(value) >= 10000):
            return f"{value:.3e}"

        return f"{value:.4f}"

    def _short_table(self, ds: xr.Dataset) -> str:
        """Creates a small .btl file with only one row per bottle."""
        btl_id = ds.bottle_info.data
        time_data = pd.to_datetime(ds["time"], unit="s")
        ds = ds.drop_vars("time")
        data_rows = self._array2cnv(ds)

        assert len(btl_id) == len(data_rows)

        rows = ""

        for id, data, timestamp in zip(btl_id, data_rows, time_data):
            line = ""

            line += self._add_whitespace(int(id))
            line += self._add_whitespace(
                timestamp.replace(microsecond=0).time()
            )
            line += self._add_whitespace(data.rstrip())

            line += self._add_whitespace("(avg)")
            rows += line + "\n"

        return rows

    def _get_required_parameters(self) -> list[str]:
        """The parameters to write to disk."""
        return [
            "prDM",
            "t090C",
            "t190C",
            "c0mS/cm",
            "c1mS/cm",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "flECO-AFL",
            "turbWETntu0",
            "par",
            "spar",
            "sal00",
            "sal11",
        ]

    def _get_global_bottle_id(self, bottle_number: int) -> int:
        """Returns the global bottle ID."""
        try:
            cast_number = int(self._ds.meta.custom["Cast"])
        except KeyError:
            return bottle_number
        return self.bottle_capacity * (cast_number) + bottle_number


@xr.register_dataset_accessor("qc")
class QCAccessor:
    """Assess the quality of the data."""

    def __init__(self, ds):
        self._ds = ds

    def _flag_var(self, var):
        """Returns the flag column corresponding to the given variable."""
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
        """Selects certain flagged values."""
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
    """Visualize data."""

    def __init__(self, ds):
        self._ds = ds

    def profile(self, var, sensor="primary", qc_mask=False, ax=None, **kwargs):
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

    def bokeh(self, print_plot: bool = False, **kwargs):
        """Plot all variables vs pressure inside internet browser."""
        basic_bokeh_plot(ctd_data=self._ds, print_plot=print_plot, **kwargs)
