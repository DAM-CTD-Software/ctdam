import re
from pathlib import Path

from ctdam.parser import DataFile, XMLCONFile


class HexFile(DataFile):
    """
    A representation of a .hex file as used by SeaBird.

    When no corresponding .xmlcon file given, a search algorithm is used
    to determine the matching .xmlcon automatically.

    Parameters
    ----------
    path_to_file: Path | str:
        The path to the file
    path_to_xmlcon: Path | str
        An optional path to the corresponding .xmlcon file
    """

    def __init__(
        self,
        path_to_file: Path | str,
        path_to_xmlcon: Path | str = "",
        *args,
        **kwargs,
    ):
        # force loading only metadata
        super().__init__(path_to_file, True)
        self.xmlcon = self.get_corresponding_xmlcon(path_to_xmlcon)

    def get_corresponding_xmlcon(
        self,
        path_to_xmlcon: Path | str = "",
    ) -> XMLCONFile | None:
        """
        Finds the best matching .xmlcon file inside the same directory.

        The logics works as follows:

        - if an .xmlcon of the same name exists, take that
        - else, find all .xmlcons of the same cruise inside the given
          directory and use the one used by the previous .hex file, sorted
          by file name.

        Parameters
        ----------
        path_to_xmlcon: Path | str:
            A path to an .xmlcon file, if not existent, use the search algorithm
        """
        # xmlcon path given, test and use it
        if isinstance(path_to_xmlcon, str):
            if path_to_xmlcon:
                return XMLCONFile(path_to_xmlcon)
        else:
            if path_to_xmlcon.exists():
                return XMLCONFile(path_to_xmlcon)
        # no xmlcon path, lets find one in the same dir
        # get all xmlcons in the dir
        # first, try the very same name
        same_name_xmlcon = self.path_to_file.with_suffix(".XMLCON")
        if same_name_xmlcon.exists():
            return XMLCONFile(same_name_xmlcon)

        # otherwise, take the xmlcon of the previous hex file, sorted by name
        # use either the extracted cruise name or the first five letters for
        # searching for xmlcons of the same cruise
        if self.cruise:
            prefix = (
                re.split(r"[_\-\/]", self.cruise.lower())[0]
                if any(x in self.cruise.lower() for x in ["_", "-", "/"])
                else self.cruise.lower()
            )
        else:
            prefix = self.file_name.lower()[:5]
        xmlcons = [
            xmlcon
            for xmlcon in sorted(
                self.file_dir.glob("*.XMLCON", case_sensitive=False)
            )
            if xmlcon.stem.lower().startswith(prefix)
        ]
        if not xmlcons:
            return None

        # looking back and using xmlcon from the previous hex file
        all_hexes = [
            hex
            for hex in sorted(
                self.file_dir.glob("*.hex", case_sensitive=False)
            )
            if hex.stem.lower().startswith(prefix)
        ]
        index = all_hexes.index(self.path_to_file)
        previous_hexes = all_hexes[:index]
        if previous_hexes:
            return HexFile(previous_hexes[-1]).xmlcon

        return XMLCONFile(xmlcons[0])
