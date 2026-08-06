import logging

import xarray as xr

from ctdam.proc.module import Module

logger = logging.getLogger(__name__)


class AirPressureCorrection(Module):
    """
    Corrects water pressure by the given air pressure.

    Parameters
    ----------
    input: Path | str | CTDData | pd.DataFrame | np.ndarray
        The input CTD data
    arguments: dict
        The argument to run the module with
    output: str
        The output type
    output_name: str | None
        The output name
    """

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
    ) -> xr.Dataset:
        self.name = "airpressure"
        return super().__call__(ds, arguments)

    def transformation(self) -> bool:
        """
        Base logic to correct pressure.

        Returns
        -------
        A boolean to indicate the success of the operation.
        """
        try:
            ctd_pressure = self.ds["pressure"].data
            air_pressure = float(
                self.ds.meta.custom["Air_Pressure"].replace("hPa", "")
            )
        except (KeyError, ValueError):
            return False

        water_pressure = 1024
        pressure_diff = round((air_pressure - water_pressure) / 100, 4)
        self.ds["pressure"].data = ctd_pressure - pressure_diff
        self.arguments["pressure_diff"] = f"{str(-pressure_diff)} dbar"

        return True
