import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any


def _remove_comments(value):
    """Recursive removal of XML comments."""

    if isinstance(value, dict):
        return {
            key: _remove_comments(val)
            for key, val in value.items()
            if key != "#comment"
        }

    if isinstance(value, list):
        return [_remove_comments(item) for item in value]

    return value


@dataclass
class Sensor:
    """Representation of a sensor and its metadata."""

    name: str
    xml_tag: str | None = None
    channel: int | None = None
    serial_number: str | None = None
    calibration_date: str | None = None
    coefficients: dict[str, Any] = field(default_factory=dict)


class SensorArray:
    """Collection of sensor metadata"""

    def __init__(self, sensors: list[Sensor] | None = None, channel_count: int | None = None,):
        self.sensors = sensors or []
        self.channel_count = channel_count

    @classmethod
    def from_sensor_info(cls, sensor_info: list[dict]) -> "SensorArray":
        sensors = []

        metadata_keys = {
            "SensorName",
            "XMLTag",
            "Channel",
            "SerialNumber",
            "CalibrationDate",
        }

        for info in sensor_info:
            coefficients = {
                key: value
                for key, value in info.items()
                if key not in metadata_keys
            }

            sensor = Sensor(
                name=info["SensorName"],
                xml_tag=info.get("XMLTag"),
                channel=int(info["Channel"]),
                serial_number=info.get("SerialNumber"),
                calibration_date=info.get("CalibrationDate"),
                coefficients=_remove_comments(coefficients),
            )

            sensors.append(sensor)

        return cls(sensors)

    @classmethod
    def from_xmlcon(cls, xmlcon) -> "SensorArray":
        """creates a SensorArray from xmlcon file"""
        return cls.from_sensor_info(xmlcon.sensor_info)

    @classmethod
    def from_cnv(cls, cnv):
        sensor_xml = "".join(cnv.sensor_metadata)
        root = ET.fromstring(sensor_xml)
        channel_count = int(root.attrib["count"])
        sensor_info = cnv.sensor_xml_to_flattened_dict(
            sensor_xml
        )
        parsed_channels = {
            int(info["Channel"])
            for info in sensor_info
        }
        not_in_use_count = 0
        for sensor_element in root.findall("sensor"):
            channel = int(sensor_element.attrib["Channel"])
            if channel in parsed_channels:
                continue

            not_in_use_count += 1
            name = (
                "NotInUse"
                if not_in_use_count == 1
                else f"NotInUse{not_in_use_count}"
            )
            sensor_info.append({"Channel": str(channel), "SensorName": name, "XMLTag": "NotInUse"})
        sensor_info.sort(
            key=lambda info: int(info["Channel"])
        )
        config = cls.from_sensor_info(sensor_info)
        config.channel_count = channel_count
        return config

    def to_sensor_info(self) -> list[dict]:
        """convert SensorMetadata back to dictionary format."""

        sensor_info = []
        for sensor in self.sensors:
            info = {
                "Channel": str(sensor.channel),
                "SensorName": sensor.name,
                "XMLTag": sensor.xml_tag,
                "SerialNumber": sensor.serial_number,
                "CalibrationDate": sensor.calibration_date,
                **sensor.coefficients,
            }

            sensor_info.append(info)

        return sensor_info

    def to_xmlcon_sensor_xml(self) -> str:
        """Create an XMLCON-style SensorArray XML block."""

        sensor_array = ET.Element("SensorArray", {"Size": str(len(self.sensors))})
        for sensor in self.sensors:
            if sensor.channel is None:
                raise ValueError(f"No channel available for sensor {sensor.name!r}")

            if sensor.xml_tag is None:
                raise ValueError(f"No XML tag available for sensor {sensor.name!r}")

            sensor_id = sensor.coefficients.get("@SensorID")
            attributes = {"index": str(sensor.channel - 1)}
            if sensor_id is not None:
                attributes["SensorID"] = str(sensor_id)

            sensor_element = ET.SubElement(sensor_array, "Sensor", attributes)
            sensor_data = ET.SubElement(sensor_element, sensor.xml_tag)
            self._dict_to_xml(
                sensor_data,
                {
                    "SerialNumber": sensor.serial_number,
                    "CalibrationDate": sensor.calibration_date,
                    **sensor.coefficients,
                },
            )

        ET.indent(sensor_array)
        return ET.tostring(sensor_array, encoding="unicode")

    def to_cnv_sensor_xml(self) -> str:
        """Create a CNV-style Sensors XML block."""

        channel_count = (
            self.channel_count
            if self.channel_count is not None
            else max(sensor.channel for sensor in self.sensors)
        )

        sensors_element = ET.Element("Sensors", {"count": str(channel_count)})
        sensors_by_channel = {}
        for sensor in self.sensors:
            sensors_by_channel[sensor.channel] = sensor

        for channel in range(1, channel_count + 1):
            sensor_element = ET.SubElement(sensors_element, "sensor", {"Channel": str(channel)})
            sensor = sensors_by_channel.get(channel)
            if sensor is None:
                continue

            if sensor.xml_tag is None:
                raise ValueError(f"No XML tag available for sensor {sensor.name!r}")

            sensor_data = ET.SubElement(sensor_element, sensor.xml_tag)
            self._dict_to_xml(
                sensor_data,
                {
                    "SerialNumber": sensor.serial_number,
                    "CalibrationDate": sensor.calibration_date,
                    **sensor.coefficients,
                },
            )

        ET.indent(sensors_element)

        return ET.tostring(sensors_element, encoding="unicode")

    @staticmethod
    def _dict_to_xml(parent: ET.Element, data: dict) -> None:
        """adds contents of dict recursively to an XML element."""

        for key, value in data.items():
            if value is None:
                continue

            if key.startswith("@"):
                parent.set(key.removeprefix("@"), str(value))

            elif isinstance(value, list):
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        SensorArray._dict_to_xml(child, item)

                    else:
                        child.text = str(item)

            elif isinstance(value, dict):
                child = ET.SubElement(parent, key)
                SensorArray._dict_to_xml(child, value)

            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)

    def __eq__(self, other) -> bool:
        if not isinstance(other, SensorArray):
            return NotImplemented

        return self.sensors == other.sensors

    def __len__(self) -> int:
        return len(self.sensors)

    def __iter__(self):
        return iter(self.sensors)

    def __getitem__(self, index: int) -> Sensor:
        return self.sensors[index]

    def add(self, sensor: Sensor) -> None:
        self.sensors.append(sensor)

    def get(self, identifier: str | int) -> Sensor | None:
        """Return a sensor by name or channel."""
        for sensor in self.sensors:
            if isinstance(identifier, str):
                if sensor.name == identifier:
                    return sensor

            elif isinstance(identifier, int):
                if sensor.channel == identifier:
                    return sensor

        return None
    
    def same_active_sensors(self, other) -> bool:
        """Check whether two sensor arrays have the same active sensors."""
        if not isinstance(other, SensorArray):
            return False

        self_active = {}
        for sensor in self.sensors:
            if sensor.xml_tag != "NotInUse":
                self_active[sensor.channel] = sensor

        other_active = {}
        for sensor in other.sensors:
            if sensor.xml_tag != "NotInUse":
                other_active[sensor.channel] = sensor

        return self_active == other_active
