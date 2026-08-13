import gsw
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from math import floor
from scipy import stats


def calculate_tau(temp, pressure, cal):
    """Calculate sensor time constant tau(T,P)."""
    D0 = float(cal.D0)
    D1 = float(cal.D1)
    D2 = float(cal.D2)
    tau20 = float(cal.Tau20)

    tau = tau20 * D0 * np.exp(D1 * pressure + D2 * (temp - 20))
    return tau

def calculate_dvdt_window(volt, time_seconds, window_seconds=2.0):
    """
    Calculate dV/dt over a window as specified in SBE documentation.
    If there are fewer than 2 points in the window (2s by default), dV/dt is set to zero.
    """
    # Convert the desired window length (in seconds) to samples
    dt = np.mean(np.diff(time_seconds))
    window_length = int(window_seconds / dt)

    # window_length must be odd and >= polyorder + 2
    if window_length % 2 == 0:
        window_length += 1
    window_length = max(window_length, 5)

    # Compute the first derivative directly
    dVdt = savgol_filter(
        volt, window_length=window_length, polyorder=1, deriv=1, delta=dt
    )

    return dVdt


def calculate_oxsol(temp, salinity):
    """
    Calculate oxygen solubility using Garcia and Gordon (1992).
    Returns oxygen solubility in ml/L.
    """
    T_scaled = np.log((298.15 - temp) / (273.15 + temp))

    # Garcia and Gordon (1992) coefficients
    A0 = 2.00907
    A1 = 3.22014
    A2 = 4.05010
    A3 = 4.94457
    A4 = -0.256847
    A5 = 3.88767
    B0 = -0.00624523
    B1 = -0.00737614
    B2 = -0.0103410
    B3 = -0.00817083
    C0 = -0.000000488682

    oxsol = np.exp(
        A0
        + A1 * T_scaled
        + A2 * T_scaled**2
        + A3 * T_scaled**3
        + A4 * T_scaled**4
        + A5 * T_scaled**5
        + salinity * (B0 + B1 * T_scaled + B2 * T_scaled**2 + B3 * T_scaled**3)
        + C0 * salinity**2
    )

    return oxsol


def pressure(
    data: np.ndarray,
    cfgp: pd.Series,
    sensor_temperature: np.ndarray,
) -> np.ndarray:

    pcal = cfgp["cal"]

    psi_to_dbar = 0.689476

    Td = float(pcal.AD590M) * sensor_temperature + float(pcal.AD590B)

    c = float(pcal.C1) + Td * (float(pcal.C2) + Td * float(pcal.C3))

    d = float(pcal.D1) + Td * float(pcal.D2)

    t0 = float(pcal.T1) + Td * (
        float(pcal.T2)
        + Td * (float(pcal.T3) + Td * (float(pcal.T4) + Td * float(pcal.T5)))
    )

    t0f = 1e-6 * t0 * data
    factor = 1.0 - t0f**2

    pressure_absolute = psi_to_dbar * c * factor * (1.0 - d * factor)

    pressure_absolute = float(pcal.Slope) * pressure_absolute + float(
        pcal.Offset
    )
    atmospheric_pressure = 10.1353

    return pressure_absolute - atmospheric_pressure


def temperature(data: np.ndarray, cfgp: pd.Series):
    """Calculate  temperature given frequency and
    temperature calibration structure tcal
    D. Rudnick 01/06/05"""
    tcal = cfgp.cal
    logf0f = np.log(float(tcal.F0) / data)
    temp = (
        1
        / (
            float(tcal.G)
            + logf0f
            * (
                float(tcal.H)
                + logf0f * (float(tcal.I) + logf0f * float(tcal.J))
            )
        )
    ) - 273.15
    # correct via custom slope and offset
    temp = float(tcal.Slope) * temp + float(tcal.Offset)
    return temp


def conductivity(
    data: np.ndarray,
    cfgp: pd.Series,
    temperature: np.ndarray,
    pressure: np.ndarray,
):
    """Calculates conductivity given frequency, temperature,
    pressure and conductivity calibration structure ccal.
    D. Rudnick 01/06/05"""

    ccal = cfgp["cal"].Coefficients[1]

    ff = data / 1000.0

    g = float(ccal.G)
    h = float(ccal.H)
    i = float(ccal.I)
    j = float(ccal.J)
    ctcor = float(ccal.CTcor)
    cpcor = float(ccal.CPcor)

    conductivity = (g + ff**2 * (h + ff * (i + ff * j))) / (
        1.0 + ctcor * temperature + cpcor * pressure
    )

    # correct via custom slope and offset
    conductivity = float(cfgp["cal"].Slope) * conductivity + float(
        cfgp["cal"].Offset
    )
    return conductivity


