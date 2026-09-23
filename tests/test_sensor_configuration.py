import json

from conftest import test_hex

from ctdam.parser.read_ctd_data import read_cnv, read_hex
from ctdam.parser.sensor_configuration import sensor_json_metadata_to_cnv_xml


def test_hex_sensor_metadata_survives_cnv_export(tmp_path):
    ds = read_hex(test_hex)
    output = tmp_path / "from_hex.cnv"

    ds.export.to_cnv(output)
    sensors = json.loads(read_cnv(output).meta.sensors)

    assert sensors[0]["SerialNumber"] == "5492"
    assert sensors[0]["G"] == "4.33459406e-003"


def test_empty_sensor_json_metadata_to_cnv_xml():
    assert sensor_json_metadata_to_cnv_xml("[]") == ""


def test_sensor_json_metadata_to_cnv_xml():
    metadata = json.dumps(
        [
            {
                "Channel": "1",
                "SensorName": "Temperature",
                "XMLTag": "TemperatureSensor",
                "SerialNumber": "5492",
            }
        ]
    )

    xml = sensor_json_metadata_to_cnv_xml(metadata)

    assert '<Sensors count="1">' in xml
    assert "<TemperatureSensor>" in xml
    assert "<SerialNumber>5492</SerialNumber>" in xml
    assert "<CalibrationDate></CalibrationDate>" in xml
