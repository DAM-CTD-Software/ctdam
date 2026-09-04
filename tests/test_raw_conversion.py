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

