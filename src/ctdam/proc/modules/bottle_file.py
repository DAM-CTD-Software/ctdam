import xarray as xr

from ctdam.proc.module import Module


class BottleFile(Module):
    """
    Creates BottleFiles.

    Parameters
    ----------
    input: xr.Dataset
        The input CTD data
    arguments: dict
        The argument to run the module with
    """

    def __call__(
        self,
        ds: xr.Dataset,
        arguments: dict = {},
    ) -> xr.Dataset:
        return super().__call__(ds, arguments)

    def transformation(self) -> bool:
        self.ds.export.to_btl(**self.arguments)

        return True
