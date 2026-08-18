import pytest
from conftest import (
    base_path,
    cnv_path,
    hex_path,
    proc_template,
    psa_path,
)

from ctdam.exceptions import NoDataError
from ctdam.parser.casts import Casts


@pytest.mark.long
@pytest.mark.parametrize(
    ("data_path", "pattern", "size"),
    [
        # test cnvs
        (cnv_path, "SO308", 3),
        # test hexes and file type detection
        (base_path, "", 10),
        # test path to single file
        (hex_path.joinpath("MSM138_10-1.hex"), "", 1),
        # test path to directory with no cnv or hex
        (psa_path, "", 0),
    ],
)
class TestCasts:
    @pytest.fixture
    def files(self, data_path, pattern) -> Casts:
        try:
            return Casts(
                path_to_data=data_path,
                processing_info=proc_template,
                pattern=pattern,
            )
        except (NoDataError, FileNotFoundError):
            pytest.skip()

    def test_base(self, files, size, tmp_path):
        assert len(files) + len(files.anomalous_data) == size
        files.to_tsv(tmp_path.joinpath(files.cruise))

    @pytest.mark.xfail(reason="Sensor metadata parsing not implemented yet.")
    def test_sensor_info(self, files, size):
        if size < 4:
            files.read_sensor_info()
            assert len(files.sensor_info) == 1
        else:
            with pytest.warns():
                files.read_sensor_info()
            assert len(files.sensor_info) > size * 0.5
