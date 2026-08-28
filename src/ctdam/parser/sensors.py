from dataclasses import dataclass, field
from typing import Any


@dataclass
class Sensor:
    """Representation of a sensor and its metadata."""

    name: str
    channel: int | None = None
    serial_number: str | None = None
    calibration_date: str | None = None
    coefficients: dict[str, Any] = field(default_factory=dict)


class SensorMetadata:
    """Collection of sensor metadata independent of the source file format."""

    def __init__(self, sensors: list[Sensor] | None = None):
        self.sensors = sensors or []

    def __len__(self) -> int:
        return len(self.sensors)

    def __iter__(self):
        return iter(self.sensors)

    def __getitem__(self, index: int) -> Sensor:
        return self.sensors[index]

    def add(self, sensor: Sensor) -> None:
        self.sensors.append(sensor)

    def get(self, name: str) -> Sensor | None:
        """Return a sensor by name."""
        for sensor in self.sensors:
            if sensor.name == name:
                return sensor
        return None
    
    @classmethod
    def from_xmlcon_sensor_info(
        cls,
        sensor_info: list[dict],
    ) -> "SensorMetadata":
        sensors = []

        for info in sensor_info:
            sensors.append(
                Sensor(
                    name=info["SensorName"],
                    channel=int(info["Channel"]),
                    serial_number=info.get("SerialNumber"),
                    calibration_date=info.get("CalibrationDate"),
                    coefficients={
                        key: value
                        for key, value in info.items()
                        if key
                        not in {
                            "SensorName",
                            "Channel",
                            "SerialNumber",
                            "CalibrationDate",
                        }
                    },
                )
            )

        return cls(sensors)