def salinity(
    conductivity: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
) -> np.ndarray:
    """ """

    practical_salinity = gsw.SP_from_C(
        conductivity,
        temperature,
        pressure,
    )

    return practical_salinity

KELVIN_OFFSET_0C = 273.15
KELVIN_OFFSET_25C = 298.15


def convert_sbe43_oxygen(
    voltage: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
    salinity: np.ndarray,
    cal,
    apply_tau_correction: bool = True,
    apply_hysteresis_correction: bool = True,
    window_size: float = 2.0,
    sample_interval: float = 1.0,
) -> np.ndarray:
    """Convert SBE43 voltage to oxygen in ml/L."""

    # XMLCON calibration coefficients
    soc = float(cal.Soc)
    v_offset = float(cal.offset)

    a = float(cal.A)
    b = float(cal.B)
    c = float(cal.C)
    e = float(cal.E)

    tau_20 = float(cal.Tau20)
    d1 = float(cal.D1)
    d2 = float(cal.D2)

    h1 = float(cal.H1)
    h2 = float(cal.H2)
    h3 = float(cal.H3)

    # Tau correction

    dvdt_values = np.zeros(
        len(voltage),
        dtype=float,
    )

    if apply_tau_correction:
        scans_per_side = floor(window_size / 2 / sample_interval)

        for i in range(scans_per_side,len(voltage) - scans_per_side):
            ox_subset = voltage[
                i - scans_per_side : i + scans_per_side + 1
            ]

            time_subset = np.arange(
                0,
                len(ox_subset) * sample_interval,
                sample_interval,
                dtype=float,
            )

            # Same regression as in old ParameterMapping
            x_mean = np.mean(time_subset)
            y_mean = np.mean(ox_subset)

            cov = np.sum((time_subset - x_mean) * (ox_subset - y_mean))

            var = np.sum((time_subset - x_mean) ** 2)
            slope = cov / var

            dvdt_values[i] = slope

    # Hysteresis correction
    corrected_voltage = np.asarray(voltage, dtype=float).copy()
    if apply_hysteresis_correction:
        for i in range(1, len(corrected_voltage)):
            d = (1.0 + h1 * (np.exp(pressure[i] / h2) - 1.0))
            c_hyst = np.exp(-sample_interval / h3)
            ox_volts = (corrected_voltage[i] + v_offset)

            previous_ox_volts = (corrected_voltage[i - 1] + v_offset)

            ox_volts_new = (
                (ox_volts + previous_ox_volts * c_hyst * d)
                - (previous_ox_volts * c_hyst)
            ) / d

            corrected_voltage[i] = (ox_volts_new - v_offset)

    return _convert_sbe43_oxygen(
        voltage=corrected_voltage,
        temperature=temperature,
        pressure=pressure,
        salinity=salinity,
        soc=soc,
        v_offset=v_offset,
        a=a,
        b=b,
        c=c,
        e=e,
        tau_20=tau_20,
        d1=d1,
        d2=d2,
        dvdt_value=dvdt_values,
    )


def _convert_sbe43_oxygen(
    voltage: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
    salinity: np.ndarray,
    soc: float,
    v_offset: float,
    a: float,
    b: float,
    c: float,
    e: float,
    tau_20: float,
    d1: float,
    d2: float,
    dvdt_value: np.ndarray,
) -> np.ndarray:
    """Convert SBE43 voltage to oxygen in ml/L."""

    # SBE43 oxygen solubility coefficients
    a0 = 2.00907
    a1 = 3.22014
    a2 = 4.05010
    a3 = 4.94457
    a4 = -0.256847
    a5 = 3.88767

    b0 = -0.00624523
    b1 = -0.00737614
    b2 = -0.0103410
    b3 = -0.00817083

    c0 = -0.000000488682

    ts = np.log(
        (KELVIN_OFFSET_25C - temperature)
        / (KELVIN_OFFSET_0C + temperature)
    )

    a_term = (a0 + a1 * ts + a2 * ts**2 + a3 * ts**3 + a4 * ts**4 + a5 * ts**5)
    b_term = salinity * (b0 + b1 * ts + b2 * ts**2 + b3 * ts**3)
    c_term = (c0 * salinity**2)

    solubility = np.exp(a_term + b_term + c_term)

    # Tau correction
    tau = (tau_20 * np.exp(d1 * pressure + d2 * (temperature - 20.0)) * dvdt_value)
    soc_term = (soc * (voltage + v_offset + tau))
    temp_term = (1.0 + a * temperature + b * temperature**2 + c * temperature**3)

    pressure_term = np.exp((e * pressure) / (temperature + KELVIN_OFFSET_0C))

    oxygen_ml_per_l = (soc_term * solubility * temp_term * pressure_term)

    return oxygen_ml_per_l


