import numpy as np
import pandas as pd


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
    return temp
