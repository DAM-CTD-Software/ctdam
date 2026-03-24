from __future__ import annotations

import copy
from collections import UserList


class CnvProcessingSteps(UserList):
    """
    A python representation of the individual ctdam.proc steps conducted
    in the process of a cnv file creation. These modules are stored in
    a dictionary structure, together with all the variables/metadata/etc.
    given in the header of a cnv file.

    Parameters
    ----------
    raw_processing_info: list
        The processing metadata lines of a .cnv file
    """

    def __init__(self, raw_processing_info: list):
        self.modules = self.extract_individual_modules(raw_processing_info)
        self.data = []
        for module in self.modules:
            self.data.append(
                self.create_step_instance(module, raw_processing_info)
            )

    def _form_processing_info(self) -> list:
        """
        Parse back to cnv-style metadata.

        Returns
        -------
        A list representing the metadata lines.
        """
        out_list = []
        for module in self.data:
            module = copy.deepcopy(module)
            if "vars" in module.metadata and module.name != "wildedit":
                module.metadata["date"] = (
                    module.metadata["date"]
                    + f" [{module.name.lower()}_vars = {module.metadata.pop('vars')}]"
                )
            if module.name == "binavg":
                collection_string = module.metadata["binavg_surface_bin"][
                    "surface_bin"
                ]
                for k, v in module.metadata["binavg_surface_bin"].items():
                    if k != "surface_bin":
                        collection_string += f", {k} = {v}"
                module.metadata["binavg_surface_bin"] = collection_string
            for key, value in module.metadata.items():
                if module.name == "wfilter" and key == "action":
                    for action_key, action_value in value.items():
                        out_list.append(
                            f"wfilter_action {action_key} = {action_value}\r\n"
                        )
                else:
                    out_list.append(f"{module.name}_{key} = {value}\r\n")
        out_list.append("file_type = ascii\r\n")
        return out_list

    def get_names(self) -> list[str]:
        """Return the processing step names."""
        return [step.name for step in self.data]

    def extract_individual_modules(self, raw_info: list[str]) -> list:
        """
        Helper function to extract processing modules from raw .cnv info.

        Parameters
        ----------
        raw_info : list[str] :
            A list of metadata lines

        Returns
        -------
        A list of ProcessingSteps.
        """
        module_list = []
        for line in raw_info:
            module = line.split("_")[0]
            if (module not in module_list) and (
                line.split()[0] != "file_type"
            ):
                module_list.append(module)
        return module_list

    def create_step_instance(
        self,
        module: str,
        raw_info: list[str],
    ) -> ProcessingStep:
        """
        Create a new ProcessingStep instance.

        Parameters
        ----------
        module : str
            The name of the step
        raw_info : list[str] :
            The key-value style metadata lines

        Returns
        -------
        A ProcessingStep instance.
        """
        # TODO: probably need to split this into smaller bits
        out_dict = {}
        inner_action_dict = {}
        # extract lines corresponding to the module
        for line in raw_info:
            if module == line.split("_")[0]:
                # removing the module names from the lines
                shifting_index = len(module) + 1
                line_content = line[shifting_index:]
                # handle the case of the validation methods keyword being
                # 'action', which corresponds to an entire dict of values
                if line_content[:6] == "action":
                    inner_action_dict = self._module_dict_feeder(
                        line_content[6:], inner_action_dict
                    )
                else:
                    # handle the cases where after some date value, another value
                    # is printed inside of [] brackets
                    double_value_list = line_content.split("[")
                    if len(double_value_list) > 1:
                        out_dict = self._module_dict_feeder(
                            double_value_list[1][shifting_index:-2], out_dict
                        )
                        line_content = double_value_list[0]
                    if line_content[:11] == "surface_bin":
                        surface_bin_dict = {}
                        for line in line_content.split(","):
                            self._module_dict_feeder(line, surface_bin_dict)
                        out_dict["surface_bin"] = surface_bin_dict
                        continue
                    # usual behavior, for 99% cases:
                    # assigning key and value to the module dict
                    out_dict = self._module_dict_feeder(line_content, out_dict)
        if inner_action_dict:
            out_dict["action"] = inner_action_dict
        return ProcessingStep(module, out_dict)

    def _module_dict_feeder(
        self,
        line: str,
        dictionary: dict,
        split_value: str = "=",
    ):
        """
        Helper for create_step_instance.

        Parameters
        ----------
        line: str
            A metadata line
        dictionary: dict
            The dictionary to extend
        split_value: str
            The key-value separator (Default value = '=')

        Returns
        -------
        A dictionary extended by one metadata lines information.
        """
        # adds the values of a specific header line into a dictionary
        try:
            key, value = line.split(split_value)
        except ValueError:
            pass
        else:
            dictionary[key.strip()] = value.strip()
        return dictionary

    def get_step(self, step: str) -> ProcessingStep | None:
        """
        Getter for ProcessingSteps.

        Parameters
        ----------
        step : str
            The step to get

        Returns
        -------
        A ProcessingStep.
        """
        for index, element in enumerate(self.data):
            if str(element) == step:
                return self.data[index]
        return None

    def add_info(
        self,
        module: str,
        key: str,
        value: str,
    ) -> ProcessingStep | None:
        """
        Adds new processing lines to the list of processing module information

        Parameters
        ----------
        module: str
            The name of the processing module
        key: str
            The description of the value
        value: str
            The information

        Returns
        -------
        The extended ProcessingStep.
        """
        if module in self.modules:
            step_info = self.get_step(module)
            if step_info:
                step_info.metadata[key] = value
        else:
            step_info = ProcessingStep(name=module, metadata={key: value})
            self.data.append(step_info)
            self.modules.append(module)
        return step_info


class ProcessingStep:
    """
    Class that is meant to represent one individual processing step.

    A processing step is one single task that changed the data of a CTD
    cast.

    Parameters
    ----------
    name : str
        The name of the step
    metadata : str
        The metadata information for this step
    """

    def __init__(self, name: str, metadata: dict):
        self.name = name
        self.metadata = metadata

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        return self.metadata == other.metadata
