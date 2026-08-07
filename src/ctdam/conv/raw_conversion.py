import gsw
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


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

def calculate_density(
    temperature: np.ndarray,  # ITS-90, °C
    salinity: np.ndarray,     # PSS-78
    pressure: np.ndarray,     # dbar
    longitude: float = 0.0,
    latitude: float = 0.0,
) -> np.ndarray:
    """Gibt in-situ Dichte in kg/m³ zurück."""
    sa = gsw.SA_from_SP(salinity, pressure, longitude, latitude)
    ct = gsw.CT_from_t(sa, temperature, pressure)
    rho = gsw.rho(sa, ct, pressure)
    return rho

def apply_oxygen_hysteresis(
    voltage: np.ndarray,
    pressure: np.ndarray,
    cal,
    sample_interval: float,
) -> np.ndarray:
    """Apply the SBE43 hysteresis correction to oxygen voltage."""

    h1 = float(cal.H1)
    h2 = float(cal.H2)
    h3 = float(cal.H3)
    voltage_offset = float(cal.offset)

    corrected_voltage = np.asarray(
        voltage,
        dtype=float,
    ).copy()

    c_factor = np.exp(
        -sample_interval / h3
    )

    for index in range(1, len(corrected_voltage)):
        d_factor = 1.0 + h1 * (
            np.exp(
                pressure[index] / h2
            )
            - 1.0
        )

        current_voltage = (
            corrected_voltage[index]
            + voltage_offset
        )

        previous_voltage = (
            corrected_voltage[index - 1]
            + voltage_offset
        )

        corrected_with_offset = (
            (
                current_voltage
                + previous_voltage
                * c_factor
                * d_factor
            )
            - previous_voltage
            * c_factor
        ) / d_factor

        corrected_voltage[index] = (
            corrected_with_offset
            - voltage_offset
        )

    return corrected_voltage

def oxygen(
    data: np.ndarray,
    cfgp: pd.Series,
    temperature: np.ndarray,
    salinity: np.ndarray,
    pressure: np.ndarray,
    time: np.ndarray,
    use_tau_correction: bool = True,
    use_hysteresis_correction: bool = True,
    min_pressure: float = 1.0,
) -> np.ndarray:
    """Convert SBE43 oxygen voltage to µmol/kg."""

    ocal = cfgp["cal"]

    equation_index = (
        int(ocal.Use2007Equation)
        if hasattr(ocal, "Use2007Equation")
        else 1
    )

    cal = ocal.CalibrationCoefficients[
        equation_index
    ]

    soc = float(cal.Soc)
    voltage_offset = float(cal.offset)
    a = float(cal.A)
    b = float(cal.B)
    c = float(cal.C)
    e = float(cal.E)

    # Zeit in Sekunden umwandeln
    if (
        hasattr(time, "dtype")
        and np.issubdtype(
            time.dtype,
            np.datetime64,
        )
    ):
        time_seconds = (
            time - time[0]
        ) / np.timedelta64(1, "s")

    elif (
        hasattr(time, "dtype")
        and np.issubdtype(
            time.dtype,
            np.timedelta64,
        )
    ):
        time_seconds = (
            time
            / np.timedelta64(1, "s")
        )

    else:
        time_seconds = np.asarray(
            time,
            dtype=float,
        )

    time_seconds = np.asarray(
        time_seconds,
        dtype=float,
    )

    if len(time_seconds) > 1:
        sample_interval = float(
            np.nanmedian(
                np.diff(time_seconds)
            )
        )
    else:
        sample_interval = 1.0

    if (
        not np.isfinite(sample_interval)
        or sample_interval <= 0
    ):
        raise ValueError(
            "The oxygen sample interval "
            "must be a positive finite value."
        )

    # Zunächst eine Kopie der Rohspannung erzeugen
    corrected_data = np.asarray(
        data,
        dtype=float,
    ).copy()

    # Hysteresekorrektur auf die Spannung anwenden
    if use_hysteresis_correction:
        corrected_data = (
            apply_oxygen_hysteresis(
                corrected_data,
                pressure,
                cal,
                sample_interval,
            )
        )

    # Tau-Korrektur
    if use_tau_correction:
        dvdt = calculate_dvdt_window(
            corrected_data,
            time_seconds,
            window_seconds=1.0,
        )

        tau = calculate_tau(
            temperature,
            pressure,
            cal,
        )

        tau_correction = tau * dvdt

    else:
        tau_correction = 0.0

    # Sauerstofflöslichkeit in ml/L
    oxsol = calculate_oxsol(
        temperature,
        salinity,
    )

    temperature_kelvin = (
        temperature + 273.15
    )

    # SBE43-Gleichung:
    # Ergebnis zunächst in ml/L
    oxygen_ml_per_l = (
        soc
        * (
            corrected_data
            + voltage_offset
            + tau_correction
        )
        * oxsol
        * (
            1.0
            + a * temperature
            + b * temperature**2
            + c * temperature**3
        )
        * np.exp(
            e
            * pressure
            / temperature_kelvin
        )
    )

    # Practical Salinity -> Absolute Salinity
    absolute_salinity = gsw.SA_from_SP(
        salinity,
        pressure,
        0.0,
        0.0,
    )

    # In-situ-Temperatur ->
    # Conservative Temperature
    conservative_temperature = (
        gsw.CT_from_t(
            absolute_salinity,
            temperature,
            pressure,
        )
    )

    # Potenzielle Dichteanomalie
    # Sigma-Theta
    potential_density_anomaly = (
        gsw.sigma0(
            absolute_salinity,
            conservative_temperature,
        )
    )

    # ml/L -> µmol/kg
    oxygen_umol_per_kg = (
        oxygen_ml_per_l
        * 44660.0
        / (
            potential_density_anomaly
            + 1000.0
        )
    )

    # Plausibilitätsprüfungen
    oxygen_umol_per_kg = np.where(
        pressure < min_pressure,
        np.nan,
        oxygen_umol_per_kg,
    )

    oxygen_umol_per_kg = np.where(
        salinity < 1.0,
        np.nan,
        oxygen_umol_per_kg,
    )

    oxygen_umol_per_kg = np.where(
        oxygen_umol_per_kg < 0.0,
        np.nan,
        oxygen_umol_per_kg,
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
