import pytest
from conftest import cnv_path, hex_path

from ctdam.parser.read_ctd_data import parse
from ctdam.qc.range_checks import DEFAULT_RANGE_LIMITS, RangeLimit


@pytest.mark.parametrize(
    "file_path",
    [
        hex_path / "EMB356_11-1.hex",
        cnv_path / "EMB356_11-1.cnv",
    ],
)
# for pressure and oxygen still missing
def test_pressure_uncertainty_is_applied_during_parsing(file_path):
    ds = parse(file_path)

    assert ds.uncertainty.get("temperature") == 0.001
    assert ds.uncertainty.get("conductivity") == 0.003


@pytest.mark.parametrize(
    "file_path",
    [
        hex_path / "EMB379_000-00_SF_0001.hex",
        cnv_path / "EMB394_006-01_CTD_0006_1m.cnv",
    ],
)
def test_flow_interval_check_runs_after_hex_and_cnv_parsing(
    file_path, monkeypatch
):
    """Test that HEX and CNV parsing flags primary channel data with bad flow.
    Bad flow flags primary temperature, conductivity, salinity and SBE43 oxygen.
    """
    monkeypatch.setitem(
        DEFAULT_RANGE_LIMITS,
        "flow_meter",
        # setting flow range to flag all flow meter readings bad
        RangeLimit("flow_meter", minimum=100),
    )
    ds = parse(file_path).sel(sensor="primary")

    assert (ds.flow_meter_qc == 4).all()
    for name in (
        "temperature_qc",
        "conductivity_qc",
        "oxygen_qc",
        "salinity_qc",
    ):
        assert (ds[name] == 4).all()
