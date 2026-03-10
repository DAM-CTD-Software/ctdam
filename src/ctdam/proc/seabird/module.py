import difflib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessingModule:
    """
    Collects the information necesssary to run a Seabird Processing module.


    A module needs paths to an exe, to a psa and to an input file. On top of
    that, a few non-mandatory settings can be specified, like the output file
    path or a new file name. The collected information is then used to feed a
    ProcessingStep.

    Parameters
    ----------

    name: str:
        The name of the module. Is used to find corresponding files.

    exe_dir: Path | str:
        The path to the executable directory. Is used if no direct path to any
        executable is given.

    psa_dir: Path | str:
        The path to the configuration directory. Is used if no direct path to
        any config file is given.

    exe_path: Path | str | None:
        The path to the modules executable.

    psa_path: Path | str | None:
        The path to the modules configuration file.

    new_file_suffix: str:
        An optional suffix to append to the output file name.
    """

    def __init__(
        self,
        name: str,
        exe_dir: Path | str,
        psa_dir: Path | str,
        exe_path: Path | str | None = None,
        psa_path: Path | str | None = None,
        new_file_suffix: str = "",
    ):
        # allowing the usage of multiple modules of the same name inside of one
        # routine/procedure
        self.name = name.lower().split("_")[0]
        if self.name == "airpressure":
            self.psa = self.check_input_path(psa_path, "par", Path(psa_dir))
        elif self.name == "iow_btl_id":
            self.psa = None
        # w_filter will be split also and needs to be handled individually
        elif self.name == "w":
            self.name = "w_filter"
            self.psa = self.check_input_path(psa_path, "psa", Path(psa_dir))
        else:
            self.psa = self.check_input_path(psa_path, "psa", Path(psa_dir))
        self.exe = self.check_input_path(exe_path, "exe", Path(exe_dir))
        self.new_file_suffix = new_file_suffix

    def __str__(self) -> str:
        return self.name

    def check_input_path(
        self, input_path: Path | str | None, file_type: str, directory: Path
    ) -> Path | None:
        """
        Tests the given exe or config path and runs find_file upon failure.

        The path needs to be absolute and present. This method basically
        performs all the logic to retrieve an executable and configuration path
        with the help of find_file.

        Parameters
        ----------
        input_path: Path | str | None :
            The path to the file that needs testing. If none given, directly
            start searching a default one by calling find_file.

        file_type: str :
            The type of the file to check on. Either 'exe' or some form of
            configuration file, usually 'psa'.

        directory: Path :
            The directory to search for, upon failure.
        """
        if isinstance(input_path, Path | str):
            input_path = Path(input_path)
        else:
            return self.find_file(file_type, directory)
        if input_path.is_absolute():
            output_path = input_path
        else:
            output_path = directory.joinpath(input_path)
        if output_path.exists():
            return output_path
        else:
            return self.find_file(file_type, directory)

    def find_file(self, file_type: str, parent_dir: Path) -> Path | None:
        """
        Finds the closest matching file of a certain type inside of a given
        directory.

        Parameters
        ----------
        file_type: str :
            The file type to search for.

        parent_dir: Path :
            The directory to search in.
        """
        file_type = file_type.lstrip(".")
        try:
            best_match = difflib.get_close_matches(
                word=f"{self.name}.{file_type}",
                possibilities=[path.name for path in parent_dir.iterdir()],
                n=1,
            )
        except FileNotFoundError as error:
            logger.error(
                f'The {file_type} directory "{parent_dir}" could not be found: {error}'
            )
        else:
            try:
                return parent_dir.joinpath(best_match[0])
            except IndexError as error:
                logger.error(
                    f"No exe or config given and none found using the name {
                        self.name
                    }.{file_type} in {parent_dir}: {error}"
                )
