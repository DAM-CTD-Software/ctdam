import pytest
from conftest import cnv_path, hex_path

from ctdam.parser.read_ctd_data import parse
from ctdam.qc.range_checks import DEFAULT_RANGE_LIMITS, RangeLimit


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
    """Test that HEX and CNV parsing automatically flags data affected by bad flow
    by setting all flow flags to bad we expect temperature, conductivity and oxygen
    to be all flagged bad"""
    monkeypatch.setitem(
        DEFAULT_RANGE_LIMITS,
        "flow_meter",
        # setting flow range to flag all flow meter readings bad
        RangeLimit("flow_meter", minimum=100),
    )
    ds = parse(file_path)

    assert (ds.flow_meter_qc == 4).all()
    for name in ("temperature", "conductivity", "oxygen"):
        assert (ds[f"{name}_qc"] == 4).all()
