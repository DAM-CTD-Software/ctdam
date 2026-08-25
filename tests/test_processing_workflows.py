import pytest
from conftest import (
    assert_different_np_array,
    cnv_path,
    hex_path,
    psa_path,
    test_cnv,
    test_hex,
)

from ctdam.exceptions import BinnedDataError, MissingParameterError
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
    try:
        all_files = process(cnv_path, use_multiprocessing=False)
    except (MissingParameterError, BinnedDataError) as error:
        pytest.skip(
            f"Could not run workflow due to missing parameter: {error}"
        )


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


@pytest.mark.long
@pytest.mark.parametrize(
    "hex", [filename for filename in hex_path.glob("*.hex")]
)
def test_full_conversion_and_processing(hex, tmp_path):
    if hex.name.startswith(("SO308-2_005", "EMB379")):
        pytest.skip()
    proc_config = {
        "output_type": "ctd_data",
        "output_dir": tmp_path,
        "modules": {
            "cast_borders": {
                "crop": True,
            },
            "wildedit_geomar": {},
            "wfilter": {},
            "airpressure": {},
            "celltm": {},
            "alignctd": {},
            "Fdelta": {},
            "loop_removal": {},
            "binavg": {},
        },
    }
    ds = read_ctd_data(hex)
    try:
        workflow = Workflow(ds, proc_config, auto_run=True)
    except (MissingParameterError, BinnedDataError) as error:
        pytest.skip(
            f"Could not run workflow due to missing parameter: {error}"
        )
    num_of_proc_steps = len(proc_config["modules"]) + 1
    if "airpressure" not in workflow.ds.meta.provenance.keys():
        num_of_proc_steps -= 1
    assert len(workflow.ds.meta.provenance.keys()) == num_of_proc_steps
