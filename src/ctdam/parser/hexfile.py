import re
from pathlib import Path

from ctdam.parser import DataFile, XMLCONFile


class HexFile(DataFile):
    """
    A representation of a .hex file as used by Sea-Bird.

    When no corresponding .xmlcon file is given, a search algorithm is used
    to determine the matching .xmlcon automatically.

    Parameters
    ----------
    path_to_file : Path | str
        Path to the HEX file.
    path_to_xmlcon : Path | str
        Optional path to the corresponding XMLCON file.
    """

    def __init__(
        self,
        path_to_file: Path | str,
        path_to_xmlcon: Path | str = "",
        *args,
        **kwargs,
    ):
        # HEX data is not read as a normal text data table here.
        # Only its metadata is loaded by DataFile.
        super().__init__(path_to_file, True)

        self.xmlcon = self.get_corresponding_xmlcon(path_to_xmlcon)

    def get_corresponding_xmlcon(
        self,
        path_to_xmlcon: Path | str = "",
    ) -> XMLCONFile | None:
        """
        Find the XMLCON file corresponding to this HEX file.

        The search order is:

        1. Use an explicitly provided XMLCON path.
        2. Find an XMLCON with the same filename stem.
        3. Reuse the XMLCON associated with the preceding HEX file from
           the same cruise.
        4. Use the first matching XMLCON from the same cruise.
        5. Return None when no matching XMLCON exists.

        Parameters
        ----------
        path_to_xmlcon : Path | str
            Optional path to a specific XMLCON file.

        Returns
        -------
        XMLCONFile | None
            Parsed XMLCON file, or None if no suitable file was found.
        """
        # 1. Use an explicitly supplied XMLCON path.
        if path_to_xmlcon:
            explicit_xmlcon = Path(path_to_xmlcon)

            if explicit_xmlcon.is_file():
                return XMLCONFile(explicit_xmlcon)

        # Read the directory once so it does not need to be scanned repeatedly.
        try:
            directory_files = sorted(self.file_dir.iterdir())
        except OSError:
            return None

        # 2. Prefer an XMLCON whose filename stem exactly matches the HEX stem.
        #
        # casefold() makes this work with:
        # cast.XMLCON
        # cast.xmlcon
        # cast.XmlCon
        same_name_xmlcon = next(
            (
                path
                for path in directory_files
                if path.is_file()
                and path.suffix.casefold() == ".xmlcon"
                and path.stem.casefold() == self.path_to_file.stem.casefold()
            ),
            None,
        )

        if same_name_xmlcon is not None:
            return XMLCONFile(same_name_xmlcon)

        # Determine the filename prefix used to identify files belonging
        # to the same cruise.
        if self.cruise:
            cruise_name = self.cruise.casefold()

            prefix = (
                re.split(r"[_/-]", cruise_name)[0]
                if any(
                    separator in cruise_name for separator in ("_", "-", "/")
                )
                else cruise_name
            )
        else:
            # Fall back to the first five characters of the filename.
            prefix = self.file_name.casefold()[:5]

        # Find all XMLCON files matching the cruise prefix.
        xmlcons = [
            path
            for path in directory_files
            if path.is_file()
            and path.suffix.casefold() == ".xmlcon"
            and path.stem.casefold().startswith(prefix)
        ]

        if not xmlcons:
            return None

        # Find all HEX files matching the same cruise prefix.
        all_hexes = [
            path
            for path in directory_files
            if path.is_file()
            and path.suffix.casefold() == ".hex"
            and path.stem.casefold().startswith(prefix)
        ]

        current_path = self.path_to_file.resolve()

        # Find the current HEX file in the sorted list.
        try:
            current_index = next(
                index
                for index, hex_file in enumerate(all_hexes)
                if hex_file.resolve() == current_path
            )
        except StopIteration:
            # Defensive fallback: the current file should normally be present.
            return XMLCONFile(xmlcons[0])

        # 3. Look for the XMLCON associated with the previous HEX file.
        previous_hexes = all_hexes[:current_index]

        if previous_hexes:
            previous_hex = HexFile(previous_hexes[-1])

            if previous_hex.xmlcon is not None:
                return previous_hex.xmlcon

        # 4. No previous configuration was available, so use the first
        # matching XMLCON.
        return XMLCONFile(xmlcons[0])
