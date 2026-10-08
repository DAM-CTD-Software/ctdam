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


@pytest.mark.parametrize("file_path", hex_path.glob("*.hex"))
def test_oxygen_uncertainty(file_path):
    ds = parse(file_path)
    if "oxygen" not in ds:
        pytest.skip("Dataset has no oxygen parameter.")

    expected_ds = ds.copy()
    expected_ds.add.teos10_vars()

    if "absolute_salinity" not in expected_ds:
        pytest.skip("Dataset cannot calculate oxygen saturation.")

    expected = 0.02 * expected_ds.gsw.O2sol().max(skipna=True).item()

    assert ds.uncertainty.get("oxygen") == pytest.approx(expected)


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
