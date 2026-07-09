from ctdam.conv.cast_borders import get_cast_borders
from ctdam.proc.module import ArrayModule


class CastBorders(ArrayModule):
    """
    Detect cast borders from pressure data.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "cast_borders"

    def transformation(self) -> bool:
        self.check_whether_working_on_binned_data()

        arguments = self.arguments.copy()

        pressure_parameter = arguments.pop("pressure_parameter", "prDM")
        crop = arguments.pop("crop", False)

        pressure = self.ctd_data[pressure_parameter].data

        borders = get_cast_borders(
            pressure=pressure,
            **arguments,
        )

        self.cast_borders = borders
        self.ctd_data.cast_borders = borders

        self.arguments["pressure_parameter"] = pressure_parameter
        self.arguments["crop"] = crop
        self.arguments["down_start"] = borders["down_start"]
        self.arguments["down_end"] = borders["down_end"]

        if "up_start" in borders:
            self.arguments["up_start"] = borders["up_start"]
        if "up_end" in borders:
            self.arguments["up_end"] = borders["up_end"]

        if crop:
            self._crop_to_downcast(
                start=borders["down_start"],
                end=borders["down_end"],
            )

        return True

    def _crop_to_downcast(self, start: int, end: int) -> None:
        for parameter in self.ctd_data.parameters.values():
            parameter.data = parameter.data[start:end]
