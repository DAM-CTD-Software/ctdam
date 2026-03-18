import logging
from collections import UserDict
from pathlib import Path

from tomlkit import dumps, table
from tomlkit.toml_file import TOMLFile

logger = logging.getLogger(__name__)


class Configuration(UserDict):
    """
    The internal representation of the .toml configuration files, that store
    the ctdam.proc information.

    Allows the interaction with these config files to be pretty much equivalent
    to a basic python dictionary.
    """

    def __init__(self, path: Path | str, data: dict | None = None):
        self.path = Path(path)
        if data is None:
            self.data = TOMLFile(path).read()
        else:
            # toml cannot handle Path objects
            for key, value in data.items():
                if isinstance(value, Path):
                    data[key] = str(value)
            self.data = data

    def __str__(self):
        return str(self.path)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, keys, value):
        self.modify([keys], value)

    def write(self, path_to_write=None):
        """
        Writes the ctdam.proc information to a file.

        Parameters
        ----------
        path_to_write :
            The path to write the file to. If none given, the input path will
            be used.
             (Default value = None)
        """
        output_path = self.path
        if path_to_write:
            output_path = path_to_write
        try:
            with open(output_path, "w") as file:
                file.write(dumps(self.data))
        except IOError as error:
            logger.error(f"Could not write configuration file: {error}")

    def modify(self, key, value):
        """
        Allows the access and modification of nested data points.

        Parameters
        ----------
        key :

        value :


        Returns
        -------

        """
        # TODO: allow addition to a specified position
        try:
            if isinstance(key, list):
                current_section = self.data
                for position in key[:-1]:
                    current_section = current_section.get(position, table())

                current_section[key[-1]] = value
            else:
                self.data.update({key: value})
        except ValueError as error:
            logger.error(f"Value modification failed: {error}")


class IncompleteProcedureConfig(Exception):
    """An exception to indicate misformed configuration files."""

    def __init__(self, message):
        super().__init__(message)
