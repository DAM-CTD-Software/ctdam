import logging
from collections import UserDict
from inspect import getmembers, isfunction
from pathlib import Path
from typing import Callable

import docstring_parser
import numpy as np
import pandas as pd
from numpydoc.docscrape import NumpyDocString

from ctdam.parser.ctddata import CTDData
from ctdam.proc.module import ArrayModule

logger = logging.getLogger(__name__)


class ExternalFunctions(UserDict):
    def __init__(self, modules: list) -> None:
        self.data = {}
        for module in modules:
            self.data[module.__name__] = self.get_module_functions(module)

    def available_modules(self) -> list:
        return list(self.data.keys())

    def functions_of_certain_module(self, module: str) -> dict:
        if module in self.available_modules():
            return self.data[module]
        else:
            return {}

    def get_all_functions(self) -> dict:
        out_dict = {}
        for module in self.available_modules():
            out_dict = {**out_dict, **self.functions_of_certain_module(module)}
        return out_dict

    def list_of_function_names(self, module: str = "") -> list:
        if module:
            return [key for key in self.functions_of_certain_module(module)]
        else:
            return [key for key in self.get_all_functions()]

    def get_module_functions(self, module) -> dict:
        out_dict = {}
        for name, function in getmembers(module, isfunction):
            out_dict[name] = ExternalFunctionInfo(function)
        return out_dict


