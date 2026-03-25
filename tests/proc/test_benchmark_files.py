import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import cnv_path
from numpy.testing import assert_equal

from ctdam.parser import CnvFile, CTDData
from ctdam.proc.module import MissingParameterError
from ctdam.proc.modules import AlignCTD
from ctdam.proc.modules.geomar_wildedit import WildeditGEOMAR
from ctdam.proc.modules.seabird_functions import (
    BinAvg,
    CellTM,
    LoopRemoval,
    WFilter,
)
from ctdam.proc.procedure import Procedure
from ctdam.proc.utils import (
    BinnedDataError,
    get_alignment_delay_and_correlation_values,
)


@pytest.mark.parametrize(
    "file",
    [file for file in cnv_path.glob("*.cnv")],
)
class TestExampleFiles:
    @pytest.fixture
    def cnv(self, file: Path, run_long_tests: bool) -> CnvFile:
        if (not run_long_tests) and (file.stat().st_size > 5 * 1000000):
            pytest.skip(f"Skipping long cnv: {file}, due to pytest option.")
        try:
            cnv = CnvFile(file)
        except FileNotFoundError as error:
            pytest.skip(str(error))
        else:
            return cnv

    @pytest.fixture
    def df(self, cnv: CnvFile) -> pd.DataFrame:
        return cnv.df

    def test_align_function(self, cnv: CnvFile, create_files):
        instance = AlignCTD()
        try:
            result = instance(
                input=cnv,
                arguments={
                    "Oxygen": None,
                },
            )
        except (ValueError, BinnedDataError):
            assert True
        else:
            # check, whether the returned delay value is below a threshold
            if create_files:
                result.to_cnv(
                    f"alignctd_{result.metadata_source.file_name}.cnv"
                )
            if cnv.processing_steps.get_step("alignctd"):
                delay_values = get_alignment_delay_and_correlation_values(
                    result.processing_steps
                )
                for delays in delay_values:
                    assert 1 < float(delays[0]) < 6
            else:
                assert True

    def test_wildedit_geomar(self, cnv: CnvFile, create_files):
        instance = WildeditGEOMAR()
        try:
            return_cnv = instance(
                input=cnv,
                arguments={
                    "std1": 3,
                    "std2": 10,
                    "window_size": 200,
                },
            )
        except (ValueError, BinnedDataError):
            assert True
        else:
            if create_files:
                return_cnv.to_cnv(
                    f"wildedit_{return_cnv.metadata_source.file_name}.cnv"
                )
            assert isinstance(return_cnv, CTDData)
            assert isinstance(
                return_cnv.parameters.full_data_array, np.ndarray
            )

    def test_procedure_on_cnvs(self, cnv: CnvFile):
        old_cnv = copy.deepcopy(cnv)
        proc_config = {
            "input": cnv,
            "output_type": "internal",
            "modules": {
                "wildedit_geomar": {"window_size": 200},
                "alignctd": {
                    "Oxygen": None,
                    "Conductivity": None,
                    "Salinity": None,
                },
            },
        }
        try:
            Procedure(
                proc_config,
                timeout=5,
            )
        except (MissingParameterError, BinnedDataError):
            assert True
        else:
            # handle case, when no columns were present inside the file
            if (
                "alignctd" or "wildedit_geomar"
            ) in cnv.processing_steps.get_names():
                assert len(cnv.processing_steps) > len(
                    old_cnv.processing_steps
                )
            else:
                assert True

    def test_w_filter(self, cnv, create_files):
        instance = WFilter()
        pre_cnv = copy.deepcopy(cnv.parameters)
        try:
            return_cnv = instance(
                input=cnv,
                arguments={
                    "Temperature": {"window_width": 50},
                    "Oxygen": {"half_width": 2, "offset": 5},
                    "Conductivity": {
                        "window_type": "triangle",
                        "window_width": 200,
                        "half_width": 3,
                        "offset": 3,
                    },
                },
            )
        except (ValueError, BinnedDataError):
            assert True
        else:
            assert isinstance(return_cnv, CTDData)
            for param in return_cnv.parameters.get_parameter_list():
                if param.param not in [
                    "Pressure",
                    "Temperature",
                    "Conductivity",
                    "Salinity",
                    "Oxygen",
                    "Fluorometer",
                    "Turbidity Meter",
                    "PAR",
                    "SPAR",
                ]:
                    continue
                try:
                    if create_files:
                        return_cnv.to_cnv(
                            f"wfilter_{return_cnv.metadata_source.file_name}.cnv"
                        )
                    assert_equal(pre_cnv[param.name].data, param.data)
                except AssertionError:
                    assert True
                else:
                    print(f"Param still equal: {param.name}")
                    assert False

    def test_cell_tm(self, cnv, create_files):
        instance = CellTM()
        pre_cnv = copy.deepcopy(cnv)
        try:
            return_cnv = instance(
                input=cnv,
                arguments={},
            )
        except (ValueError, BinnedDataError):
            assert True
        else:
            assert isinstance(return_cnv, CTDData)
        for param in return_cnv.parameters.get_parameter_list():
            if param.param == "Conductivity":
                try:
                    if create_files:
                        return_cnv.to_cnv(
                            f"celltm_{return_cnv.metadata_source.file_name}.cnv"
                        )
                    assert_equal(
                        return_cnv.parameters[param.name].data,
                        pre_cnv.parameters[param.name].data,
                    )
                except AssertionError:
                    assert True
                else:
                    assert False

    def test_loop_edit(self, cnv, create_files):
        instance = LoopRemoval()
        # catch binned data
        try:
            pre_flag = copy.deepcopy(cnv.parameters["flag"].data)
        except KeyError:
            pytest.skip(f"File {cnv.file_name} is binned.")
        return_cnv = instance(
            input=cnv,
            arguments={},
        )
        assert isinstance(return_cnv, CTDData)
        if instance.ran_processing:
            try:
                if create_files:
                    return_cnv.to_cnv(
                        f"loopedit_{return_cnv.metadata_source.file_name}.cnv"
                    )
                assert_equal(pre_flag, return_cnv.parameters["flag"].data)
            except AssertionError:
                assert True
            else:
                assert False

    def test_bin_avg(self, cnv, create_files):
        instance = BinAvg()
        bin_variable = "prDM"
        if bin_variable not in cnv.parameters:
            pytest.skip()
        try:
            return_cnv = instance(
                input=cnv,
                arguments={
                    "bin_variable": bin_variable,
                    "bin_size": 0.1,
                },
            )
        except (ValueError, BinnedDataError):
            pytest.skip(f"File {cnv.file_name} is already binned.")
        else:
            if create_files:
                return_cnv.to_cnv(
                    f"bin_avg_{return_cnv.metadata_source.file_name}.cnv",
                    reduced_header=True,
                )
            assert isinstance(return_cnv, CTDData)
            # in case of pressure gaps, the bins do not rise continuesly,
            # thats why we are checking for 98%
            diff = np.diff(return_cnv.parameters[bin_variable].data)
            assert len(diff[np.isclose(diff, 0.1)]) > len(diff) * 0.98
