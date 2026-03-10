import pytest
from conftest import btl_path, cnv_path, hex_path

from ctdam.parser import (
    BottleFile,
    CnvCollection,
    CnvFile,
    DataFile,
    FileCollection,
    HexCollection,
    XMLCONFile,
    get_collection,
)


@pytest.mark.parametrize(
    ("path", "suffix", "file_type", "num_of_files"),
    [
        (btl_path, ".btl", BottleFile, 1),
    ],
)
class TestCollections:
    @pytest.fixture
    def files(
        self,
        path: str,
        suffix: str,
        file_type: DataFile,
        num_of_files: int,
    ):
        files = get_collection(
            path_to_files=path,
            file_suffix=suffix,
        )
        return files

    @pytest.fixture
    def df(self, files: FileCollection):
        return files.get_collection_dataframe()

    def test_collected_dataframe(self, files: FileCollection):
        assert (
            files.df.size
            == sum([file.df.shape[0] for file in files])
            * files.df_list[0].shape[1]
        )

    def test_cast_specific_info_added(
        self,
        files: FileCollection,
        num_of_files: int,
    ):
        df = files.get_collection_dataframe(
            files.get_dataframes(event_log=True, coordinates=True)
        )

        assert len(df.Event.unique()) == num_of_files
        assert len(df.Longitude.unique()) == num_of_files
        assert len(df.Latitude.unique()) == num_of_files

    def test_cnv_specifics(self, files: FileCollection):
        if files.file_suffix != "cnv":
            pytest.skip("cnv-specific test")
        assert files.data_meta_info["c0mS/cm"]["name"] == "Conductivity"
        df = files.tidy_collection_dataframe(files.df)
        assert df.isna().sum().sum() == 0
        assert files.array.shape == (
            sum([file.parameters.full_data_array.shape[0] for file in files]),
            files[0].parameters.full_data_array.shape[1],
        )
        assert files.array.shape == files.df.shape
        assert files.get_dataframes(time_correction=True)


def test_mixed_processing_steps():
    cnvs = CnvCollection(cnv_path, only_metadata=True)
    with pytest.warns(UserWarning):
        cnvs.get_processing_steps()


class TestHexCollections:
    @pytest.fixture
    def files(self) -> FileCollection:
        files = HexCollection(
            path_to_files=hex_path,
            pattern="SO308-2",
            sorting_key=lambda file: int(file.stem.split("_")[1]),
        )
        return files

    def test_pattern_handling(self, files):
        assert len(files) == 3

    def test_xmlcon_matching(self, files):
        xmlcon = XMLCONFile(hex_path.joinpath("SO308-2.XMLCON"))
        for file in files:
            assert file.xmlcon == xmlcon
