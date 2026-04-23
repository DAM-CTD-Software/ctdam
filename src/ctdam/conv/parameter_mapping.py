import logging
from math import floor

import gsw
import numpy as np
import pandas as pd
from seabirdscientific import cal_coefficients as sbs_cal
from seabirdscientific import conversion as sbs_con

from ctdam.parser.parameter import Parameters
from ctdam.utils import map_metadata

logger = logging.getLogger(__name__)


class ParameterMapping:
    """ """

    def __init__(
        self,
        xmlcon_part: dict,
        raw_data: pd.DataFrame,
        parameters: Parameters,
        voltage_sensors_start: int = 6,
    ) -> None:
        self.source = xmlcon_part
        self.name = (
            xmlcon_part["SensorName"]
            if xmlcon_part["SensorName"]
            else xmlcon_part["SerialNumber"]
        )
        self.sensor_id = xmlcon_part["@SensorID"]
        self.raw_data = raw_data
        self.voltage_sensors_start = voltage_sensors_start
        if self.name[-1] == "2":
            self.name = self.name[:-1]
            self.second_sensor = True
        else:
            self.second_sensor = False
        self.parameters = parameters
        self.param_types = [p.param for p in parameters.get_parameter_list()]
        self.sample_interval = 1 / 24
        self.sensor_data = self.locate_sensor_data(raw_data)
        if isinstance(self.sensor_data, np.ndarray):
            self.coefficients = self.extract_coefficients(xmlcon_part)
            self.metadata = map_metadata(self.name, self.second_sensor)

    def extract_coefficients(self, source: dict):
        """


        Parameters
        ----------
        source: dict


        Returns
        -------

        """
        # Temperature SBE 4
        if self.sensor_id == "55":
            if source["UseG_J"] == "1":
                self.convert_freq_temperature()
            else:
                self.convert_temperature()

        # Conductivity SBE 3
        elif self.sensor_id == "3":
            if source["Coefficients"][0]["@equation"] == "1":
                logger.error(
                    "Unsupported Conductivity coefficients given, please use the new coefficients."
                )
            self.convert_conductivity()
        # Pressure
        elif self.sensor_id == "45":
            self.convert_pressure()
        # Oxygen SBE43
        elif self.sensor_id == "38":
            if source["CalibrationCoefficients"][0]["@equation"] == "1":
                logger.error(
                    "Unsupported Oxygen coefficients given, please use the new coefficients."
                )
            self.convert_oxygen()
        # PAR
        elif self.sensor_id == "42":
            self.coef = sbs_cal.PARCoefficients
            self.coef.im = float(source["M"])
            self.coef.a0 = float(source["CalibrationConstant"])
            self.coef.a1 = float(source["Offset"])
            self.coef.multiplier = float(source["Multiplier"])
            self.converted_data = (
                self.coef.multiplier
                * (
                    (10**9 * 10 ** (self.sensor_data / self.coef.im))
                    / self.coef.a0
                )
                + self.coef.a1
            )

        # Altimeter
        elif self.sensor_id == "0":
            self.coef = sbs_cal.AltimeterCoefficients
            self.coef.slope = float(source["ScaleFactor"])
            self.coef.offset = float(source["Offset"])
            self.converted_data = sbs_con.convert_altimeter(
                volts=self.sensor_data,
                coefs=self.coef,
            )
        # Fluorometer
        elif self.sensor_id in ["20", "19"]:
            self.coef = sbs_cal.ECOCoefficients
            self.coef.slope = float(source["ScaleFactor"])
            self.coef.offset = float(source["Vblank"])
            self.converted_data = sbs_con.convert_eco(
                raw=self.sensor_data,
                coefs=self.coef,
            )
        # Turbidity Meter
        elif self.sensor_id == "67":
            self.coef = sbs_cal.ECOCoefficients
            self.coef.slope = float(source["ScaleFactor"])
            self.coef.offset = float(source["DarkVoltage"])
            self.converted_data = sbs_con.convert_eco(
                raw=self.sensor_data,
                coefs=self.coef,
            )
        # SPAR
        elif self.sensor_id == "51":
            self.coef = sbs_cal.SPARCoefficients
            self.coef.conversion_factor = float(source["ConversionFactor"])
            self.converted_data = sbs_con.convert_spar_biospherical(
                volts=self.sensor_data,
                coefs=self.coef,
            )
        # User Polynomial Sensor
        elif self.sensor_id == "61":
            if (
                self.name.startswith("Oxygen")
                or self.source["SerialNumber"] == "Pyro1"
            ):
                self.convert_oxygen_pyro_science()
            elif self.name.startswith("Flow Meter"):
                self.create_parameter(
                    self.sensor_data * float(self.source["A1"]),
                    map_metadata("Flow Meter", self.second_sensor),
                    "Flow",
                )

    def locate_sensor_data(self, raw_data: dict) -> np.ndarray | None:
        """


        Parameters
        ----------
        raw_data: dict


        Returns
        -------

        """
        if self.name in ["Temperature", "Conductivity"]:
            name = self.name.lower()
            if self.second_sensor:
                name = "secondary " + name

        elif self.name == "Pressure":
            name = "digiquartz pressure"
        elif self.name == "SPAR":
            name = "surface par"
        else:
            sensor_index = int(self.source["Channel"])
            name = f"volt {sensor_index - self.voltage_sensors_start}"

        try:
            sensor_data = raw_data[name].values
        except Exception as error:
            logger.debug(
                f"Could not locate sensor data for {self.name}: {error}"
            )
            sensor_data = None
        return sensor_data

    def create_parameter(self, data, metadata: dict = {}, name: str = ""):
        """


        Parameters
        ----------
        data :

        metadata: dict
             (Default value = {})
        name: str
             (Default value = "")

        Returns
        -------

        """
        try:
            self.parameters.create_parameter(
                data=data,
                metadata=metadata,
                name=name,
            )
        except AttributeError:
            logger.debug(f"{name} had no succesfull mapping.")

    def convert_freq_temperature(self):
        """ """
        self.coef = sbs_cal.TemperatureFrequencyCoefficients
        for param in ["G", "H", "I", "J", "F0"]:
            setattr(self.coef, param.lower(), float(self.source[param]))
        self.converted_data = sbs_con.convert_temperature_frequency(
            frequency=self.sensor_data,
            coefs=self.coef,
            standard="ITS90",
            units="C",
        )

    def convert_temperature(self):
        """ """
        self.coef = sbs_cal.TemperatureCoefficients
        for index, param in enumerate(["A", "B", "C", "D"]):
            setattr(self.coef, f"a{index}", float(self.source[param]))
        self.converted_data = sbs_con.convert_temperature(
            frequency=self.sensor_data,
            coefs=self.coef,
            standard="ITS90",
            units="C",
        )

    def convert_pressure(self):
        """ """
        self.coef = sbs_cal.PressureDigiquartzCoefficients
        for param in self.source:
            if param in [
                "Channel",
                "SensorName",
                "@SensorID",
                "SerialNumber",
                "CalibrationDate",
                "Slope",
                "Offset",
            ]:
                continue
            setattr(
                self.coef,
                param if param.startswith("A") else param.lower(),
                float(self.source[param]),
            )
        self.converted_data = sbs_con.convert_pressure_digiquartz(
            pressure_count=self.sensor_data,
            compensation_voltage=self.raw_data["temperature compensation"]
            .astype(float)
            .values,
            coefs=self.coef,
            units="dbar",
            sample_interval=self.sample_interval,
        )
        # apply correction on data
        self.converted_data = self.converted_data * float(
            self.source["Slope"]
        ) + float(self.source["Offset"])

    def convert_conductivity(self):
        """ """
        self.coef = sbs_cal.ConductivityCoefficients
        for param in ["G", "H", "I", "J", "CPcor", "CTcor", "WBOTC"]:
            setattr(
                self.coef,
                param.lower(),
                float(self.source["Coefficients"][1][param]),
            )
        if "Pressure" not in self.param_types:
            return
        p_values = self.parameters["prDM"].data
        if "Temperature" in self.param_types:
            if self.second_sensor:
                t_values = self.parameters["t190C"].data
            else:
                t_values = self.parameters["t090C"].data
        else:
            return

        self.converted_data = sbs_con.convert_conductivity(
            conductivity_count=self.sensor_data,
            temperature=t_values,
            pressure=p_values,
            coefs=self.coef,
            scalar=1,
        )
        self.convert_salinity(self.converted_data, t_values, p_values)

    def convert_salinity(
        self,
        conductivity: np.ndarray,
        t_values: np.ndarray,
        p_values: np.ndarray,
    ):
        """


        Parameters
        ----------
        conductivity: np.ndarray

        t_values: np.ndarray

        p_values: np.ndarray


        Returns
        -------

        """
        # TODO: allow selection of baltic salinity conversion here
        converted_data = gsw.SP_from_C(
            C=conductivity,
            t=t_values,
            p=p_values,
        )
        self.create_parameter(
            converted_data, map_metadata("Salinity", self.second_sensor)
        )

    def convert_sbe43_oxygen(
        self,
        voltage: np.ndarray,
        temperature: np.ndarray,
        pressure: np.ndarray,
        salinity: np.ndarray,
        coefs: sbs_cal.Oxygen43Coefficients,
        apply_tau_correction: bool = False,
        apply_hysteresis_correction: bool = False,
        window_size: float = 1,
        sample_interval: float = 1,
    ):
        """
        Overwrite of Sea-Birds super slow function.

        Parameters
        ----------
        voltage: np.ndarray

        temperature: np.ndarray

        pressure: np.ndarray

        salinity: np.ndarray

        coefs: sbs_cal.Oxygen43Coefficients :

        apply_tau_correction: bool
             (Default value = False)
        apply_hysteresis_correction: bool
             (Default value = False)
        window_size: float
             (Default value = 1)
        sample_interval: float
             (Default value = 1)

        Returns
        -------

        """
        # start with all 0 for the dvdt
        dvdt_values = np.zeros(len(voltage))
        if apply_tau_correction:
            # Calculates how many scans to have on either side of our median
            # point, accounting for going out of index bounds
            scans_per_side = floor(window_size / 2 / sample_interval)
            for i in range(scans_per_side, len(voltage) - scans_per_side):
                ox_subset = voltage[
                    i - scans_per_side : i + scans_per_side + 1
                ]

                time_subset = np.arange(
                    0,
                    len(ox_subset) * sample_interval,
                    sample_interval,
                    dtype=float,
                )

                def manual_linregress(x, y):
                    """


                    Parameters
                    ----------
                    x :

                    y :


                    Returns
                    -------

                    """
                    x_mean, y_mean = np.mean(x), np.mean(y)
                    cov = np.sum((x - x_mean) * (y - y_mean))
                    var = np.sum((x - x_mean) ** 2)
                    slope = cov / var
                    intercept = y_mean - slope * x_mean
                    return slope, intercept

                slope, _ = manual_linregress(time_subset, ox_subset)

                dvdt_values[i] = slope

        correct_ox_voltages = voltage.copy()
        if apply_hysteresis_correction:
            # Hysteresis starts at 1 because 0 can't be corrected
            for i in range(1, len(correct_ox_voltages)):
                # All Equation info from APPLICATION NOTE NO. 64-3
                d = 1 + coefs.h1 * (np.exp(pressure[i] / coefs.h2) - 1)
                c = np.exp(-1 * sample_interval / coefs.h3)
                ox_volts = correct_ox_voltages[i] + coefs.v_offset

                prev_ox_volts_new = correct_ox_voltages[i - 1] + coefs.v_offset
                ox_volts_new = (
                    (ox_volts + prev_ox_volts_new * c * d)
                    - (prev_ox_volts_new * c)
                ) / d
                ox_volts_final = ox_volts_new - coefs.v_offset
                correct_ox_voltages[i] = ox_volts_final

        oxygen = sbs_con._convert_sbe43_oxygen(
            correct_ox_voltages,
            temperature,
            pressure,
            salinity,
            coefs,
            dvdt_values,
        )
        return oxygen

    def convert_oxygen(self):
        """ """
        self.coef = sbs_cal.Oxygen43Coefficients
        for param, value in self.source["CalibrationCoefficients"][1].items():
            param = f"v_{param}" if param == "offset" else param
            param = "tau_20" if param == "Tau20" else param
            setattr(self.coef, param.lower(), float(value))
        if "Pressure" not in self.param_types:
            return
        p_values = self.parameters["prDM"].data
        if "Temperature" in self.param_types:
            if self.second_sensor:
                t_values = self.parameters["t190C"].data
            else:
                t_values = self.parameters["t090C"].data
        else:
            return
        if "Salinity" in self.param_types:
            if self.second_sensor:
                s_values = self.parameters["sal11"].data
            else:
                s_values = self.parameters["sal00"].data
        else:
            return
        converted_data = self.convert_sbe43_oxygen(
            voltage=self.sensor_data,
            temperature=t_values,
            pressure=p_values,
            salinity=s_values,
            coefs=self.coef,
            apply_tau_correction=True,
            apply_hysteresis_correction=True,
            window_size=2,
            sample_interval=self.sample_interval,
        )
        self.create_parameter(
            converted_data,
            map_metadata("Oxygen mlL", self.second_sensor),
        )
        # TODO: flexibilize this
        # give out umol/kg
        try:
            lon = self.raw_data["NMEA Longitude"]
            lat = self.raw_data["NMEA Latitude"]
        except KeyError:
            lon = 0
            lat = 0
        absolute_salinity = gsw.SA_from_SP(
            SP=s_values,
            p=p_values,
            lon=lon,
            lat=lat,
        )
        self.create_parameter(
            absolute_salinity,
            map_metadata("Absolute Salinity", self.second_sensor),
        )
        conservative_temperature = gsw.conversions.CT_from_t(
            SA=absolute_salinity,
            t=t_values,
            p=p_values,
        )
        self.create_parameter(
            conservative_temperature,
            map_metadata("Conservative Temperature", self.second_sensor),
        )
        # TODO: flexibile sigma selection
        potential_density = gsw.density.sigma0(
            SA=absolute_salinity,
            CT=conservative_temperature,
        )
        self.create_parameter(
            potential_density, map_metadata("Density"), self.second_sensor
        )
        self.converted_data = sbs_con.convert_oxygen_to_umol_per_kg(
            ox_values=converted_data,
            potential_density=potential_density,
        )
        # give out umol/l
        oxygen_umol_l = self.converted_data * potential_density / 1000
        self.create_parameter(
            oxygen_umol_l,
            map_metadata(
                "Oxygen umolL",
                self.second_sensor,
            ),
        )

    def convert_oxygen_pyro_science(self):
        """ """
        try:
            oxygen = self.sensor_data * float(self.source["A1"])
        except TypeError as error:
            logger.error(
                f"could not convert pyro oxygen: {self.source['SerialNumber']}: {error}"
            )
        else:
            # oxygen in umol/kg
            self.create_parameter(
                oxygen, map_metadata("Oxygen Pyro 2"), self.second_sensor
            )
            # oxygen in ml/l
            if "ConservativeTemperature" in self.param_types:
                conservative_temperature = self.parameters["gsw_ctA0"].data
            else:
                return
            if "AbsoluteSalinity" in self.param_types:
                absolute_salinity = self.parameters["gsw_saA0"].data
            else:
                return
            potential_density = gsw.density.sigma0(
                SA=absolute_salinity,
                CT=conservative_temperature,
            )
            oxygen_mll = (
                (oxygen * (potential_density + 1000))
                / 1
                / sbs_con.OXYGEN_MLPERL_TO_UMOLPERKG
            )
            self.create_parameter(
                oxygen_mll,
                map_metadata("Oxygen Pyro mlL 2", self.second_sensor),
            )