class ExternalFunctionInfo:
    def __init__(self, external_function: Callable) -> None:
        self.function = external_function
        self.name = self.function.__name__
        module = self.function.__module__
        self.module = module.split(".")[0] if "." in module else module
        self.raw_docstring = self.function.__doc__
        self.parse_docstring(self.raw_docstring)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.__str__()

    def run(self, ctd_data: CTDData, parameters: dict = {}) -> bool:
        if parameters:
            return self._run_with_parameters(ctd_data, parameters)
        else:
            return self._run_with_mapping(ctd_data)

    def _run_with_parameters(
        self,
        ctd_data: CTDData,
        parameters: dict,
    ) -> bool:
        try:
            self.execute_funtion(
                args=list(parameters.values()), ctd_data=ctd_data
            )
        except Exception as error:
            logger.warning(f"Could not run {self.name}: {error}")
            return False
        return True

    def _run_with_mapping(self, ctd_data: CTDData) -> bool:
        args0 = []
        args1 = []
        second_column = False
        for parameter in self.param_info:
            try:
                columns = self.map_parameter(parameter["name"], ctd_data)
                if len(columns) == 0:
                    logger.warning(
                        f"Could not run {self.name}, argument {parameter} was not understood."
                    )
                    return False
                elif len(columns) == 1:
                    args0.append(ctd_data.parameters[columns[0]].data)
                    args1.append(ctd_data.parameters[columns[0]].data)
                elif len(columns) == 2:
                    args0.append(ctd_data.parameters[columns[0]].data)
                    args1.append(ctd_data.parameters[columns[1]].data)
                    second_column = True
                else:
                    raise ValueError(
                        f"Unexpected number of columns in: {columns}"
                    )
            except KeyError as error:
                logger.warning(
                    f"Could not run {self.name} without column {str(error).strip()}. "
                )
                return False

        return_value0 = self.execute_funtion(args0, ctd_data)
        if second_column:
            return_value1 = self.execute_funtion(args1, ctd_data, True)
        else:
            return_value1 = True
        return return_value0 and return_value1

    def execute_funtion(
        self,
        args: list,
        ctd_data: CTDData,
        second_sensor: bool = False,
    ) -> bool:
        try:
            new_columns = self.function(*args)
        except Exception as error:
            logger.warning(f"Could not run {self.name}: {error}")
            return False
        if isinstance(new_columns, tuple) or len(self.return_info) > 1:
            if not len(new_columns) == len(self.return_info):
                logger.warning(
                    f"Could not run {self.name}: expected number of return values does not match the actual ones."
                )
                return False
        else:
            new_columns = [new_columns]
        for column, return_value in zip(new_columns, self.return_info):
            metadata = self.create_cnv_metadata(return_value, second_sensor)
            ctd_data.parameters.create_parameter(
                data=column,
                metadata=metadata,
                name=metadata["name"],
            )
        return True

    def create_cnv_metadata(
        self,
        return_value: dict,
        second_sensor: bool = False,
    ) -> dict:
        return_name = str(return_value["name"])
        mapped_name = self.map_parameter(return_name)
        if len(mapped_name) > 1:
            shortname = mapped_name[int(second_sensor)]
        else:
            shortname = f"{self.module}_{mapped_name[0].split('_')[0] if '_' in mapped_name[0] else mapped_name[0]}_{int(second_sensor)}"
        name = return_name.strip()
        unit = (
            return_value["type"].split(",")[1]
            if "," in return_value["type"]
            else return_value["type"]
        ).strip()
        metainfo = return_value["desc"].strip()
        return {
            "shortname": shortname,
            "longinfo": f"{name}, {metainfo} [{unit}]",
            "name": name,
            "metainfo": metainfo,
            "unit": unit,
        }

    def map_parameter(
        self,
        parameter: str,
        ctd_data: CTDData | None = None,
    ) -> list:
        mapper = {
            "p": ["prDM"],
            "SA": ["gsw_saA0", "gsw_saA1"],
            "SA_baltic": ["gsw_saA0", "gsw_saA1"],
            "CT": ["gsw_ctA0", "gsw_ctA1"],
            "t": ["t090C", "t190C"],
            "lat": ["latitude"],
            "lon": ["longitude"],
            "SP": ["sal00", "sal11"],
            "pt": ["potemp090C", "potemp190C"],
        }
        if parameter in mapper:
            return mapper[parameter]
        elif isinstance(ctd_data, CTDData):
            present_params = [
                p.name
                for p in ctd_data
                if p.param.lower() == parameter.lower()
            ]
            if present_params:
                return present_params
            else:
                return [parameter]
        else:
            return [parameter]

    def parse_docstring(self, raw_docstring):
        if not isinstance(raw_docstring, str):
            return None
        docstring = docstring_parser.parse(raw_docstring)
        if not docstring.style:
            return None
        self.general_info = str(docstring.short_description) + (
            str(docstring.long_description)
            if docstring.long_description
            else ""
        )
        self.param_info = [
            {
                "name": p.arg_name,
                "desc": p.description,
            }
            for p in docstring.params
        ]
        if docstring.style.name.lower() == "numpydoc":
            docstring = NumpyDocString(raw_docstring)
            self.return_info = [
                {
                    "name": p.name,
                    "type": p.type,
                    "desc": " ".join(p.desc),
                }
                for p in docstring["Returns"]
            ]
        else:
            ret_object = docstring.returns
            if ret_object:
                self.return_info = [
                    {
                        "name": ret_object.return_name,
                        "type": ret_object.type_name,
                        "desc": ret_object.description,
                    }
                ]
            else:
                self.return_info = [{"name": self.name}]


class ExternalFunctionCaller(ArrayModule):
    """ """

    def __init__(
        self,
        module: str,
        processing_functions: ExternalFunctions,
    ) -> None:
        super().__init__()
        self.module = module
        if self.module not in processing_functions.list_of_function_names():
            raise ValueError(
                f"Could not run processing function: {module}, unkown."
            )
        self.function = processing_functions.get_all_functions()[module]
        self.name = self.function.name

    def __call__(
        self,
        input: Path | str | CTDData | pd.DataFrame | np.ndarray,
        arguments: dict = {},
        output: str = "cnvobject",
        output_name: str | None = None,
        **kwargs,
    ) -> None | CTDData | pd.DataFrame | np.ndarray:
        return super().__call__(input, arguments, output, output_name)

    def transformation(self) -> bool:
        self.parent_module = self.function.module
        try:
            return_value = self.function.run(self.ctd_data, self.arguments)
        except Exception as error:
            logger.warning(
                f"Could not run processing function: {self.module}: {error}"
            )
            return False
        return return_value
