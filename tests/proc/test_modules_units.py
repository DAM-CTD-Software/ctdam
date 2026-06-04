import logging

import numpy as np
import pytest
from conftest import btl_path, cnv_path, test_cnv
from numpy.testing import assert_array_equal

from ctdam.exceptions import BinnedDataError
from ctdam.parser import CnvFile, CTDData
from ctdam.proc.modules import (
    AirPressureCorrection,
    AlignCTD,
    LoopRemoval,
    OwnBtlFile,
    WFilter,
    create_bottle_file,
    wildedit_geomar,
)
from ctdam.proc.utils import get_alignment_delay_and_correlation_values

logger = logging.getLogger(__name__)


@pytest.fixture
def cnv():
    return CnvFile(test_cnv, create_dataframe=False)


def test_align_get_corr(cnv):
    instance = AlignCTD()
    instance.parameters = cnv.parameters
    assert instance.get_correlation(cnv.parameters["sbeox0ML/L"]) == -1
    assert instance.get_correlation(cnv.parameters["c0mS/cm"]) == 1


def test_correlation_check():
    instance = AlignCTD()
    instance.minimum_correlation = 0.1
    instance.sample_rate = 24
    assert not instance.check_correlation_result(
        5 * instance.sample_rate, 0.09
    )
    assert not instance.check_correlation_result(
        6.001 * instance.sample_rate, 0.50
    )
    assert not instance.check_correlation_result(
        0.99 * instance.sample_rate, 0.50
    )
    assert instance.check_correlation_result(5.99 * instance.sample_rate, 0.50)
    assert not instance.check_correlation_result(np.nan, 0.50)
    assert not instance.check_correlation_result(
        2 * instance.sample_rate, np.nan
    )


def test_align_without_values(cnv):
    new_cnv = AlignCTD()(
        input=cnv,
        arguments={
            "Oxygen": None,
        },
    )
    assert isinstance(new_cnv, CTDData)
    try:
        assert_array_equal(
            CnvFile(
                test_cnv, create_dataframe=False
            ).parameters.get_full_data_array(),
            new_cnv.parameters.get_full_data_array(),
        )
    except AssertionError:
        if not new_cnv.processing_steps.get_step("alignctd"):
            assert False
        delay_values = get_alignment_delay_and_correlation_values(
            new_cnv.processing_steps
        )
        for delays in delay_values:
            assert 1 < float(delays[0]) < 6

    else:
        assert not new_cnv.processing_steps.get_step("alignctd")


def test_compare_align_with_and_without_values(cnv):
    without_values = AlignCTD()(
        input=cnv,
        arguments={
            "Oxygen": None,
        },
    )
    if not without_values.processing_steps.get_step("alignctd"):
        assert False
    delay_values = get_alignment_delay_and_correlation_values(
        without_values.processing_steps
    )
    with_values = AlignCTD()(
        input=CnvFile(test_cnv, create_dataframe=False),
        arguments={
            "Oxygen1": delay_values[0][0],
            "Oxygen2": delay_values[1][0],
        },
    )
    assert_array_equal(
        without_values.parameters.full_data_array,
        with_values.parameters.full_data_array,
    )


def test_wildedit_geomar_logic(cnv):
    data = cnv.parameters["t090C"].data
    new_data, flags = wildedit_geomar(
        data=data,
        flag=cnv.parameters["flag"].data,
        std1=3.0,
        std2=10,
        window_size=50,
    )
    assert new_data.size == data.size == flags.size


def test_alignment_factor_retrieval(cnv):
    result = AlignCTD()(
        input=cnv,
        arguments={
            "Oxygen": None,
        },
    )
    assert get_alignment_delay_and_correlation_values(
        result.processing_steps
    ) == [
        ("3.21", "0.29"),
        ("3.0", "0.14"),
    ]


def test_air_pressure_correction(cnv):
    old_data = cnv.parameters["prDM"].data
    new_cnv = AirPressureCorrection()(input=cnv)
    pressure_diff = (
        new_cnv.processing_steps.get_step("airpressurecorrection")
        .metadata["pressure_diff"]
        .split()[0]
    )
    assert old_data.size == new_cnv.parameters["prDM"].data.size
    assert float(old_data[0]) + float(pressure_diff) == float(
        new_cnv.parameters["prDM"].data[0]
    )


def test_airpressure_with_bugged_metadata(cnv):
    cnv.metadata["Air_Pressure"] = "definitely_not_a_number"
    new_cnv = AirPressureCorrection()(input=cnv)
    assert isinstance(new_cnv, CTDData)


def test_binned_data_error():
    cnv = cnv_path.joinpath("MSM140_1.cnv")
    with pytest.raises(BinnedDataError):
        AlignCTD()(
            input=cnv,
            arguments={
                "Oxygen": None,
            },
        )


def test_create_btl():
    btl = create_bottle_file(
        input=cnv_path.joinpath("EMB295_14-1.cnv"),
        arguments={
            "bl": btl_path.joinpath("EMB295_14-1.bl"),
            "write_btl": False,
        },
    )
    assert isinstance(btl, OwnBtlFile)


def test_wfilter(cnv):
    new_cnv = WFilter()(
        input=cnv,
        arguments={
            "tUrB iDIty": {"window_type": "median", "window_width": 10}
        },
    )
    assert isinstance(new_cnv, CTDData)
    # check for boundary effects
    assert new_cnv["prDM"].data[0] > 0.2
    assert cnv.parameters.get_data_length() == new_cnv.get_data_length()


def test_time_dependent_loop_removal():

    module = LoopRemoval()
    # strictly increasing — nothing should be flagged
    pressure = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 4.01])
    flags = module.time_dependent_loop_removal(pressure=pressure, delta=0.0)
    assert not flags.any()

    # loop at index 3: should be flagged
    pressure = np.array([0.0, 1.0, 3.0, 2.0, 4.0])
    flags = module.time_dependent_loop_removal(pressure=pressure, delta=0.0)
    assert flags[3]
    assert not flags[[0, 1, 2, 4]].any()
