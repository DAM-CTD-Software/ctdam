from pathlib import Path

import pytest
from conftest import (
    btl_path,
    check_and_remove_file,
    cnv_path,
    hex_path,
    proc_template,
    psa_path,
    test_hex,
)
from numpy.testing import assert_equal

from ctdam.parser.ctddata import CTDData
from ctdam.proc.procedure import Procedure
from ctdam.proc.settings import IncompleteProcedureConfig


@pytest.mark.long
@pytest.mark.parametrize(
    "filename", [filename for filename in hex_path.glob("*.hex")]
)
def test_procedure_on_hexes(filename: Path, tmp_path):
    output_name = f"{filename.stem}_test.cnv"
    proc_config = {
        "input": filename,
        "output_dir": tmp_path,
        "output_name": output_name,
        "output_type": "cnv",
        "modules": {
            "alignctd": {},
            "binavg": {},
        },
    }
    procedure = Procedure(
        proc_config,
        auto_run=False,
        timeout=10,
    )
    procedure.run()
    for suffix in [""]:
        check_and_remove_file(
            tmp_path.joinpath(f"{filename.stem}_test{suffix}.cnv")
        )


def test_fingerprint(tmp_path):
    proc_config = {
        "input": cnv_path,
        "output_type": "internal",
        "modules": {
            "alignctd": {"Oxygen": ""},
        },
    }
    procedure = Procedure(
        proc_config,
        auto_run=False,
        procedure_fingerprint_directory=tmp_path,
    )
    new_config = procedure.procedure_fingerprint()
    if new_config is not None:
        assert proc_config == new_config.data
    else:
        pytest.fail("Expected a configuration from fingerprint.")


def test_procedure_without_seabird(tmp_path):
    cnv_name = "EMB295_14-1"
    file_type_dir = tmp_path.joinpath("procedure")
    proc_config = {
        "input": cnv_path.joinpath(cnv_name).with_suffix(".cnv"),
        "output_type": "cnv",
        "output_dir": tmp_path,
        "modules": {
            "alignctd": {"Oxygen": "", "file_suffix": "_align"},
            "wildedit_geomar": {
                "std1": "3",
                "std2": 4,
                "window_size": "200",
                "file_suffix": "_wildedit",
            },
            "Helmholtz_energy_ice": {"file_suffix": "_gsw"},
            "create_bottle_file": {
                "bl": str(btl_path.joinpath(cnv_name).with_suffix(".bl")),
            },
            "binavg": {"file_suffix": "_binavg"},
        },
    }
    procedure = Procedure(
        proc_config, auto_run=True, file_type_dir=file_type_dir
    )
    assert "gsw_Helmholtz_energy_ice_0" in procedure.ctd_data.parameters
    assert (
        "create_bottle_file"
        not in procedure.ctd_data.processing_steps.get_names()
    )
    assert procedure.btl.ctd_data == procedure.ctd_data
    for file in [
        *[
            tmp_path.joinpath(cnv_name + suffix).with_suffix(".cnv")
            for suffix in ["", "_align", "_wildedit", "_gsw", "_binavg"]
        ],
        tmp_path.joinpath(cnv_name).with_suffix(".obtl"),
        file_type_dir.joinpath("obtl", cnv_name).with_suffix(".obtl"),
    ]:
        check_and_remove_file(file)


def test_empty_modules():
    with pytest.raises(IncompleteProcedureConfig):
        Procedure(
            {
                "input": test_hex,
                "psa_directory": psa_path,
            },
            auto_run=True,
        )


@pytest.mark.long
def test_full_file_proc(tmp_path):
    Procedure(
        proc_template,
        auto_run=False,
        file_type_dir=tmp_path,
        procedure_fingerprint_directory=tmp_path,
    ).run(test_hex)


@pytest.mark.long
@pytest.mark.parametrize(
    "hex", [filename for filename in hex_path.glob("*.hex")]
)
def test_non_seabird_conversion_and_processing(hex, create_files, tmp_path):
    if hex.name.startswith("SO308-2_005"):
        pytest.skip()
    proc_config = {
        "input": hex,
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
    procedure = Procedure(proc_config, auto_run=True, plot=True)
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
    procedure = Procedure(proc_config, auto_run=True)
    assert procedure.output.cast_borders["down_start"] == 1053