def oxygen(
    data: np.ndarray,
    cfgp: pd.Series,
    temperature: np.ndarray,
    salinity: np.ndarray,
    pressure: np.ndarray,
    time: np.ndarray,
    use_tau_correction: bool = True,
    use_hysteresis_correction: bool = True,
) -> np.ndarray:

    ocal = cfgp["cal"]

    equation_index = (
        int(ocal.Use2007Equation)
        if hasattr(
            ocal,
            "Use2007Equation",
        )
        else 1
    )

    cal = ocal.CalibrationCoefficients[
        equation_index
    ]

    sample_interval = 1.0 / 24.0

    oxygen_ml_per_l = (
        convert_sbe43_oxygen(
            voltage=data,
            temperature=temperature,
            pressure=pressure,
            salinity=salinity,
            cal=cal,
            apply_tau_correction=(
                use_tau_correction
            ),
            apply_hysteresis_correction=(
                use_hysteresis_correction
            ),
            window_size=2.0,
            sample_interval=sample_interval,
        )
    )

    absolute_salinity = gsw.SA_from_SP(
        salinity,
        pressure,
        0.0,
        0.0,
    )

    conservative_temperature = (
        gsw.CT_from_t(
            absolute_salinity,
            temperature,
            pressure,
        )
    )

    potential_density = gsw.sigma0(
        absolute_salinity,
        conservative_temperature,
    )

    # ml/L -> µmol/kg
    oxygen_umol_per_kg = (
        oxygen_ml_per_l
        * 44660.0
        / (
            potential_density
            + 1000.0
        )
    )

    return oxygen_umol_per_kg

def par_biosphericallicorchelsea(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Convert PAR voltage to PAR values."""

    cal = cfgp["cal"]

    multiplier = float(cal.Multiplier)
    b = float(cal.B)
    m = float(cal.M)
    calibration_constant = float(cal.CalibrationConstant)
    offset = float(cal.Offset)

    par_data = (
        multiplier * (1e9 * 10 ** ((data - b) / m)) / calibration_constant
    ) + offset

    return par_data


def altimeter(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Calculate altimeter distance from voltage."""

    cal = cfgp["cal"]

    scale_factor = float(cal.ScaleFactor)
    offset = float(cal.Offset)

    altitude = data * scale_factor + offset

    return altitude


def fluorescence(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Convert fluorescence voltage using XMLCON calibration."""

    cal = cfgp["cal"]

    scale_factor = float(cal.ScaleFactor)
    vblank = float(cal.Vblank)

    return scale_factor * (data - vblank)


def turbidity(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Convert turbidity voltage using XMLCON calibration."""

    cal = cfgp["cal"]

    scale_factor = float(cal.ScaleFactor)
    dark_voltage = float(cal.DarkVoltage)

    return scale_factor * (data - dark_voltage)


def fluorowetlabcdom(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Convert CDOM voltage using XMLCON calibration."""

    cal = cfgp["cal"]

    scale_factor = float(cal.ScaleFactor)
    vblank = float(cal.Vblank)

    return scale_factor * (data - vblank)


def spar(
    data: np.ndarray,
    cfgp: pd.Series,
) -> np.ndarray:
    """Convert SPAR voltage using XMLCON calibration."""

    cal = cfgp["cal"]

    conversion_factor = float(cal.ConversionFactor)
    ratio_multiplier = float(cal.RatioMultiplier)

    return data * conversion_factor * ratio_multiplier
