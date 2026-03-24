import logging
import platform
import subprocess
from pathlib import Path
from time import sleep

from ctdam.proc.seabird import ProcessingModule

logger = logging.getLogger(__name__)


class ProcessingStep:
    """
    A representation of a single Seabird processing step.

    One instance of this class corresponds to one Seabird processing module and
    its invocation on one single file.

    Parameters
    ----------

    module: ProcessingModule :
        The Sea-Bird module to run.

    input_path: Path | str
        The path to the target file.

    xmlcon_path: Path | str | None
        The path to the XMLCON file.

    output_path: Path | str | None
        The path to write the new file to. Default is the same as the input
        one.

    original_input_path: Path | str | None
        The path to the target file of the whole processing workflow.

    new_name: str | None
        Option to set a new name to the output file.

    verbose: bool
        Allows to run the module in "window" mode, which gives the option to
        check and manipulate the modules configuration. Is suppressed by
        default.

    Returns
    -------
    A runnable instance.

    """

    def __init__(
        self,
        module: ProcessingModule,
        input_path: Path | str,
        xmlcon_path: Path | str | None = None,
        output_path: Path | str | None = None,
        original_input_path: Path | str | None = None,
        new_name: str | None = None,
        verbose: bool = False,
    ):
        self.exe = module.exe
        self.psa = module.psa
        self.name = module.name
        self.input_path = Path(input_path)
        self.input_dir = self.input_path.parent
        self.new_name = self.build_new_name(new_name, module.new_file_suffix)
        self.verbose = verbose
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.input_dir
        if xmlcon_path:
            self.xmlcon = Path(xmlcon_path)
        else:
            self.xmlcon = self.input_dir.joinpath(
                self.input_path.stem + ".XMLCON"
            )
        if original_input_path:
            self.original_input_path = Path(original_input_path)
        else:
            self.original_input_path = self.input_path

    def __str__(self) -> str:
        return self.name

    def build_new_name(
        self,
        new_name: str | None,
        new_file_suffix: str,
    ) -> Path:
        """
        Sets the output file path with all the information given.

        Parameters
        ----------
        new_name: str | None
            The optional new output name.

        new_file_suffix: str
            The optional suffix to append to the new output name.

        Returns
        -------
        A string representing the new name.

        """
        if new_name:
            name = Path(new_name).stem
        else:
            name = self.input_path.stem
        return Path(name + new_file_suffix).with_suffix(".cnv")

    def run_string(self) -> list:
        """
        Builds the command line command that is used to run the module.

        Collects the different bits of information and options and handles them
        accordingly. Does also consider module specific specialities and the
        wanted verbosity.
        """
        run_command_list = [str(self.exe)]
        if not self.verbose:
            run_command_list.append("/s")
            run_command_list.append("/m")
        if self.name == "iow_btl_id":
            run_command_list.append(f"-i{self.input_path}")
            run_command_list.append(f"-o{self.output_path}")
        elif self.name == "bottlesum":
            input_ros_path = self.original_input_path.with_suffix(".ros")
            if not input_ros_path.exists():
                input_ros_path = self.input_path.with_suffix(".ros")
                if not input_ros_path.exists():
                    return []
            run_command_list.append(f"/c{self.xmlcon}")
            run_command_list.append(f"/p{self.psa}")
            run_command_list.append(f"/i{input_ros_path}")
            run_command_list.append(f"/o{self.output_path}")
            run_command_list.append(f"/f{self.new_name.with_suffix('.btl')}")
        else:
            run_command_list.append(f"/p{self.psa}")
            run_command_list.append(f"/i{self.input_path}")
            run_command_list.append(f"/o{self.output_path}")
        if self.name not in ["airpressure", "iow_btl_id", "bottlesum"]:
            run_command_list.append(f"/c{self.xmlcon}")
            run_command_list.append(f"/f{self.new_name}")
        if self.name == "airpressure":
            run_command_list.append(f"/f\\{self.new_name}")
        logger.debug(
            f"Command line arguments of processing step {self.name}:\n\t - "
            + "\n\t - ".join(run_command_list)
        )
        return run_command_list

    def run(self, command: list | None = None, timeout: int = 60):
        """
        Handles the creation of the command line command.

        Is mostly needed to correctly running the Sea-Bird processing modules
        on a linux system using the wine emulator.

        Parameters
        ----------
        command: list | None
             The command to run. If not given, creates it.
        """
        if not command:
            command = self.run_string()
        # To run processing on Linux, two programs need to be installed, wine
        # and unix2dos. Inside wine, the SeabirdProcessing Software Suite needs
        # to be installed and configured. If airpressure or iow_btl_id want to
        # be used, these need to be copied in the directory where the other
        # processing exes reside.
        if platform.system() == "Linux":
            # seabird cannot work with unix-style line-endings, using only LF,
            # so the input file needs to be converted to use windows-style
            # line-endings, featuring CR followed by a LF
            self.run_process(["unix2dos", self.input_path])
            command.insert(0, "wine")
        self.run_process(command, timeout)

    def run_process(self, command: list, timeout: int = 60):
        """
        Creates and monitors the execution of the module.

        This is done in a separate process, to allow leveraging
        multi-threading. Does also set a timeout for killing the process after
        some time.

        Parameters
        ----------
        command: list
            The command to run, with all the necessary parameters.

        timeout: int
            The time in seconds to wait for the execution to finish. Kills the
            process otherwise.
        """
        if not command:
            return
        try:
            ps = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=platform.platform().startswith("Win"),
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as error:
            logger.error(
                f"Running processing step of the module {
                    self.name
                } and the command '{command}' failed: {error}"
            )
        else:
            run_time = 0
            while ps.poll() is None and run_time < timeout:
                sleep(1)
                run_time += 1
            if run_time == timeout:
                ps.kill()
                raise subprocess.TimeoutExpired(
                    f"Process {command} ran into a timeout", timeout=timeout
                )
