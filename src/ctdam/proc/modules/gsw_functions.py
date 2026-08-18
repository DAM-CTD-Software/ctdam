import logging
from ctdam.proc.module import Module
import xarray as xr

logger = logging.getLogger(__name__)


class GSWFunction(Module):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
        default_values: dict = {},
    ) -> xr.Dataset:
        return super().__call__(ds, arguments, default_values)

    def transformation(self) -> bool:
        self.ds.add.teos10_vars()
        try:
            new_parameter = self.ds.gsw.__getitem__(self.name)
        except KeyError:
            logger.error(f"Not a known gsw-function: {self.name}")
            return False
        except TypeError as error:
            logger.error(f"Failed to run gsw-function {self.name}: {error}")
            return False

        try:
            self.ds[new_parameter.attrs["standard_name"]] = new_parameter
        except KeyError:
            self.ds[new_parameter.name] = new_parameter

        return True
