from pathlib import Path

import pandas as pd


class GEOMARCTDFile:
    """
    A parser to read .ctd files created by the GEOMAR ctdam.proc software.

    Goes through the file line by line and sorts the individual lines in
    corresponding lists. That way, data and different types of metadata are
    structured on a basic level.
    In general, this parser is meant to stick close to the way the Seabird-
    Parsers are written.
    """

    def __init__(
        self,
        path_to_file: Path | str,
        only_header: bool = False,
        create_dataframe: bool = True,
    ):
        self.path_to_file = Path(path_to_file)
        self.only_header = only_header
        self.raw_input = []
        self.metadata = {}
        self.history = []
        self.comment = []
        self.data_header = []
        self.raw_data = []
        self.read_file()
        if create_dataframe:
            self.create_dataframe()

    def __str__(self) -> str:
        return "/n".join(self.raw_data)

    def __repr__(self) -> str:
        return str(self.path_to_file.absolute())

    def __eq__(self, other) -> bool:
        return self.raw_data == other.raw_data

    def read_file(self):
        with open(self.path_to_file, "r") as file:
            past_header = False
            for line in file:
                self.raw_input.append(line)
                if line.startswith("History"):
                    self.history.append(
                        line.removeprefix("History  = # GEOMAR").strip()
                    )
                elif line.startswith("Comment"):
                    self.comment.append(
                        line.removeprefix("Comment  =").strip()
                    )
                elif line.startswith("Columns"):
                    self.data_header = [
                        column.removeprefix("Columns  =").strip()
                        for column in line.split(":")
                    ]
                    past_header = True
                    if self.only_header:
                        break
                else:
                    if not past_header:
                        try:
                            key, value = line.split("=")
                        except ValueError:
                            key = line
                            value = ""
                        self.metadata[key.strip()] = value.strip()
                    else:
                        self.raw_data.append(line)

    def create_dataframe(self):
        self.df = pd.DataFrame(
            [row.split() for row in self.raw_data],
            dtype=float,
            columns=self.data_header,
        )
