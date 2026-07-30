import gsw
from conftest import cnv_path, test_cnv

from ctdam.parser.cnvfile import CnvFile
from ctdam.proc.modules.available_modules import processing_functions
from ctdam.proc.modules.external_functions import (
    ExternalFunctionCaller,
    ExternalFunctions,
)
from ctdam.proc.procedure import Procedure


def test_external_function_dict():
    exfun = ExternalFunctions([gsw])
    functions = exfun.get_all_functions()

    assert len(exfun) == 1
    assert functions

    for function_name in [
        "SP_from_C",
        "SA_from_SP",
        "CT_from_t",
        "rho",
        "z_from_p",
    ]:
        assert function_name in functions


def test_ex_fun_info():
    info = ExternalFunctions([gsw]).get_all_functions()["Helmholtz_energy_ice"]
    assert info.return_info[0]["desc"]
    cnv = CnvFile(test_cnv)
    success = info.run(cnv)
    assert success
    assert "gsw_Helmholtz_energy_ice_1" in list(cnv.parameters.keys())
    assert (
        cnv.parameters["gsw_Helmholtz_energy_ice_0"].data.shape
        == cnv.parameters["prDM"].data.shape
    )


def test_multi_step_ex_functions():
    gsws = ExternalFunctions([gsw]).get_all_functions()
    step1 = gsws["SA_from_SP_Baltic"]
    step2 = gsws["enthalpy_t_exact"]
    cnv = CnvFile(cnv_path.joinpath("MSM140_1.cnv"))
    success1 = step1.run(cnv)
    assert success1
    success2 = step2.run(cnv)
    assert success2
    assert "gsw_enthalpy_t_exact_1" in list(cnv.parameters.keys())


def test_caller():
    cnv = CnvFile(cnv_path.joinpath("MSM140_1.cnv"))
    module = ExternalFunctionCaller("SA_from_SP_Baltic", processing_functions)
    module(
        input=cnv,
        output_name=str("test"),
    )
    assert "gsw_saA1" in list(cnv.parameters.keys())


def test_in_procedure():
    procedure = Procedure(
        configuration={
            "input": test_cnv,
            "output_type": "cnvobject",
            "modules": {
                "wildedit_geomar": {},
                "Helmholtz_energy_ice": {},
            },
        },
        auto_run=True,
    )
    assert "gsw_Helmholtz_energy_ice_0" in procedure.ctd_data.parameters


def test_module_addition():
    exfun = ExternalFunctions([gsw])
    exfun.add_module("seabirdscientific.conversion")
    exfun.add_module("seabirdfilehandler")
    assert len(exfun) == 2
    exfun.remove_module("gsw")
    assert len(exfun) == 1
