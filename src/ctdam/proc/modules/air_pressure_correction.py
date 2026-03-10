import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ctdam.parser.ctddata import CTDData
from ctdam.proc.module import ArrayModule

logger = logging.getLogger(__name__)


class AirPressureCorrection(ArrayModule):
    """
    Corrects water pressure by the given air pressure.
    """

    def __call__(
        self,
        input: Path | str | CTDData | pd.DataFrame | np.ndarray,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        **kwargs,
    ) -> None | CTDData | pd.DataFrame | np.ndarray:
        return super().__call__(input, arguments, output, output_name)

    def transformation(self) -> bool:
        """
        Base logic to correct pressure.
        """
        try:
            prDM = self.ctd_data["prDM"].data
            air_pressure = float(
                self.ctd_data.metadata["Air_Pressure"].replace("hPa", "")
            )
        except (KeyError, ValueError):
            return False

        water_pressure = 1024
        pressure_diff = round((air_pressure - water_pressure) / 100, 4)
        self.ctd_data["prDM"].data = prDM - pressure_diff
        self.arguments["pressure_diff"] = f"{str(-pressure_diff)} dbar"

        return True
