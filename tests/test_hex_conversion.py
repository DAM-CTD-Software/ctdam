from pathlib import Path

import pytest
import xarray as xr
from conftest import hex_path

from ctdam.parser.read_ctd_data import read_hex


@pytest.fixture(params=hex_path.glob("*.hex"), scope="class")
def ds(request):
    try:
        return read_hex(request.param)
    # TODO: implement time gap handling
    except ValueError:
        return


class TestHexConversion:
    def test_calling(self, ds):
        pass

    @pytest.mark.skip(reason="Not implemented")
    def test_cnv_export(self, ds, create_files):
        if not isinstance(ds, xr.Dataset):
            pytest.skip()
        file_path = (
            hex_path / f"out_test_{Path(ds.attrs['path_to_source_file']).name}"
        )
        ds.export.to_cnv(file_path)
        if not create_files:
            file_path.unlink()
