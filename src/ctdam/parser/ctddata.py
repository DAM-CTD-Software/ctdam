import importlib.metadata
import logging
import os
import tomllib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import gsw
import netCDF4 as nc
import numpy as np
import xmltodict
from numpy.testing import assert_equal

from ctdam.parser import CnvFile, CnvProcessingSteps, HexFile, Parameters
from ctdam.utils import (
    extract_sensor_name,
    parse_xmlcon_sensor_data,
    sbe_to_decimal,
)

logger = logging.getLogger(__name__)


class CTDData:
    """
    Class to store data and metadata representing one single CTD cast in.

    Is meant to work as single exchange format for CTD data. At the moment,
    Sea-Birds .hex and .cnv file can be parsed in this format, but other
    CTD data formats are meant to follow.
    From this class, several output options are possible, at the moment,
    the .cnv format is the only one available.


    Parameters
    ----------
    parameters: Parameters
        A parameters instance holding all data values
    metadata_source: HexFile | CnvFile
        Source file information
    processing_steps: CnvProcessingSteps
        The processing history of the file upon creation (Default: empty)

    Attributes
    ----------
    parameters: Parameters
        All data inside individual Parameter instances. All attributes and
        methods can be accessed directly.
    metadata_source: HexFile | CnvFile
        The complete parent file the data is parsed from. All attributes and
        methods can be accessed directly.
    raw_sensor: dict
        Sensor metadata parsed into accessible key-value pairs
    sensor_info: list
        Tidied sensor metadata
    processing_steps: CnvProcessingSteps
        Structure to hold Processing metadata
    conductivity_on_creation: np.array
        The original conductivity
    cast_borders: dict
        Structured cast start and end points
    output_cnv_data: list
        The full file written as ascii .cnv file
    output_parameters: Parameters
        The parameters exported to a ascii .cnv file
    """

    def __init__(
        self,
        parameters: Parameters,
        metadata_source: HexFile | CnvFile,
        processing_steps: CnvProcessingSteps = CnvProcessingSteps([]),
    ) -> None:
        self.parameters = parameters
        self.metadata_source = metadata_source
        if isinstance(metadata_source, HexFile):
            self.raw_sensor = parse_xmlcon_sensor_data(
                metadata_source.xmlcon.data
            )
            self.sensor_info = extract_sensor_name(self.raw_sensor["sensor"])
            self.processing_steps = processing_steps
        else:
            self.sensor_info = metadata_source.sensors
            self.processing_steps = metadata_source.processing_steps
        try:
            self.conductivity_on_creation = self["c0mS/cm"].data
        except KeyError:
            self.conductivity_on_creation = np.ndarray([])
        self.cast_borders = self.get_cast_borders_dict()

    def __getattr__(self, name: str, /):
        parameters = self.__dict__.get("parameters")
        metadata_source = self.__dict__.get("metadata_source")

        if parameters is not None and hasattr(parameters, name):
            return getattr(parameters, name)
        if metadata_source is not None and hasattr(metadata_source, name):
            return getattr(metadata_source, name)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.parameters.values())[key]
        else:
            return self.parameters[key]

    def __dir__(self):
        return sorted(
            set(super().__dir__())
            | set(dir(self.parameters))
            | set(dir(self.metadata_source))
        )

    def __eq__(self, other: object, /) -> bool:
        if hasattr(other, "parameters"):
            return self.parameters == other.parameters
        else:
            return False

    def __lt__(self, other: object) -> bool:
        return Path.__lt__(self.path_to_file, other.path_to_file)

    def __gt__(self, other: object) -> bool:
        return Path.__gt__(self.path_to_file, other.path_to_file)

    def __repr__(self) -> str:
        return str(self.path_to_file)

    def __len__(self) -> int:
        return len(self.parameters)

    def __iter__(self):
        return self.parameters.values().__iter__()

    def __contains__(self, key: object) -> bool:
        return self.parameters.__contains__(key)

    def __fspath__(self):
        return self.__str__()

    def process(
        self,
        proc_settings: dict | list = {
            "remove_flags": False,
            "output_type": "internal",
            "modules": {
                "wildedit_geomar": {},
                "wfilter": {},
                "alignctd": {},
                "celltm": {},
                "binavg": {},
            },
        },
    ):
        """
        Applies a processing workflow to this CTD data.

        Parameters
        ----------
        proc_settings: dict
            A processing workflow that can be parsed by ctdam.proc.Procedure

        """
        from ctdam.proc import Procedure

        # allow for easy module selection via a simple list
        if isinstance(proc_settings, list):
            modules = {k: {} for k in proc_settings}
            proc_settings = {
                "remove_flags": False,
                "output_type": "internal",
                "modules": modules,
            }

        self = Procedure(proc_settings).run(self)

    def plot(
        self,
        *args,
        **kwargs,
    ):
        """
        Plots this CTD Data.

        Parameters
        ----------
        Will be passed to 'ctdam.vis.visualize.basic_bokeh_plot'

        print_plot: bool
            Whether to save the plot to disk (Default value = False)
        output_name: str
            The name of the output file (Default value = "")
        output_directory: Path | str
            The directory to store the output file in (Default value = "")
        metadata: bool
            Whether to save metadata in the file (Default value = True)
        show_plot: bool
            Whether to open the plot in a browser (Default value = True)
        y_axis_params: list[str] :
            Possible parameters for the y axis
        config_path: Path | str
            The path to the config file (Default value = "vis_config.toml")
        """
        from ctdam.vis import basic_bokeh_plot

        basic_bokeh_plot(self, *args, **kwargs)

    def get_cast_borders_dict(self) -> dict:
        """
        Parses the cast border information into a manageable format.

        Returns
        -------
        A dictionary holding the info
        """
        try:
            metadata = self.processing_steps[0].metadata["cast_borders"]
        except Exception:
            cast_borders = {}
        else:
            if isinstance(metadata, dict):
                cast_borders = metadata
            elif isinstance(metadata, str):
                try:
                    cast_borders = {
                        e.split(":")[0].strip(): int(e.split(":")[1].strip())
                        for e in metadata.split(",")
                    }
                except Exception as error:
                    logger.error(
                        f"Could not extract cast_border info in {self.file_name}: {error}"
                    )
                    cast_borders = {}
            else:
                cast_borders = {}
        return cast_borders

    def update_salinity(self):
        """
        Re-calculate the salinity values.

        During processing, the conductivity, pressure and temperature values
        may change. In order to use this upgraded information in depending
        parameters, they need to be re-calculated.
        """
        if "prDM" not in self.parameters:
            return
        for conductivity in [
            p for p in self.get_parameter_list() if p.param == "Conductivity"
        ]:
            second_sensor = conductivity.sensor_number == 2
            if "Temperature" in [p.param for p in self.values()]:
                if second_sensor:
                    t_values = self["t190C"].data
                else:
                    t_values = self["t090C"].data
            else:
                return
            p_values = self["prDM"].data

            salinity = gsw.SP_from_C(
                C=conductivity.data.astype(float),
                t=t_values,
                p=p_values,
            )

            salinity_name = "sal11" if second_sensor else "sal00"
            try:
                self[salinity_name].data = salinity
            except KeyError:
                sensor_mapping_file = Path(__file__).parent.joinpath(
                    "sensor_mapping.toml"
                )
                if not sensor_mapping_file.exists():
                    logger.error(
                        f"No sensor mapping file found. Looked in {sensor_mapping_file}. Could not recalculate salinity."
                    )
                    return
                with open(sensor_mapping_file, "rb") as file:
                    mapper = tomllib.load(file)
                salinity_long_name = (
                    "Salinity" + " 2" if second_sensor else "Salinity"
                )
                self.create_parameter(
                    salinity, mapper["metadata"][salinity_long_name]
                )

    def array2cnv(
        self,
        parameters: Parameters | None = None,
        bad_flag=-9.990e-29,
    ) -> list:
        """
        Parse the numpy array data into .cnv data format.


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
        parameters = parameters if parameters else self.parameters
        result = []
        for param in parameters.values():
            np.nan_to_num(param.data, copy=False, nan=bad_flag)
        output_formats = [p.output_format for p in parameters.values()]
        for row in parameters.get_full_data_array():
            formatted_row = [
                output_format.format(elem)[:10].rjust(11)
                for elem, output_format in zip(row, output_formats)
            ]
            formatted_row = "".join(formatted_row)
            result.append(formatted_row + os.linesep)
        return result

    def parse_output_sensor_info(self) -> list:
        """
        Recreate the sensor information of a .cnv file.

        Returns
        -------
        A list that represents the .cnv sensor metadata format.
        """
        if isinstance(self.metadata_source, HexFile):
            out_list = [
                f"# {data}{os.linesep}"
                for data in xmltodict.unparse(
                    {"Sensors": self.raw_sensor},
                    pretty=True,
                    indent=2,
                ).split("\n")
            ][1:]
        elif isinstance(self.metadata_source, CnvFile):
            out_list = [
                f"# {data.rstrip()}{os.linesep}" for data in self.sensor_data
            ]
        else:
            out_list = []
        return out_list

    def get_processing_info(self) -> list:
        """
        Return processing information.

        Does add hex2py metadata if no conversion information present.

        Returns
        -------
        A list with the processing info.
        """
        if len(self.processing_steps) == 0:
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y.%m.%d %H:%M:%S"
            )
            try:
                version = f", v{importlib.metadata.version('ctdam.parser')}"
            except Exception:
                version = ""
            self.processing_steps.add_info(
                module="hex2py",
                key="metainfo",
                value=f"{timestamp}, ctdam.parser python package{version}",
            )

        return self.processing_steps._form_processing_info()

    def create_header(
        self,
        parameters: Parameters | None = None,
        reduced_header: bool = False,
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
        parameters = parameters if parameters else self.parameters
        sb9_info = (
            [f"* {data.strip()}{os.linesep}" for data in self.sbe9_data[:-1]]
            if not reduced_header
            else []
        )
        data_table_description = parameters._form_data_table_info(
            output_spans=not reduced_header
        )
        system_utc = self.sbe9_data[-1]
        sensor_data = (
            self.parse_output_sensor_info() if not reduced_header else []
        )
        processing_info = self.get_processing_info()
        header = [
            *sb9_info,
            *[
                f"** {key} = {value}{os.linesep}"
                if value
                else f"** {key}{os.linesep}"
                for key, value in self.metadata.items()
            ],
            f"* {system_utc.strip()}{os.linesep}",
            *[f"# {data}" for data in data_table_description],
            *self.extra_data_table_desc(data_table_description, system_utc),
            *sensor_data,
            *[f"# {data}" for data in processing_info],
            f"*END*{os.linesep}",
        ]
        return header

    def extra_data_table_desc(
        self,
        data_table_description: list,
        system_utc: str,
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
        if not [
            line
            for line in data_table_description
            if line.startswith("interval")
        ]:
            nmea_time = [
                line for line in self.sbe9_data if line.startswith("NMEA UTC")
            ]
            if system_utc.startswith("System"):
                start_time_string = f"{system_utc.split('=')[1].strip()} [System UTC, first data scan.]"
            elif nmea_time:
                start_time_string = f"{nmea_time[0].split('=')[1].strip()} [NMEA time, first data scan.]"
            else:
                start_time_string = "unknown"

            out_list = [
                f"# interval = {self.bin_unit}: {1 / self.sample_rate:1.7f}{os.linesep}",
                f"# start_time = {start_time_string}{os.linesep}",
                f"# bad_flag = -0.0000{os.linesep}",
            ]

        return out_list

    def drop_flagged_rows(self, parameters: Parameters | None = None):
        """
        Remove data rows that are flagged bad and the flag column.


        Parameters
        ----------
        parameters: Parameters | None
            A specific parameters instance or self.parameters
        """
        parameters = parameters if parameters else self.parameters
        if parameters.binned:
            return
        if "flag" not in parameters:
            return
        flags = parameters.data.pop("flag").data.astype(bool)
        for param in parameters.get_parameter_list():
            param.data = param.data[~flags]

    def pick_output_columns(
        self,
        parameters: Parameters,
        mode: list[str] | Literal["all", "default"] = "all",
    ):
        """
        Define the parameter columns to output.

        Parameters
        ----------
        parameters: Parameters
            A specific parameters instance or self.parameters
        mode: list[str] | Literal["all", "default"]
            List of output parameters, or descriptors 'all' or 'default' (Default value = "all")
        """
        parameters = parameters if parameters else self.parameters
        default_columns = [
            "Pressure",
            "Temperature",
            "Salinity",
            "Oxygen",
            "Fluorescence",
            "Turbidity",
            "PAR",
            "SPAR",
            "Latitude",
            "Longitude",
            "Time",
        ]
        if mode == "all":
            return
        elif mode == "default":
            columns = default_columns
        elif isinstance(mode, list):
            columns = mode
        else:
            logger.error(
                f"Unknown output option: {mode}. Returning all columns."
            )
            return
        params_to_drop = [
            k
            for k, v in parameters.items()
            if v.param.lower() not in [c.lower() for c in columns]
        ]
        for param in params_to_drop:
            try:
                parameters.pop(param)
            except KeyError:
                continue

    def to_cnv(
        self,
        file_path: Path | str = "",
        remove_flags: bool = True,
        output_parameters: list[str] | Literal["all", "default"] = "all",
        reduced_header: bool = False,
        bad_flag: float = -9.990e-29,
        seabird_compatible: bool = True,
    ):
        """
        Writes the data and metadata inside of this instance as new .cnv
        file to disk.

        Parameters
        ----------
        file_path: Path | str
             Path to the new .cnv file, will default to the input file name
        remove_flags: bool
             Whether to remove flagged rows (Default value = True)
        output_parameters: list[str] | Literal["all","default"] :
             Which parameter columns to output (Default value = "all")
        reduced_header: bool
             Whether to output a reduced head (Default value = False)
        bad_flag: float
             The value to use as bad value indicator (Default value = -9.990e-29)

        Returns
        -------

        """
        file_path = Path(file_path) if file_path else self.path_to_file
        # prepare data
        ## use a separate parameters object to specify specific output
        parameters = deepcopy(self.parameters)
        if self.conductivity_on_creation.size != 1:
            try:
                assert_equal(
                    self.conductivity_on_creation,
                    self.parameters["c0mS/cm"].data,
                )
            except AssertionError:
                self.update_salinity()
        if remove_flags:
            self.drop_flagged_rows(parameters)
        self.pick_output_columns(parameters, output_parameters)
        if seabird_compatible:
            parameters.remove_parameter("timeU")
        parameters.sort_parameters()
        # create output format
        data = self.array2cnv(parameters, bad_flag)
        header = self.create_header(parameters, reduced_header)
        self.output_cnv_data = [*header, *data]
        # writing content out
        try:
            with open(
                file_path.with_suffix(".cnv"), "w", encoding="latin-1"
            ) as file:
                for line in self.output_cnv_data:
                    try:
                        file.write(line)
                    except TypeError:
                        logger.error(line)

        except IOError as error:
            logger.error(f"Could not write cnv file: {error}")
        self.output_parameters = parameters

    def to_netCDF(
        self,
        file_path: Path | str = "",
        toml_path: Path | str | None = None,
        nc_path: Path | str | None = None,
    ):
        "creates a netCDF file out of a hex or cnv file."
        file_path = Path(file_path) if file_path else self.path_to_file

        if toml_path is None:
            toml_file = Path(__file__).parent.parent.joinpath(
                "conv", "sensor_mapping.toml"
            )
        else:
            toml_file = Path(toml_path)
        if not toml_file.is_file:
            raise FileNotFoundError(f"toml file not found: {toml_file}")

        try:
            with open(toml_file, "rb") as f:
                mapping = tomllib.load(f)
        except Exception as e:
            raise ValueError(
                f"Error while parsing toml file '{toml_file}': {e}"
            )

        if nc_path is None:
            nc_path = self.path_to_file.with_suffix(".nc")
        else:
            nc_path = Path(nc_path)

        with nc.Dataset(nc_path, "w", format="NETCDF4") as ds:
            n_obs = self.get_data_length()
            ds.createDimension("obs", n_obs)

            coordinates = []
            for var in ["timeS", "timeU", "longitude", "latitude"]:
                header_info = [
                    l
                    for l in self.metadata_source.sbe9_data
                    if var in l.lower()
                ]
                if var in self.parameters:
                    pass
                elif header_info:
                    var_value = sbe_to_decimal(
                        header_info[0].split("=")[1].strip()
                    )
                    self.parameters.create_parameter(var_value, name=var)
                else:
                    continue
                new_var = ds.createVariable(var, "f4", ("obs",))
                new_var.long_name = (
                    self.parameters[var].metadata["name"].lower()
                )
                new_var.units = self.parameters[var].unit
                new_var.metainfo = self.parameters[var].metadata["longinfo"]
                new_var[:] = self.parameters[var].data
                coordinates.append(var)

            if "prDM" in self.parameters and new_var.long_name == "latitude":
                depth = ds.createVariable("depth", "f4", ("obs",))
                depth.units = "m"
                depth.long_name = "Depth"
                depth.positive = "down"
                depth[:] = -gsw.z_from_p(
                    self["prDM"].data, self.parameters[var].data
                )

            for sensor_key, attributes in mapping.get("metadata", {}).items():
                raw_name = attributes.get("shortname")

                if not raw_name:
                    logger.warning(
                        f"warning: 'shortname' not found for sensor '{sensor_key}' in TOML. skipped."
                    )
                    continue

                base_name = raw_name.replace("/", "_").replace(" ", "_")
                var_name = base_name
                counter = 1

                while var_name in ds.variables:
                    var_name = f"{base_name}_{counter}"
                    counter += 1

                var = ds.createVariable(var_name, "f4", ("obs",))
                var.long_name = attributes["longinfo"]
                var.units = attributes["unit"]
                var.metainfo = attributes["metainfo"]
                var.original_sensor_key = sensor_key
                var.coordinates = " ".join(coordinates)

                if raw_name in self:
                    ds.variables[var_name][:] = self[raw_name].data
