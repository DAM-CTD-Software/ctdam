import pytest
from conftest import (
    base_path,
    btl_path,
    cnv_path,
    hex_path,
    proc_template,
    psa_path,
    test_cnv,
)

from ctdam.exceptions import NoDataError
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
from ctdam.parser.casts import Casts


@pytest.mark.parametrize(
    ("path", "suffix", "file_type", "num_of_files"),
    [
        (btl_path, ".btl", BottleFile, 2),
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
        assert files.df.size == sum(
            [file.df.shape[0] for file in files]
            # ) * max([file.df.shape[1] for file in files])
        ) * len(list(set().union(*[file.df.columns for file in files])))

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


@pytest.mark.long
@pytest.mark.parametrize(
    ("data_path", "pattern", "size"),
    [
        # test cnvs
        (cnv_path, "SO308", 3),
        # test hexes and file type detection
        (base_path, "", 11),
        # test file type detection with pattern
        (base_path, "cnv", 10),
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

    def test_sensor_info(self, files, size):
        if size < 4:
            files.read_sensor_info()
            assert len(files.sensor_info) == 1
        else:
            with pytest.warns():
                files.read_sensor_info()
            assert len(files.sensor_info) > size * 0.5


def test_ctddata_in_casts(tmp_path):
    cnv = CnvFile(test_cnv)
    casts = Casts(
        ctd_data=[cnv.to_ctd_data()],
        plot=True,
        show_plot=False,
        plot_dir=tmp_path,
    )
    assert tmp_path.joinpath(test_cnv.name).with_suffix(".html").exists()
    casts.read_sensor_info()
    assert len(casts.sensor_info) == 1
