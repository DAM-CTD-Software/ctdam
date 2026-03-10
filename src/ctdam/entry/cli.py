import importlib.metadata
import logging
import shutil
import sys
from pathlib import Path

from ctdam import APPNAME
from ctdam.conv import decode_hex
from ctdam.parser import CTDData

try:
    import typer
    from platformdirs import user_config_dir, user_log_dir
    from typing_extensions import Annotated
except (ImportError, ModuleNotFoundError, TypeError):
    sys.exit(
        "The 'cli' extra is required to use this feature. Install with: uv pip install ctdam[cli]"
    )

from ctdam.parser import HexCollection
from ctdam.proc.procedure import Procedure
from ctdam.proc.settings import Configuration
from ctdam.proc.utils import default_seabird_exe_path

logger = logging.getLogger(__name__)


log_file_path = (
    Path(user_log_dir(APPNAME)).joinpath(APPNAME).with_suffix(".log")
)
config_dir = Path(user_config_dir(APPNAME))
VIS_CONFIG_NAME = "vis_config.toml"
app = typer.Typer()


@app.callback()
def common(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
):
    ctx.obj = {"verbose": verbose}
    if not log_file_path.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(),
        ],
    )


@app.command()
def run(
    processing_target: Annotated[
        str,
        typer.Argument(
            help="The target file to process.",
        ),
    ],
    path_to_configuration: Annotated[
        str,
        typer.Argument(
            help="The path to the configuration file.",
        ),
    ],
    procedure_fingerprint_directory: Annotated[
        str,
        typer.Option(
            "--fingerprint",
            "-f",
            help="The path to a fingerprint directory. If none given, no fingerprints will be created.",
        ),
    ] = "",
    file_type_dir: Annotated[
        str,
        typer.Option(
            "--file-type",
            "-t",
            help="The path to a file type directory. If none given, the files will not be separated into file type directories.",
        ),
    ] = "",
    plot: Annotated[
        bool,
        typer.Option(
            "--plot",
            "-p",
            help="Whether to plot the file after processing.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="An option to allow more verbose output.",
        ),
    ] = False,
):
    """
    Processes one target file using the given procedure workflow file.
    """
    path_to_config = Path(path_to_configuration)
    if path_to_config.exists():
        config = Configuration(path_to_config)
    else:
        sys.exit("Could not find the configuration file.")
    config["input"] = processing_target
    Procedure(
        configuration=config,
        procedure_fingerprint_directory=procedure_fingerprint_directory,
        file_type_dir=file_type_dir,
        plot=plot,
        verbose=verbose,
    )


@app.command()
def convert(
    input_dir: Annotated[
        str,
        typer.Argument(
            help="The data directory with the target .hex files.",
        ),
    ],
    psa_path: Annotated[
        str,
        typer.Option(
            "--psa_path",
            "-s",
            help="The path to the .psa for datcnv. If none given, hex2py will be used for conversion.",
        ),
    ] = "",
    output_dir: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="The directory to store the converted .cnv files in.",
        ),
    ] = "",
    xmlcon_dir: Annotated[
        str,
        typer.Option(
            "--xmlcons",
            "-x",
            help="The directory to look for .xmlcon files.",
        ),
    ] = "",
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="A name pattern to filter the target .hex files with.",
        ),
    ] = "",
) -> list[Path]:
    """
    Converts a list of Sea-Bird raw data files (.hex) to .cnv files.
    Does either use an explicit list of paths or searches for all .hex files in
    the given directory.
    """
    if not output_dir:
        output_dir = input_dir
    if not xmlcon_dir:
        xmlcon_dir = input_dir
    hexes = HexCollection(
        path_to_files=Path(input_dir),
        pattern=pattern,
        file_suffix="hex",
        path_to_xmlcons=Path(xmlcon_dir),
    )
    resulting_cnvs = []
    if psa_path:
        proc_config = {
            "output_dir": output_dir,
            "modules": {
                "datcnv": {"psa": psa_path},
            },
        }
        procedure = Procedure(
            proc_config,
            auto_run=False,
            verbose=True if len(hexes) == 1 else False,
        )
    with typer.progressbar(hexes, label="Converting files:") as progress:
        for hex in progress:
            try:
                if psa_path:
                    result = procedure.run(hex.path_to_file)
                else:
                    result = decode_hex(hex)
                    file_name = result.metadata_source.file_name
                    result.to_cnv(
                        Path(output_dir)
                        .joinpath(file_name)
                        .with_suffix(".cnv")
                    )
            except Exception as e:
                logger.error(f"Failed to convert: {hex.path_to_file}, {e}")
            else:
                resulting_cnvs.append(result)

    return resulting_cnvs


@app.command()
def batch(
    input_dir: Annotated[
        str,
        typer.Argument(
            help="The data directory with the target files.",
        ),
    ],
    config: Annotated[
        str,
        typer.Argument(
            help="Either an explicit config as dict or a path to a .toml config file.",
        ),
    ],
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="A name pattern to filter the target files with.",
        ),
    ] = ".hex",
) -> list[Path] | list[CTDData]:
    """
    Applies a processing config to multiple .hex or. cnv files.
    """
    resulting_cnvs = []
    if isinstance(config, dict):
        proc_config = config
    else:
        proc_config = Configuration(config)
    procedure = Procedure(proc_config, auto_run=False)
    with typer.progressbar(
        Path(input_dir).rglob(f"*{pattern}*"), label="Processing files:"
    ) as progress:
        for file in progress:
            try:
                result = procedure.run(file)
            except Exception as e:
                logger.error(f"Error when processing {file}: {e}")
            else:
                resulting_cnvs.append(result)
    return resulting_cnvs


