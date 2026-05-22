import logging

import numpy as np
import pytest
from conftest import test_cnv

from ctdam.parser import CnvFile, Parameters

logger = logging.getLogger(__name__)

# TODO: rethink this
data_table_length = 3067


@pytest.fixture
def cnv():
    return CnvFile(test_cnv)


@pytest.fixture
def parameters(cnv: CnvFile):
    return Parameters(cnv.data, cnv.data_table_description)


def test_parameter_metadata_loading(parameters: Parameters):
    spans = parameters.get_spans()
    assert isinstance(spans, list)
    for parameter in parameters.values():
        assert isinstance(parameter.metadata, dict)
        assert isinstance(parameter.span, tuple)
        parameter.data[0] = parameter.span[1] + 1
    assert spans != parameters.get_spans()


@pytest.mark.parametrize(
    "data, metadata, name",
    [
        (
            np.full(fill_value=1, shape=data_table_length, dtype=float),
            {},
            "something",
        ),
        ("EMB999_123-12", {"shortname": "event", "name": "event"}, "event"),
    ],
)
def test_addition_of_new_parameters(
    parameters: Parameters,
    data: np.ndarray | str | int | float,
    metadata: dict,
    name: str,
):
    new_parameter = parameters.create_parameter(
        data=data,
        metadata=metadata,
        name=name,
    )
    assert new_parameter.name in parameters
    assert new_parameter.data.shape[0] == data_table_length
    assert len(new_parameter.metadata) == 5


def test_parameter_removal(parameters):
    parameters.remove_parameter("prDM")
    assert "prDM" not in parameters
