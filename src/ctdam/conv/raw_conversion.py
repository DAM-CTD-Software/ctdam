import numpy as np
import pandas as pd
import gsw
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

    Td = (float(pcal.AD590M) * sensor_temperature + float(pcal.AD590B))

    c = (float(pcal.C1) + Td * (float(pcal.C2) + Td * float(pcal.C3)))

    d = (  float(pcal.D1) + Td * float(pcal.D2))

    t0 = ( float(pcal.T1) + Td * (float(pcal.T2)+ Td * (float(pcal.T3) + Td * (float(pcal.T4) + Td * float(pcal.T5)))))

    t0f = 1e-6 * t0 * data
    factor = 1.0 - t0f**2

    pressure_absolute = (psi_to_dbar * c * factor * (1.0 - d * factor))

    pressure_absolute = (float(pcal.Slope) * pressure_absolute + float(pcal.Offset))
    atmospheric_pressure = 10.1353

    return pressure_absolute - atmospheric_pressure

def temperature(data: np.ndarray, cfgp: pd.Series):
    """Calculate  temperature given frequency and
    temperature calibration structure tcal
    D. Rudnick 01/06/05"""
    tcal = cfgp.cal
    logf0f = np.log(float(tcal.F0) / data)
    temp = (1/(float(tcal.G)+ logf0f * (float(tcal.H) + logf0f * (float(tcal.I) + logf0f * float(tcal.J))))) - 273.15
    return temp

def conductivity(data: np.ndarray, cfgp: pd.Series, temperature: np.ndarray, pressure: np.ndarray):
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

    conductivity = (g + ff**2 * (h + ff * (i + ff * j))) / (1.0 + ctcor * temperature + cpcor * pressure)

    return conductivity


def salinity(
    conductivity: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
) -> np.ndarray:
    """
   
    """

    practical_salinity = gsw.SP_from_C(
        conductivity,
        temperature,
        pressure,
    )

    return practical_salinity


def oxygen(
    data: np.ndarray,
    cfgp: pd.Series,
    temperature: np.ndarray,
    salinity: np.ndarray,
    pressure: np.ndarray,
    time: np.ndarray,
    use_tau_correction: bool = True,
    min_pressure: float = 1.0,
) -> np.ndarray:
    
    

    ocal = cfgp["cal"]

    equation_index = (
        int(ocal.Use2007Equation)
        if hasattr(ocal, "Use2007Equation")
        else 1
    )

    cal = ocal.CalibrationCoefficients[equation_index]

    soc = float(cal.Soc)
    voltage_offset = float(cal.offset)
    a = float(cal.A)
    b = float(cal.B)
    c = float(cal.C)
    e = float(cal.E)

    if (
        hasattr(time, "dtype")
        and np.issubdtype(time.dtype, np.datetime64)
    ):
        time_seconds = (
            time - time[0]
        ) / np.timedelta64(1, "s")

    elif (
        hasattr(time, "dtype")
        and np.issubdtype(time.dtype, np.timedelta64)
    ):
        time_seconds = time / np.timedelta64(1, "s")

    else:
        time_seconds = np.asarray(time, dtype=float)

    if use_tau_correction:
        dvdt = calculate_dvdt_window(
            data,
            time_seconds,
            window_seconds=2.0,
        )

        tau = calculate_tau(
            temperature,
            pressure,
            cal,
        )

        tau_correction = tau * dvdt

    else:
        tau_correction = 0.0

    oxsol = calculate_oxsol(
        temperature,
        salinity,
    )

    temperature_kelvin = temperature + 273.15

    oxygen_data = (soc * (data + voltage_offset + tau_correction) * oxsol * (1.0 + a * temperature + b * temperature**2 + c * temperature**3)
        * np.exp(e * pressure / temperature_kelvin))

    oxygen_data = oxygen_data * 44.6596

    return oxygen_data

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

    par_data = ( multiplier * (1e9 * 10 ** ((data - b) / m)) / calibration_constant) + offset

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