try:
    from processing.gui.procedure_config_view import run_gui
except ImportError:
    pass
else:

    @app.command()
    def edit(file: str):
        """
        Opens a procedure workflow file in GUI for editing.
        """
        run_gui(file)


@app.command()
def show(file: typer.FileText):
    """
    Display the contents of a procedure workflow file.
    """
    content = file.read()
    print(content, end="")


try:
    from processing.visualize import basic_bokeh_plot, cruise_plots
except ImportError:
    pass
else:

    @app.command()
    def plot(
        cnv: Annotated[
            str,
            typer.Argument(
                help="The path to the cnv file.",
            ),
        ] = "",
        output_directory: Annotated[
            str,
            typer.Option(
                "--output_directory",
                "-d",
                help="The path to the output_directory.",
            ),
        ] = "html",
        output_name: Annotated[
            str,
            typer.Option(
                "--output_name",
                "-o",
                help="The name of the output .html .",
            ),
        ] = "",
        save: Annotated[
            bool,
            typer.Option(
                "--save",
                "-s",
                help="Whether to save the plot as a .html file.",
            ),
        ] = False,
        metadata: Annotated[
            bool,
            typer.Option(
                "--metadata",
                "-m",
                help="Whether to display .cnv file metadata in the plot.",
            ),
        ] = False,
    ):
        """
        Plot a cnv file.
        """
        if output_name:
            save = True
        basic_bokeh_plot(
            ctd_data=cnv,
            output_name=str(output_name),
            output_directory=output_directory,
            print_plot=save,
            metadata=metadata,
        )

    @app.command()
    def vis(
        directory: Annotated[
            str,
            typer.Argument(
                help="The path to the target directory holding the .cnv files.",
            ),
        ] = "",
        output_directory: Annotated[
            str,
            typer.Option(
                "--output_directory",
                "-d",
                help="The path to the output directory.",
            ),
        ] = "html",
        output_name: Annotated[
            str,
            typer.Option(
                "--output_name",
                "-o",
                help="The name of the output .html file.",
            ),
        ] = "main.html",
        embed_contents: Annotated[
            bool,
            typer.Option(
                "--embed_contents",
                "-e",
                help="Whether to embed the target .html files or just link to them.",
            ),
        ] = False,
        html_title: Annotated[
            str,
            typer.Option(
                "--html_title",
                "-t",
                help="The title that will be used inside the .html file.",
            ),
        ] = "",
        overwrite: Annotated[
            bool,
            typer.Option(
                "--overwrite",
                "-w",
                help="Whether to overwrite existing plot .html files.",
            ),
        ] = False,
        no_new_plots: Annotated[
            bool,
            typer.Option(
                "--no_new_plots",
                "-p",
                help="Whether no new plot .html files should be created.",
            ),
        ] = False,
        size_limit: Annotated[
            int,
            typer.Option(
                "--size_limit",
                "-l",
                help="""File size limit in MB to which plots will be created.
             Very large files can slow down the visualizer considerabily.""",
            ),
        ] = 10,
        filter: Annotated[
            str,
            typer.Option(
                "--filter",
                "-f",
                help="The files to select for visualization.",
            ),
        ] = "",
        file_type: Annotated[
            str,
            typer.Option(
                "--file_type",
                "-y",
                help="The data type to plot.",
            ),
        ] = "cnv",
    ):
        """
        Create a main html that incorporates the individual .html plots.
        """

        _check_config_path()

        output_path = cruise_plots(
            directory=directory,
            output_directory=output_directory,
            output_name=output_name,
            embed_contents=embed_contents,
            html_title=html_title,
            overwrite=overwrite,
            no_new_plots=no_new_plots,
            size_limit=size_limit,
            filter=filter,
            config_path=config_dir.joinpath(VIS_CONFIG_NAME),
            file_type=file_type,
        )
        print(f"Created main .html file: {output_path}")


def _check_config_path():
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    vis_config_path = config_dir.joinpath(VIS_CONFIG_NAME)
    if not vis_config_path.exists():
        shutil.copy(
            Path(__file__).parent.joinpath(VIS_CONFIG_NAME), vis_config_path
        )


@app.command()
def check():
    """
    Assures that all requirements to use this tool are met.
    """
    if not default_seabird_exe_path().exists():
        print(
            "You are missing a Sea-Bird Processing installation or are not using the default path. Please ensure that a valid installation can be found in Program Files (x86)/Sea-Bird/SBEDataProcessing-Win32/"
        )
    else:
        print("All set, you are ready to go.")
    try:
        from processing.gui.procedure_config_view import run_gui  # noqa: F401
    except ImportError:
        print(
            "\nIf you want to use a GUI to edit your ctd processing workflows, install the additional dependencies via 'uvx--from ctdam[gui] ctdam'"
        )
    try:
        from processing.visualize import (  # noqa: F401
            basic_bokeh_plot,
            cruise_plots,
        )
    except ImportError:
        print(
            "\nIf you want to use the plotting capabilities, install the additional dependencies via 'uvx--from ctdam[vis] ctdam'"
        )


@app.command()
def log(
    number_of_entries: Annotated[
        int, typer.Argument(help="The number of entries to print.")
    ] = 30,
):
    """
    Prints the last x entries of the log file.
    """
    if not log_file_path.exists():
        return
    lines = log_file_path.read_text().splitlines()
    last_x_lines = lines[-number_of_entries:]
    for line in last_x_lines:
        print(line)


@app.command()
def version():
    """
    Displays the version number of this software.
    """
    print(importlib.metadata.version("ctdam"))


if __name__ == "__main__":
    app()
