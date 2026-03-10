import importlib.metadata
import logging
import tomllib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Tuple

import gsw
import numpy as np
import xmltodict
from numpy.testing import assert_equal

from ctdam.parser import CnvFile, CnvProcessingSteps, HexFile, Parameters
from ctdam.utils import (
    extract_sensor_name,
    parse_xmlcon_sensor_data,
)

logger = logging.getLogger(__name__)


class CTDData:
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

    def get_cast_borders_dict(self) -> dict:
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
        self, parameters: Parameters | None = None, bad_flag=-9.990e-29
    ) -> list:
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
            result.append(formatted_row + "\r\n")
        return result

    def parse_output_sensor_info(self) -> list:
        if isinstance(self.metadata_source, HexFile):
            out_list = [
                f"# {data}\r\n"
                for data in xmltodict.unparse(
                    {"Sensors": self.raw_sensor},
                    pretty=True,
                    indent=2,
                ).split("\n")
            ][1:]
        elif isinstance(self.metadata_source, CnvFile):
            out_list = [f"# {data.rstrip()}\r\n" for data in self.sensor_data]
        else:
            out_list = []
        return out_list

    def get_processing_info(self) -> list:
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
        """Re-creates the cnv header."""
        parameters = parameters if parameters else self.parameters
        sb9_info = (
            [f"* {data.strip()}\r\n" for data in self.sbe9_data[:-1]]
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
                f"** {key} = {value}\r\n" if value else f"** {key}\r\n"
                for key, value in self.metadata.items()
            ],
            f"* {system_utc.strip()}\r\n",
            *[f"# {data}" for data in data_table_description],
            *self.extra_data_table_desc(data_table_description, system_utc),
            *sensor_data,
            *[f"# {data}" for data in processing_info],
            "*END*\r\n",
        ]
        return header

    def extra_data_table_desc(
        self,
        data_table_description: list,
        system_utc: str,
    ) -> list:
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
                f"# interval = {self.bin_unit}: {1 / self.sample_rate:1.7f}\r\n",
                f"# start_time = {start_time_string}\r\n",
                "# bad_flag = -0.0000\r\n",
            ]

        return out_list

    def drop_flagged_rows(self, parameters: Parameters | None = None):
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
    ) -> Tuple[Parameters, list]:
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
        parameters.sort_parameters()
        # create output format
        data = self.array2cnv(parameters, bad_flag)
        header = self.create_header(parameters, reduced_header)
        file_data = [*header, *data]
        # writing content out
        try:
            with open(
                file_path.with_suffix(".cnv"), "w", encoding="latin-1"
            ) as file:
                for line in file_data:
                    try:
                        file.write(line)
                    except TypeError:
                        logger.error(line)

        except IOError as error:
            logger.error(f"Could not write cnv file: {error}")

        return parameters, file_data
