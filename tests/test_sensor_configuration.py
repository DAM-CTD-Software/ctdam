import json

import pytest
from conftest import test_cnv, test_hex

from ctdam.parser.read_ctd_data import read_cnv
from ctdam.parser.seabird_data_files import CnvFile
from ctdam.parser.sensor_configuration import SensorArray
from ctdam.parser.xmlfiles import XMLCONFile


@pytest.fixture
def sensors():
    return SensorArray.from_cnv(CnvFile(test_cnv))


@pytest.fixture
def xmlcon_sensors():
    return SensorArray.from_xmlcon(XMLCONFile(test_hex.with_suffix(".XMLCON")))


def test_load_xmlcon_sensors(xmlcon_sensors):
    assert len(xmlcon_sensors) == 15
    assert xmlcon_sensors.channel_count == 15
    assert [sensor.channel for sensor in xmlcon_sensors] == list(range(1, 16))

    temperature = xmlcon_sensors[0]
    assert temperature.name == "Temperature"
    assert temperature.xml_tag == "TemperatureSensor"
    assert temperature.serial_number == "5492"
    assert temperature.calibration_date == "2023-12-18"
    assert temperature.coefficients["G"] == "4.33459406e-003"


def test_sensor_metadata_json_round_trip(xmlcon_sensors):
    stored = json.dumps(xmlcon_sensors.to_sensor_info())
    restored = SensorArray.from_sensor_info(json.loads(stored))

    assert restored == xmlcon_sensors


def test_sensor_metadata_cnv_round_trip(sensors, tmp_path):
    ds = read_cnv(test_cnv)
    output = tmp_path / "round_trip.cnv"

    ds.export.to_cnv(output)
    restored = SensorArray.from_cnv(CnvFile(output))

    assert restored.same_active_sensors(sensors)
    assert restored.channel_count == sensors.channel_count
