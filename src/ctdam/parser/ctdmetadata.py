from pathlib import Path

from ctdam.parser.cnvfile import CnvFile
from ctdam.parser.hexfile import HexFile


class CTDMetadata:
    def __init__(
        self,
        device_info: list = [],
        custom_metadata: dict = {},
        associated_files: dict = {},
        metadata_source: CnvFile | HexFile | Path | str = "",
    ) -> None:
        if isinstance(metadata_source, (CnvFile, HexFile)):
            self.metadata_source = metadata_source
            self.device_info = metadata_source.sbe9_data
            self.custom = metadata_source.metadata
        else:
            self.metadata_source = self.path_to_file = Path(metadata_source)
            self.device_info = device_info
            self.custom = custom_metadata
            self.associated_files = associated_files

    def __getattr__(self, name: str, /):
        metadata_source = self.__dict__.get("metadata_source")

        if metadata_source is not None and hasattr(metadata_source, name):
            return getattr(metadata_source, name)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(dir(self.metadata_source)))
