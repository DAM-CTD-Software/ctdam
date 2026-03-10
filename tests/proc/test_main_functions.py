import pytest
from conftest import (
    check_and_remove_file,
    hex_path,
)

from ctdam.parser.ctddata import CTDData

try:
    from ctdam.entry.cli import batch, convert
except ImportError:
    pass
else:

    @pytest.mark.long
    def test_convert_function(tmp_path):
        pattern = "SO308-2"
        result = convert(
            input_dir=str(hex_path),
            output_dir=str(tmp_path),
            pattern=pattern,
        )
        assert len(result) == 3
        for ctd_data in result:
            check_and_remove_file(
                tmp_path.joinpath(ctd_data.file_name).with_suffix(".cnv")
            )

    @pytest.mark.long
    def test_batch_processing_function():
        pattern = "SO308-2*.hex"
        proc_config = {
            "output_type": "internal",
            "modules": {
                "wildedit_geomar": {},
                "celltm": {},
            },
        }
        result = batch(
            input_dir=str(hex_path),
            config=proc_config,
            pattern=pattern,
        )
        assert len(result) == 3
        for file in result:
            assert isinstance(file, CTDData)
            assert len(file.processing_steps) == 3
