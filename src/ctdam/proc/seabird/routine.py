import logging
import multiprocessing
from pathlib import Path

from ctdam.proc.seabird.module import ProcessingModule
from ctdam.proc.seabird.step import ProcessingStep
from ctdam.proc.settings import IncompleteConfigFile
from ctdam.proc.utils import fill_file_type_dir

logger = logging.getLogger(__name__)


class ProcessingRoutine:
    """
    Batch processing of running multiple processing modules in sequence is
    realised by this class. It also allows batch processing of multiple files
    at the same time.
    In order to accomplish that, a very specific input is needed, specified in
    detail by a configuration .toml file. For that reason, a thorough input
    check takes place upon initialization.

    Parameters
    ----------
    processing_info: dict :
        All the information necessary to run a processing routine. Can be built
        internally in other python code or, more often, will be the input from
        a .toml configuration file.

    """

    def __init__(self, processing_info: dict):
        self.processing_info = processing_info
        try:
            self.exe_dir = Path(processing_info["exe_directory"])
            self.psa_dir = Path(processing_info["psa_directory"])
        except KeyError:
            error_message = f"The input {
                processing_info
            } is missing an exe_dir and/or psa_dir, you need to specify both of them."
            raise IncompleteConfigFile(error_message)
        try:
            self.file_list = [
                Path(file) for file in processing_info["file_list"]
            ]
            assert len(self.file_list) > 0
        except (KeyError, AssertionError):
            try:
                self.input_dir = Path(processing_info["input_directory"])
            except KeyError:
                error_message = f"The input {
                    processing_info
                } is missing an input_dir and/or a file name, specify one of them."
                raise IncompleteConfigFile(error_message)
        try:
            self.xmlcons = Path(processing_info["xmlcons"])
            assert len(str(self.xmlcons)) > 1
        except (KeyError, AssertionError):
            self.xmlcons = None
        try:
            self.output_dir = Path(processing_info["output_directory"])
        except KeyError:
            try:
                self.output_dir = self.input_dir.parent
            except KeyError:
                self.output_dir = self.file_list[0].parent
        try:
            self.file_type_dir = Path(processing_info["file_type_directory"])
        except KeyError:
            self.file_type_dir = None
        try:
            self.verbose = processing_info["verbose"]
        except KeyError:
            self.verbose = False
        self.module_info = {
            key: value for key, value in processing_info["modules"].items()
        }
        if list(self.module_info.keys())[0] == "datcnv":
            self.input_data = "hex"
        else:
            self.input_data = "cnv"
        self.modules = self.create_modules()
        self.steps = self.create_steps()

    def create_modules(self) -> list[ProcessingModule]:
        """
        Loads the module information into individual module instances.

        A module is the representation of one Sea-Bird module of the same name.
        It stores the path to the executable and a configuration .psa file.
        """
        out_list = []
        for name, info in self.module_info.items():
            try:
                psa_path = info["psa"]
            except KeyError:
                psa_path = None
            try:
                exe_path = info["exe"]
            except KeyError:
                exe_path = None
            try:
                new_file_suffix = info["file_suffix"]
            except KeyError:
                new_file_suffix = ""
            out_list.append(
                ProcessingModule(
                    name=name,
                    exe_dir=self.exe_dir,
                    psa_dir=self.psa_dir,
                    psa_path=psa_path,
                    exe_path=exe_path,
                    new_file_suffix=new_file_suffix,
                )
            )
        return out_list

    def create_steps(self) -> list[ProcessingStep]:
        """
        Creates a list of processing steps from the input information.

        A step is the application of one processing module to a target data
        file, which usually is either .hex or .cnv .
        """
        # TODO: break into smaller pieces
        out_list = []
        try:
            files = self.file_list
        except AttributeError:
            files = [
                file for file in self.input_dir.rglob(f"*{self.input_data}")
            ]
        for file in files:
            file = Path(file)
            input_dir = file.parent
            if self.input_data == "hex":
                xmlcon = self.find_xmlcon(file)
                if not xmlcon:
                    continue
            else:
                xmlcon = None
            for index, module in enumerate(self.modules):
                if index == 0:
                    input_path = file
                else:
                    input_path = self.output_dir.joinpath(
                        file.with_suffix(".cnv").name
                    )
                if module.name == "bottlesum":
                    input_path = input_dir.joinpath(
                        file.with_suffix(".ros").name
                    )
                    if not input_path.exists():
                        continue
                    new_file_name = file.with_suffix(".btl").name
                elif module.name == "iow_btl_id":
                    input_path = input_path.joinpath(
                        file.with_suffix(".btl").name
                    )
                    if not input_path.exists():
                        continue
                    new_file_name = file.with_suffix(".btl").name
                elif module.name == "derive":
                    xmlcon = self.find_xmlcon(file)
                    new_file_name = file.with_suffix(".cnv").name
                else:
                    new_file_name = file.with_suffix(".cnv").name
                out_list.append(
                    ProcessingStep(
                        module=module,
                        input_path=input_path,
                        xmlcon_path=xmlcon,
                        output_path=self.output_dir,
                        new_name=str(new_file_name),
                        verbose=self.verbose,
                    )
                )
            if self.file_type_dir:
                for target_file in input_dir.iterdir():
                    if target_file.stem == file.stem:
                        fill_file_type_dir(self.file_type_dir, target_file)
        return out_list

    def find_xmlcon(self, input_file: Path) -> Path | None:
        """
        Recursively searches for a corresponding .XMLCON file to a given input
        file.

        Parameters
        ----------
        input_file: Path :
            The path to the target input file.


        Returns
        -------
        A path to the .XMLCON file, or none, if none found.

        """
        if self.xmlcons:
            parent_dir = self.xmlcons
        else:
            parent_dir = input_file.parent
        for xmlcon in parent_dir.rglob("*.XMLCON", case_sensitive=False):
            if xmlcon.stem.lower() == input_file.stem.lower():
                return xmlcon
        logger.warning(
            f'Could not find a matching XMLCON for the file "{
                input_file.stem
            }" inside of "{parent_dir}".'
        )

    def run(self, timeout: int = 60):
        """
        Performs the processing by calling the steps run methods in sequence.
        """
        for step in self.steps:
            step.run(timeout=timeout)

    def start_thread(self):
        """
        Starts a separate process to run the processing.

        This leverages parallel computing capabilities and allows the targeted
        killing of the processing, when necessary.
        """
        self.run_thread = multiprocessing.Process(target=self.run)
        self.run_thread.start()

    def cancel(self):
        """Kills the running processing process."""
        logger.info(f"Interupted processing of \n{self.processing_info}")
        self.run_thread.kill()
