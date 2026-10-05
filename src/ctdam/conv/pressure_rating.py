from pathlib import Path

import gsw
import numpy as np
from munch import munchify

from ctdam.conv.raw_conversion import pressure
from ctdam.parser.seabird_data_files import SeabirdDataFile
from ctdam.parser.xmlfiles import XMLCONFile, XMLFile

DEPTH_RATINGS = (1400, 2000, 4200, 6800, 10500)


def _read_pressure_config(path):
    xml = XMLFile(path)
    if xml.xml_tree.tag == "PressureSensor":
        return {"cal": munchify(xml.data["PressureSensor"])}

    return XMLCONFile(path).coefficients["PressureSensor"]


def pressure_sensor_guesser(path, sensor_temperature_c=5):
    hex_path = Path(path).with_suffix(".hex")
    latitude = 0
    if hex_path.is_file():
        hex_file = SeabirdDataFile(hex_path, only_header=True)
        latitude = hex_file.start_position[0]

    cfg = _read_pressure_config(path)
    cal = cfg["cal"]
    temp = sensor_temperature_c
    t0 = float(cal.T1) + temp * (
        float(cal.T2)
        + temp
        * (float(cal.T3) + temp * (float(cal.T4) + temp * float(cal.T5)))
    )

    baseline_frequency = 1000000 / t0
    max_frequency = baseline_frequency * 1.10

    # neccassary to get a pressure reading from the frequency i guess.
    # pressure doesnt use temperature in celius but uses counts
    sensor_temp = (temp - float(cal.AD590B)) / float(cal.AD590M)
    pressure_dbar = pressure(
        np.array([max_frequency]), cfg, np.array([sensor_temp])
    )[0]
    estimated_depth_m = -gsw.z_from_p(pressure_dbar, lat=latitude)

    smallest_difference_found = 999999
    for possible_depth_rating_m in DEPTH_RATINGS:
        difference_as_fraction_of_rating = (
            abs(estimated_depth_m - possible_depth_rating_m)
            / possible_depth_rating_m
        )

        if difference_as_fraction_of_rating < smallest_difference_found:
            smallest_difference_found = difference_as_fraction_of_rating
            predicted_depth_rating_m = possible_depth_rating_m

    return {
        "serial_number": cal.SerialNumber,
        "predicted_model_in_m": predicted_depth_rating_m,
        "actual_prediction": float(estimated_depth_m),
    }
