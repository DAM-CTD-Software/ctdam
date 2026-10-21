import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from ctdam.conv.unit_conversion import oxygen_umolperkg_to_umolperl
from ctdam.entry.casts import Casts
from ctdam.entry.report.mapper import dship_event_mapper
from ctdam.entry.report.texts import ProcessingReport

logger = logging.getLogger(__name__)

column_mapper = {
    "depth": "Depth water [m] (CTD, {})",
    "pressure": "Pressure [dbar] (CTD, {})",
    "temperature": "Temperature [°C] (Sensor 1, CTD, {})",
    "temperature2": "Temperature [°C] (Sensor 2, CTD, {})",
    "salinity": "Salinity (Sensor 1, PSU, Calculated)",
    "salinity2": "Salinity (Sensor 2, PSU, Calculated)",
    "conductivity": "Conductivity [mS/cm] (Sensor 1, CTD, {})",
    "conductivity2": "Conductivity [mS/cm] (Sensor 2, CTD, {})",
    "ox_umol_l": "Oxygen [µmol/l] (Sensor 1, CTD, {})",
    "ox_umol_l2": "Oxygen [µmol/l] (Sensor 2, CTD, {})",
    "ox_ml_l": "Oxygen [ml/l] (Sensor 1, CTD, {})",
    "ox_ml_l2": "Oxygen [ml/l] (Sensor 2, CTD, {})",
    "oxygen": "Oxygen [µmol/kg] (Sensor 1, CTD, {})",
    "oxygen2": "Oxygen [µmol/kg] (Sensor 2, CTD, {})",
    "svCM": "Sound velocity in water [m/s] (Chen-Millero, Calculated)",
    "fluorescence": "Chlorophyll A [mg/m**3] (CTD, {})",
    "turbidity": "Turbidity (Nephelometric turbidity unit) [NTU] (CTD, {})",
    "spar": "SPAR (CTD, {})",
    "par_biosphericallicorchelsea": "Radiation, photosynthetically active (CTD, {})",
    "density": "Density, sigma-theta [kg/m**3]",
    "altimeter": "Height above sea floor/altitude [m] (Altimeter, CTD, {})",
    "wetCDOM": "fCDOM (mg/m**3)",
    "longitude": "Longitude",
    "latitude": "Latitude",
    "station": "Event",
}


