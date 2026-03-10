import pytest
from conftest import cnv_path, test_cnv

from ctdam.parser import CnvFile, CnvProcessingSteps


@pytest.fixture
def proc_steps() -> CnvProcessingSteps:
    path_to_file = cnv_path.joinpath("EMB295_14-1.cnv")
    cnv = CnvFile(path_to_file)
    return CnvProcessingSteps(cnv.processing_info)


def test_output_list_length(proc_steps):
    assert len(proc_steps.modules) == 7


def test_individual_module_dict(proc_steps):
    for step, length in {
        "wildedit": 8,
        "datcnv": 6,
        "wfilter": 4,
    }.items():
        assert len(proc_steps.get_step(step).metadata) == length


def test_addition_of_new_proc_lines():
    cnv = CnvFile(test_cnv)
    len_datcnv_metadata = len(
        cnv.processing_steps.get_step("datcnv").metadata.keys()
    )
    cnv.add_processing_metadata("datcnv", "test", "5")
    assert len(cnv.processing_steps.get_names()) == 1
    assert (
        len(cnv.processing_steps.get_step("datcnv").metadata.keys())
        == len_datcnv_metadata + 1
    )
