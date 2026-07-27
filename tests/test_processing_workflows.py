import pytest
from conftest import (
    cnv_path,
    hex_path,
    psa_path,
    test_hex,
    assert_different_np_array,
    test_cnv,
)
from numpy.testing import assert_equal

from ctdam.parser.read_ctd_data import read_ctd_data
from ctdam.proc.entry import process
from ctdam.proc.settings import IncompleteProcedureConfig
from ctdam.proc.workflow import Workflow


def test_empty_modules():
    ds = read_ctd_data(test_cnv)
    with pytest.raises(IncompleteProcedureConfig):
        Workflow(
            ds,
            {
                "input": test_hex,
                "psa_directory": psa_path,
            },
            auto_run=True,
        )


@pytest.mark.long
def test_process_entry_function():
    all_files = process(cnv_path, use_multiprocessing=False)


def test_gsw_xarray_workflow_processing(ds):
    if not (
        "pressure" in ds.data_vars
        and "conductivity" in ds.data_vars
        and "temperature" in ds.data_vars
    ):
        pytest.skip()
    proc_settings = {
        "modules": {
            "SA_from_SP": {},
            "CT_from_t": {},
            "sigma0": {},
        }
    }
    Workflow(
        ds,
        proc_settings,
    )
    assert "density" in ds.data_vars
    assert_different_np_array(
        ds.density.sel(sensor="primary"),
        ds.density.sel(sensor="secondary"),
        ds,
    )


@pytest.mark.xfail(reason="conversion not implemented yet.")
@pytest.mark.long
@pytest.mark.parametrize(
    "hex", [filename for filename in hex_path.glob("*.hex")]
)
def test_non_seabird_conversion_and_processing(hex, create_files, tmp_path):
    if hex.name.startswith("SO308-2_005"):
        pytest.skip()
    proc_config = {
        "output_type": "ctd_data",
        "output_dir": tmp_path,
        "modules": {
            "wildedit_geomar": {},
            "wfilter": {},
            "airpressure": {},
            "celltm": {},
            "alignctd": {},
            "Helmholtz_energy_ice": {},
            "loop_removal": {},
            "binavg": {},
        },
    }
    procedure = Workflow(proc_config, auto_run=True)
    file_path = procedure.ctd_data.path_to_file
    assert isinstance(procedure.ctd_data, CTDData)
    num_of_proc_steps = len(proc_config["modules"]) + 1
    if "Air_Pressure" not in procedure.ctd_data.metadata:
        num_of_proc_steps -= 1
    assert len(procedure.ctd_data.processing_steps) == num_of_proc_steps
    # check, whether salinity has been recalculated
    if create_files:
        pre_salinity = procedure.ctd_data.parameters["sal00"].data
        procedure.ctd_data.to_cnv(
            f"procedure_{file_path.with_suffix('.cnv')}",
            remove_flags=False,
        )
        try:
            assert_equal(
                pre_salinity, procedure.ctd_data.parameters["sal00"].data
            )
        except AssertionError:
            assert True
        else:
            assert False


@pytest.mark.xfail(reason="conversion not implemented yet.")
def test_conversion_options():
    proc_config = {
        "input": test_hex,
        "output_type": "internal",
        "modules": {
            "hex2py": {
                "min_soak_window": 50,
                "max_fd_quotient": 100,
                "min_velocity": 2.0,
            },
            "binavg": {},
        },
    }
    procedure = Workflow(proc_config, auto_run=True)
    assert procedure.output.cast_borders["down_start"] == 1053
