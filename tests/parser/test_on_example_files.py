from datetime import datetime
from pathlib import Path

import pytest
from conftest import btl_path, cnv_path, hex_path

from ctdam.parser import BottleFile, CnvFile, HexFile


@pytest.mark.parametrize(
    "file",
    [file for file in cnv_path.glob("*.cnv")],
)
class TestExampleFiles:
    @pytest.fixture
    def cnv(self, file: Path, run_long_tests: bool):
        if (not run_long_tests) and (file.stat().st_size > 5 * 1000000):
            pytest.skip(f"Skipping long cnv: {file}")
        try:
            cnv = CnvFile(
                file,
                create_dataframe=True,
            )
        except FileNotFoundError as error:
            pytest.skip(str(error))
        else:
            return cnv

    def test_found_start_time(self, cnv: CnvFile):
        assert isinstance(cnv.start_time, datetime)

    def test_calculate_full_time(self, cnv):
        assert (cnv.absolute_time_calculation()) == (
            len([p for p in cnv.parameters.keys() if p.startswith("time")]) > 0
        )

    def test_ctd_data2cnv_conversion(self, cnv):
        ctd_data = cnv.to_ctd_data()
        test_cnv = cnv.path_to_file.with_stem(
            f"conversion_test_{cnv.path_to_file.stem}"
        )
        ctd_data.to_cnv(test_cnv)
        # test seabird metadata
        assert cnv.sbe9_data == CnvFile(test_cnv).sbe9_data
        # test custom metadata
        assert cnv.metadata == CnvFile(test_cnv).metadata
        # test sensor xml
        assert cnv.sensor_data == CnvFile(test_cnv).sensor_data
        # test processing_steps
        assert cnv.processing_steps == CnvFile(test_cnv).processing_steps
        test_cnv.unlink()

    @pytest.mark.skip("Parameter needs a little rewrite.")
    def test_cnv_export_from_np_array(
        self,
        cnv: CnvFile,
    ):
        if cnv.parameters.duplicate_columns:
            assert True
        else:
            new_cnv_data = cnv.array2cnv()
            assert new_cnv_data == cnv.data

    def test_processing_step_extraction(self, cnv: CnvFile):
        assert cnv.processing_steps

    def test_sample_rate_retrieval(self, cnv):
        if cnv.file_name == "MSM140_1":
            target_rate = 1
        else:
            target_rate = 24
        assert cnv.parameters.sample_rate == target_rate


@pytest.mark.parametrize(
    "filename",
    [filename for filename in hex_path.glob("*.hex")],
)
class TestHexFiles:
    @pytest.fixture
    def hex(self, filename: str) -> HexFile:
        return HexFile(filename)

    def test_read_only_metadata(self, hex: HexFile):
        assert len(hex.data) == 0


@pytest.mark.parametrize(
    "filename",
    [filename for filename in btl_path.rglob("*.btl")],
)
def test_btl_reading(filename):
    btl = BottleFile(filename)
    assert "Timestamp" in btl.df.columns
