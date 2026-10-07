import numpy as np
from munch import munchify

from ctdam.conv.raw_conversion import pressure

PRESSURE_RATINGS_PSIA = (2000, 3000, 6000, 10000, 15000)


def guess_pressure_rating(calibration, sensor_temperature_c=5):
    """Return the nominal pressure rating in psia using a 10% frequency rise."""
    cal = munchify(calibration)
    temp = sensor_temperature_c
    t0 = float(cal.T1) + temp * (
        float(cal.T2)
        + temp
        * (float(cal.T3) + temp * (float(cal.T4) + temp * float(cal.T5)))
    )
    baseline_frequency = 1000000 / t0
    max_estimated_frequency = baseline_frequency * 1.10

    # The pressure converter expects internal temperature as AD590 counts.
    sensor_temp = (temp - float(cal.AD590B)) / float(cal.AD590M)
    pressure_dbar = pressure(
        np.array([max_estimated_frequency]),
        {"cal": cal},
        np.array([sensor_temp]),
    )[0]
    # Restore absolute pressure before comparing with psia ratings.
    estimated_pressure_psia = (pressure_dbar + 10.1353) / 0.689476

    # default is the sensor with the highest pressure rating
    predicted_pressure_rating_psia = 15000

    smallest_difference_found = 999999
    for possible_pressure_rating_psia in PRESSURE_RATINGS_PSIA:
        difference_as_fraction_of_rating = (
            abs(estimated_pressure_psia - possible_pressure_rating_psia)
            / possible_pressure_rating_psia
        )

        if difference_as_fraction_of_rating < smallest_difference_found:
            smallest_difference_found = difference_as_fraction_of_rating
            predicted_pressure_rating_psia = possible_pressure_rating_psia

    return predicted_pressure_rating_psia
