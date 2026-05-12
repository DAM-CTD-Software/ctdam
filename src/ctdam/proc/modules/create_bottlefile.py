import importlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ctdam.exceptions import BinnedDataError, InvalidArgumentCombination
from ctdam.parser import BottleLogFile, CnvFile
from ctdam.parser.ctddata import CTDData

logger = logging.getLogger(__name__)


class OwnBtlFile:
    def __init__(
        self,
        ctd_data: CTDData | None = None,
        blf: BottleLogFile | None = None,
        path_to_file: Path | str = "",
    ):
        if ctd_data and blf:
            self.ctd_data = ctd_data
            self.blf = blf
            self.data = self.create_btl()
        elif path_to_file:
            # TODO: use DataFile variables and methods to read an existing file
            pass
        else:
            raise InvalidArgumentCombination

    def create_btl(self) -> str:
        req_parameters = [
            "prDM",
            "t090C",
            "t190C",
            "c0mS/cm",
            "c1mS/cm",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "sal00",
            "sal11",
            "par",
            "spar",
            "flECO-AFL",
            "turbWETntu0",
        ]

        data_averages = self._get_averages()
        ctd_data_header = self.ctd_data.create_header()
        timestamp = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
        ctd_data_header.insert(
            -2,
            f"# create_bottlefile_metainfo = {timestamp}, ctdam python package, v{importlib.metadata.version('ctdam')}\n",
        )
        btl_file = "".join(
            [
                line
                for line in ctd_data_header
                if not line.startswith(
                    ("# name", "# span", "# nquan", "# nvalues", "# units")
                )
            ]
        )

        btl_base_id = int(self.ctd_data.metadata["WsStartID"]) - 1

        line = add_whitespace("Btl_Posn")
        line += add_whitespace("Btl_ID")
        line += add_whitespace("Datetime", 22)
        for i in range(len(req_parameters)):
            line += add_whitespace(req_parameters[i])
        btl_file += line + "\n"

        for i in range(len(self.blf.data_list)):
            line = ""

            line += add_whitespace(self.blf.data_list[i][0][1])
            line += add_whitespace(self.blf.data_list[i][0][1] + btl_base_id)
            line += add_whitespace(self.blf.data_list[i][1], 22)

            for j in range(len(data_averages[0])):
                line += add_whitespace(data_averages[i, j])

            if i == len(self.blf.data_list) - 1:
                btl_file += line
                continue

            btl_file += line + "\n"

        return btl_file

    def _get_averages(self) -> np.ndarray:
        cnv_data = self.ctd_data.parameters.get_full_data_array().astype(float)
        par_index_list = self._get_parameters()
        averages = np.array(
            [
                [None for x in range(len(par_index_list))]
                for y in range(len(self.blf.data_list))
            ]
        )

        for i in range(len(self.blf.data_list)):
            for j in range(len(par_index_list)):
                start_index = self.blf.data_list[i][2][0]
                end_index = self.blf.data_list[i][2][1]
                averages[i, j] = np.average(
                    cnv_data[start_index:end_index, j]
                ).round(4)

        return averages

    def _get_parameters(self) -> list:
        """gets the Indices of the required parameterts from the cnv

        Parameters
        ----------
        List of Parameters of the cnv

        Returns
        -------
        list of corresponding indices

        """
        req_parameters = [
            "prDM",
            "t090C",
            "t190C",
            "c0mS/cm",
            "c1mS/cm",
            "sbox0Mm/Kg",
            "sbox1Mm/Kg",
            "sal00",
            "sal11",
            "par",
            "spar",
            "flECO-AFL",
            "turbWETntu0",
        ]
        parameter_list = self.ctd_data.get_parameter_list()
        par_shortname_list = [x.name for x in parameter_list]
        par_index_list = []
        for i in range(len(req_parameters)):
            par_index_list.append(par_shortname_list.index(req_parameters[i]))
        return par_index_list


def _check_input(input, type):
    if type == BottleLogFile:
        if isinstance(input, BottleLogFile):
            return input
        elif isinstance(input, str):
            if input and Path(input).exists():
                return type(input)
            else:
                return ""
        elif isinstance(input, Path):
            if input is not Path(".") and input.exists():
                return type(input)
            else:
                return ""
        else:
            raise ValueError(
                f"Argument of {type(input)} cannot be used for {type}"
            )
    elif type == CTDData:
        if isinstance(input, CTDData):
            return input
        elif isinstance(input, str):
            if input:
                return CnvFile(input).to_ctd_data()
            else:
                return ""
        elif isinstance(input, Path):
            if input is not Path("."):
                return CnvFile(input).to_ctd_data()
            else:
                return ""
        else:
            raise ValueError(
                f"Argument of {type(input)} cannot be used for {type}"
            )
    else:
        raise ValueError(
            f"Argument of {type(input)} cannot be used for {type}"
        )


def create_bottle_file(
    input: CTDData | Path | str = "",
    arguments: dict = {},
    output_name: Path | str = "",
    original_input_path: Path | str = "",
    **kwargs,
) -> OwnBtlFile | CTDData:
    """
    Creates a custom bottle file, given a .cnv and .bl file.

    The resulting file strongly adheres to the format of a regular .btl file.
    Specifically, the header is the same, only the data table features a
    different format. Its a 11-character wide tsv, as a cnv data table. In
    contrast to a .btl, only average values are used.

    In general, this custom bottle file (.obtl) can be generated at any time
    during the CTD processing. This improves over the standard Sea-Bird variant
    that allows this only during .cnv creation using Datcnv. With the .obtl
    file one can ensure the very same data quality from a .cnv file inside a
    bottle file.
    """
    ctd_data = _check_input(input, CTDData)
    try:
        blf = _check_input(arguments["bl"], BottleLogFile)
    except KeyError:
        if original_input_path:
            original_input_path = Path(original_input_path)
        else:
            original_input_path = ctd_data.path_to_file
        if original_input_path.exists():
            blf = _check_input(
                original_input_path.with_suffix(".bl"), BottleLogFile
            )
        else:
            blf = None

    if ctd_data:
        if not blf:
            try:
                blf = BottleLogFile(ctd_data.path_to_file.with_suffix(".bl"))
            except (FileNotFoundError, ValueError, TypeError):
                logger.info(
                    f"Could not find a corresponding .bl file to the cnv {ctd_data.metadata_source.path_to_file}"
                )
                return ctd_data
    else:
        if blf:
            try:
                ctd_data = CnvFile(
                    blf.path_to_file.with_suffix(".cnv")
                ).to_ctd_data()
            except (FileNotFoundError, ValueError, TypeError):
                raise ValueError(
                    f"Could not find a corresponding .cnv file to the bl {blf.path_to_file}"
                )
        else:
            raise InvalidArgumentCombination

    if ctd_data.binned:
        raise BinnedDataError(
            file_name=ctd_data.file_name,
            step_name="create_bottle_file",
        )
    btl = OwnBtlFile(ctd_data, blf)

    # usually write btl to disk, skip this only when explicitely stated
    if "write_btl" in arguments and not arguments["write_btl"]:
        pass
    else:
        if not output_name:
            output_name = ctd_data.path_to_file
        if "file_suffix" in arguments:
            stem = Path(output_name).stem
            output_name = Path(output_name).with_stem(
                stem + arguments["file_suffix"]
            )
        with open(Path(output_name).with_suffix(".obtl"), "w") as file:
            file.write(btl.data)

    return btl


def add_whitespace(data, space: int = 11):
    return (space - len(str(data))) * " " + str(data)