class Hex2pyData(Casts):
    def __init__(
        self,
        path_to_data: Path | str = "",
        ctd_data: list[xr.Dataset] = [],
        processing_info: dict = {},
        action_log: Path | str = "",
        dship_mapper_tolerance: int = 300,
        pattern: str = "",
        auto_creator: bool = False,
        cruise: str = "",
        ctd_manufacturer: str = "Sea-Bird",
        validated_parameters: list[str] = [],
        use_multiprocessing: bool = True,
        ctdclient_used: bool = False,
    ) -> None:
        super().__init__(
            path_to_data,
            ctd_data,
            processing_info,
            pattern,
            use_multiprocessing=use_multiprocessing,
        )
        self.action_log = action_log
        self.dship_mapper_tolerance = dship_mapper_tolerance
        self.pattern = pattern
        self.auto_creator = auto_creator
        self.cruise = cruise
        self.column_mapper = {
            k: v.format(ctd_manufacturer) for k, v in column_mapper.items()
        }
        self.validated_parameters = [
            value.lower() for value in validated_parameters
        ]
        self.ctdclient_used = self.check_ctdlient_usage(ctdclient_used)
        if auto_creator:
            self.run()

    def check_ctdlient_usage(self, user_entry: bool = False) -> bool:
        if user_entry:
            return True
        current_client_dship_keys = [
            "Cruise",
            "Station",
            "Platform",
            "Cast",
            "Operator",
            "GPS_Time",
            "GPS_Lat",
            "GPS_Lon",
            "Water_Depth",
            "Air_Pressure",
            "WsStartID",
            "Pos_Alias",
        ]
        custom_metadata = self.data[0].meta.custom.keys()
        for key in current_client_dship_keys:
            if not key in custom_metadata:
                return False
        return True

    def map_column_names(self):
        self.df = self.df.rename(mapper=self.column_mapper, axis=1)
        self.map_quality_flag_names()
        quality_flags_to_keep = [
            p for p in self.df.columns if p.startswith("Quality flag")
        ]
        self.drop_unmaped_columns(
            [*list(self.column_mapper.values()), *quality_flags_to_keep]
        )

    def drop_unmaped_columns(self, column_names: list):
        column_names += ["Station", "Date/Time"]
        self.df = self.df.drop(
            labels=[
                column
                for column in self.df.columns
                if column not in column_names
            ],
            axis=1,
            errors="ignore",
        )

    def map_quality_flag_names(self):
        for column in [c for c in self.df.columns if "qc" in c]:
            if not column.startswith(
                (
                    "pressure",
                    "conductivity",
                    "temperature",
                    "salinity",
                    "oxygen",
                )
            ):
                continue
            self.df.rename(
                mapper={column: self.quality_flag_name(column)},
                axis=1,
                inplace=True,
            )

    def quality_flag_name(self, column_name: str) -> str:
        new_name = "Quality flag, "
        if column_name.startswith(("pressure", "temperature")):
            new_name += "water "
        new_name += column_name.lower().split("_")[0]
        find_sensor_with_number = "2" if column_name.endswith("2") else "1"

        if find_sensor_with_number:
            new_name += f" []//*Sensor {find_sensor_with_number};"
        new_name += " QC flag meanings: 0:no QC, 1:good, 2:probably good, 3:probably bad, 4:bad, 5-7:not used, 8:interpolated, 9:missing"

        return new_name

    def run(self):
        self.add_cast_numbers()
        if self.action_log:
            self.unmapped_dship_events = dship_event_mapper(
                self.data, self.action_log, self.dship_mapper_tolerance
            )
            print(self.unmapped_dship_events)
        self.add("Cast")
        self.add("Station")
        self.add_other_oxygen_formats()
        self.convert_time_format()
        self.create_grand_dataframe()
        self.map_column_names()
        self.to_tsv()
        self.read_sensor_info_and_create_report(
            ctdclient_used=self.ctdclient_used
        )

    def add_other_oxygen_formats(self):
        for cast in self.data:
            # potential density
            cast.add.teos10_vars()
            # umol/L
            o_umol_l = oxygen_umolperkg_to_umolperl(cast.oxygen, cast.density)
            try:
                _ = cast.oxygen.data.shape[1]
                dims = (cast.access.dims[0], "sensor")
            except IndexError:
                dims = (cast.access.dims[0],)

            cast["ox_umol_l"] = (
                dims,
                o_umol_l.data,
                {},
            )

            # ml/L
            o_ml_l = o_umol_l / 44660
            cast["ox_ml_l"] = (
                dims,
                o_ml_l.data,
                {},
            )

    def read_sensor_info_and_create_report(self, *args, **kwargs):
        if len(self.sensor_info) > 1:
            warnings.warn(
                "Sensor anomalies found. Please check the sensor_info attribute for details."
            )
            sensor_info = []
            for configuration in self.sensor_info:
                for sensor in configuration[1]:
                    sensor_info.append(sensor)
        else:
            sensor_info = self.sensor_info[0][1]
        if self.cruise:
            self.report = ProcessingReport(
                cruise_label=self.cruise,
                sensor_info=sensor_info,
                processing_modules=self.data[0].meta.provenance.keys(),
                validated=bool(self.validated_parameters),
                *args,
                **kwargs,
            )

    def create_grand_dataframe(self):
        list_of_dfs = [cast.access.pandas_dataframe() for cast in self.data]
        self.df = pd.concat(list_of_dfs, ignore_index=False).reset_index()

    def add(self, name: str):
        for cast in self.data:
            cast[name] = (
                (cast.access.dims[0],),
                np.full(
                    fill_value=cast.meta.custom[name],
                    shape=cast.access.size,
                ),
                {},
            )

    def convert_time_format(self):
        for cast in self.data:
            try:
                datetime_object = cast["time"].data.astype("datetime64[s]")
                cast["Date/Time"] = (
                    (cast.access.dims[0],),
                    np.datetime_as_string(datetime_object),
                    {},
                )
            except KeyError:
                break

    def to_tsv(self, file_name: str | Path | None = None):
        file_name = f"{self.cruise}_CTD" if file_name is None else file_name
        # format the output float values
        mapper = {v: k for k, v in column_mapper.items()}

        df_out = self.df.copy()

        for column in df_out.columns:
            try:
                df_out[column] = df_out[column].astype("float")
            except ValueError:
                continue
            if column.startswith("Quality"):
                df_out[column] = df_out[column].map("{:.0f}".format)
                continue
            try:
                mapped_name = mapper[column.replace("Sea-Bird", "{}")]
            except KeyError:
                continue
            formatter = self.data[0].export._set_output_format(
                mapped_name.replace("2", "")
            )
            df_out[column] = df_out[column].map(formatter.format)
        df_out.to_csv(
            path_or_buf=Path(file_name).with_suffix(".tab"),
            sep="\t",
            index=False,
        )
