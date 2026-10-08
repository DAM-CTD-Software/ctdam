import numpy as np
import pandas as pd
from munch import Munch
from numpy.testing import assert_allclose

from ctdam.conv import raw_conversion
from ctdam.conv.pressure_rating import guess_pressure_rating


def test_user_polynomial_conversion():
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
    actual = raw_conversion.userpolynomial(voltage, cfgp)

    assert_allclose(actual, expected)


def test_guess_pressure_rating():
    # From EMB379_000-00_SF_0001.XMLCON sensor 0853
    calibration = {
        "C1": -1.544512e004,
        "C2": 4.633850e-003,
        "C3": 3.812460e-003,
        "D1": 4.741300e-002,
        "D2": 0.000000e000,
        "T1": 3.017247e001,
        "T2": -2.347700e-004,
        "T3": 3.247000e-006,
        "T4": 3.849310e-009,
        "T5": 0.000000e000,
        "AD590M": 1.283640e-002,
        "AD590B": -9.854378e000,
        "Slope": 1.00000000,
        "Offset": 0.00000,
    }

    assert guess_pressure_rating(calibration) == 3000
