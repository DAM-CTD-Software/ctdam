import logging

from ctdam.conv.cast_borders import get_cast_borders
from ctdam.exceptions import MissingParameterError
from ctdam.proc.module import Module

logger = logging.getLogger(__name__)


class CastBorders(Module):
    """
    Detect cast borders from pressure data.
    """

    synonyms = ["cast_borders", "cast_limits", "limits"]

    def __init__(self) -> None:
        super().__init__()

    def transformation(self) -> bool:
        # check, if cast borders already cut
        if [
            module
            for module in self.ds.meta.provenance.keys()
            if module in self.names
        ]:
            logger.warning("CastBorders already cut.")
            return False
        self.check_whether_working_on_binned_data()
        if not self._check_parameter_existence("pressure"):
            raise MissingParameterError(self.name, "pressure")

        arguments = self.arguments.copy()

        pressure_parameter = arguments.pop("pressure_parameter", "pressure")
        crop = arguments.pop("crop", True)

        pressure = self.ds[pressure_parameter].data

        borders = get_cast_borders(
            pressure=pressure,
            **arguments,
        )

        self.cast_borders = borders

        self.arguments["down_start"] = borders["down_start"]
        self.arguments["down_end"] = borders["down_end"]

        if "up_start" in borders:
            self.arguments["up_start"] = borders["up_start"]
        if "up_end" in borders:
            self.arguments["up_end"] = borders["up_end"]

        if crop:
            self._crop_to_downcast(
                borders["down_start"],
                borders["down_end"] + 1,
            )

        return True

    def _crop_to_downcast(self, start: int, end: int) -> None:
        self.ds = self.ds.isel(scan=slice(start, end))

        self.flags = self.flags[start:end]
