import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from ctdam import PARAMETER_MAPPING

logger = logging.getLogger(__name__)


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
        except ValueError:
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
            bad_flag=-9.990e-29,
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
        ds_flat = self._get_flattened_ds(ds)
        index = 0
        for name in ds_flat:
            data_array = ds_flat[name]
            print(name)
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
                print(sensor)
            else:
                metadata = parameter

            new_table_info.append(
                f"name {index} = {metadata['shortname']}: {metadata['longinfo']}{os.linesep}"
            )

            # 'data table spans'
            # data_array = np.column_stack([ds_flat[var].values for var in ds_flat])
            try:
                mx = np.ma.masked_array(
                    data_array, mask=data_array == bad_flag
                )
                span = (np.nanmin(mx), np.nanmax(mx))
            except ValueError:
                span = (0, 0)
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
        ds: xr.xarray,
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
        ds: xr.xarray,
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
        ds_flat = self._get_flattened_ds(ds)
        full_array = np.column_stack([ds_flat[var].values for var in ds_flat])

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

    def _get_flattened_ds(
        self,
        ds,
        suffix_map={"primary": "", "secondary": "2"},
    ) -> xr.Dataset:
        """Turn (scan, sensor) variables into separate (scan,) variables, suffixed like Sea-Bird columns."""
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
                    self._ds.ctd.profile(
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
        good = self._ds[self._flag_var(var)].isin([1, 2])
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
