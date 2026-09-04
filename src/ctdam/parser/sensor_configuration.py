from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any


def _to_int(value):
    if value is None:
        return None

    return int(value)

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

    def __init__(
        self,
        sensors: list[Sensor] | None = None,
        channel_count: int | None = None,
    ):
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
        """Creates a SensorArray from an XMLCON file."""

        sensor_array = xmlcon.data[
            "SBE_InstrumentConfiguration"
        ]["Instrument"]["SensorArray"]

        channel_count = int(sensor_array["@Size"])

        config = cls.from_sensor_info(
            xmlcon.sensor_info
        )

        config.channel_count = channel_count

        return config

    @classmethod
    def from_cnv(cls, cnv):
        sensor_xml = "".join(cnv.sensor_metadata)
        root = ET.fromstring(sensor_xml)
        channel_count = int(root.attrib["count"])
        sensor_info = cnv.sensor_xml_to_flattened_dict(sensor_xml)
        parsed_channels = {int(info["Channel"]) for info in sensor_info}
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
            sensor_info.append(
                {
                    "Channel": str(channel),
                    "SensorName": name,
                    "XMLTag": "NotInUse",
                }
            )
        sensor_info.sort(key=lambda info: int(info["Channel"]))
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

        sensor_array = ET.Element(
            "SensorArray", {"Size": str(len(self.sensors))}
        )
        for sensor in self.sensors:
            if sensor.channel is None:
                raise ValueError(
                    f"No channel available for sensor {sensor.name!r}"
                )

            if sensor.xml_tag is None:
                raise ValueError(
                    f"No XML tag available for sensor {sensor.name!r}"
                )

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
            sensor_element = ET.SubElement(
                sensors_element, "sensor", {"Channel": str(channel)}
            )
            sensor = sensors_by_channel.get(channel)
            if sensor is None:
                continue

            if sensor.xml_tag is None:
                raise ValueError(
                    f"No XML tag available for sensor {sensor.name!r}"
                )

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

@dataclass
class InstrumentConfiguration:
    name: str | None = None
    frequency_channels_suppressed: int | None = None
    voltage_words_suppressed: int | None = None
    computer_interface: int | None = None
    deck_unit_version: int | None = None
    scans_to_average: int | None = None
    surface_par_voltage_added: int | None = None
    scan_time_added: int | None = None
    nmea_position_data_added: int | None = None
    nmea_depth_data_added: int | None = None
    nmea_time_added: int | None = None
    nmea_device_connected_to_pc: int | None = None

    @classmethod
    def from_xmlcon(cls, xmlcon):
        instrument = xmlcon.data[
            "SBE_InstrumentConfiguration"
        ]["Instrument"]

        return cls(
            name=instrument.get("Name"),
            frequency_channels_suppressed=_to_int(
                instrument.get("FrequencyChannelsSuppressed")
            ),
            voltage_words_suppressed=_to_int(
                instrument.get("VoltageWordsSuppressed")
            ),
            computer_interface=_to_int(
                instrument.get("ComputerInterface")
            ),
            deck_unit_version=_to_int(
                instrument.get("DeckUnitVersion")
            ),
            scans_to_average=_to_int(
                instrument.get("ScansToAverage")
            ),
            surface_par_voltage_added=_to_int(
                instrument.get("SurfaceParVoltageAdded")
            ),
            scan_time_added=_to_int(
                instrument.get("ScanTimeAdded")
            ),
            nmea_position_data_added=_to_int(
                instrument.get("NmeaPositionDataAdded")
            ),
            nmea_depth_data_added=_to_int(
                instrument.get("NmeaDepthDataAdded")
            ),
            nmea_time_added=_to_int(
                instrument.get("NmeaTimeAdded")
            ),
            nmea_device_connected_to_pc=_to_int(
                instrument.get("NmeaDeviceConnectedToPC")
            ),
        )

    @classmethod
    def from_cnv(cls, cnv):
        config = cls()

        for line in cnv.instrument_metadata:
            line = line.strip()

            if line.startswith(
                "Number of Scans Averaged by the Deck Unit"
            ):
                value = line.split("=", 1)[1].strip()
                config.scans_to_average = int(value)

            elif line == "surface PAR voltage added to scan":
                config.surface_par_voltage_added = 1

            elif line == "Append System Time to Every Scan":
                config.scan_time_added = 1

            elif line.startswith("Store Lat/Lon Data"):
                if "Append to Every Scan" in line:
                    config.nmea_position_data_added = 1

        return config
    

@dataclass
class CTDConfiguration:
    instrument: InstrumentConfiguration
    sensors: SensorArray

    @classmethod
    def from_xmlcon(cls, xmlcon) -> "CTDConfiguration":
        return cls(
            instrument=InstrumentConfiguration.from_xmlcon(
                xmlcon
            ),
            sensors=SensorArray.from_xmlcon(
                xmlcon
            ),
        )

    @classmethod
    def from_cnv(cls, cnv):
        return cls(
            instrument=InstrumentConfiguration.from_cnv(
                cnv
            ),
            sensors=SensorArray.from_cnv(
                cnv
            ),
        )
    

    def to_xmlcon(
        self,
        output_path: Path | str,
    ) -> None:
        root = ET.Element(
            "SBE_InstrumentConfiguration"
        )

        instrument_element = ET.SubElement(
            root,
            "Instrument"
        )

        self._add_instrument_xml(
            instrument_element
        )

        sensor_array = ET.fromstring(
            self.sensors.to_xmlcon_sensor_xml()
        )

        instrument_element.append(
            sensor_array
        )

        tree = ET.ElementTree(root)
        ET.indent(tree)

        tree.write(
            output_path,
            encoding="utf-8",
            xml_declaration=True,
        ) 
    

    def _add_instrument_xml(
        self,
        parent: ET.Element,
    ) -> None:
        values = {
            "Name": self.instrument.name,
            "FrequencyChannelsSuppressed":
                self.instrument.frequency_channels_suppressed,
            "VoltageWordsSuppressed":
                self.instrument.voltage_words_suppressed,
            "ComputerInterface":
                self.instrument.computer_interface,
            "DeckUnitVersion":
                self.instrument.deck_unit_version,
            "ScansToAverage":
                self.instrument.scans_to_average,
            "SurfaceParVoltageAdded":
                self.instrument.surface_par_voltage_added,
            "ScanTimeAdded":
                self.instrument.scan_time_added,
            "NmeaPositionDataAdded":
                self.instrument.nmea_position_data_added,
            "NmeaDepthDataAdded":
                self.instrument.nmea_depth_data_added,
            "NmeaTimeAdded":
                self.instrument.nmea_time_added,
            "NmeaDeviceConnectedToPC":
                self.instrument.nmea_device_connected_to_pc,
        }

        for tag, value in values.items():
            if value is None:
                continue

            element = ET.SubElement(
                parent,
                tag
            )

            element.text = str(value)