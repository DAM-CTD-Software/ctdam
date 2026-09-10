import numpy as np
import pandas as pd
from munch import Munch
from numpy.testing import assert_allclose

from ctdam.conv import raw_conversion


def test_flow_meter_conversion():
    voltage = np.array([0.0, 1.0, 2.0])
    cfgp = pd.Series(
        {
            "cal": Munch(
                A0="1.0",
                A1="2.0",
                A2="3.0",
                A3="4.0",
            )
        }
    )

    expected = np.array([1.0, 10.0, 49.0])
    actual = raw_conversion.flow_meter(voltage, cfgp)

    assert_allclose(actual, expected)


def test_pyro_oxygen_conversion():
    voltage = np.array([0.0, 1.0, 2.0, np.nan, 1.0])
    potential_density = np.array([25.0, 25.0, 30.0, 25.0, np.nan])
    calibration = Munch(A0="0.0", A1="200.0", A2="0.0", A3="0.0")
    cfgp = pd.Series({"cal": calibration})
    expected = np.array([0.0, 195.12, 388.35, np.nan, np.nan])

    # For example, 200 µmol/L at 1.025 kg/L gives 195.12 µmol/kg.
    actual = raw_conversion.pyro_oxygen(voltage, cfgp, potential_density)
    # Allow for rounding the expected values to two decimal places.
    assert_allclose(actual, expected, rtol=0, atol=0.005)
