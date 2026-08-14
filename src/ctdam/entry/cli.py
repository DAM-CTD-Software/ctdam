import importlib.metadata
import logging
import shutil
import sys
from pathlib import Path

import xarray as xr
from tomlkit import dumps
from tomlkit.toml_file import TOMLFile

from ctdam import APPNAME
from ctdam.proc.entry import process

try:
    import typer
    from platformdirs import user_config_dir, user_log_dir
    from typing_extensions import Annotated
except (ImportError, ModuleNotFoundError, TypeError):
    sys.exit(
        "The 'cli' extra is required to use this feature. Install with: uv pip install ctdam[cli]"
    )

from ctdam.proc.settings import Configuration
from ctdam.proc.utils import default_seabird_exe_path

logger = logging.getLogger(__name__)


log_file_path = (
    Path(user_log_dir(APPNAME)).joinpath(APPNAME).with_suffix(".log")
)
config_dir = Path(user_config_dir(APPNAME))
config_path = config_dir.joinpath(f"{APPNAME.lower()}").with_suffix(".toml")
if not config_path.exists():
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.touch()
    with open(config_path, "w") as file:
        file.write(dumps({"modules": []}))
config = TOMLFile(config_path).read()
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


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Show version and exit."
    ),
):
    if version:
        print(importlib.metadata.version("ctdam"))
        raise typer.Exit()


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
    process(input=processing_target, other_settings=config.data)


@app.command()
def convert(
    input_dir: Annotated[
        str,
        typer.Argument(
            help="The data directory with the target .hex files.",
        ),
    ],
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
):
    """
    Converts a list of Sea-Bird raw data files (.hex) to .cnv files.
    Does either use an explicit list of paths or searches for all .hex files in
    the given directory.
    """
    if not output_dir:
        output_dir = input_dir
    if not xmlcon_dir:
        xmlcon_dir = input_dir
    output_data = process(input_dir)
    for array in output_data:
        assert isinstance(array, xr.Dataset)
        file_name = array.attrs["path_to_source_file"]
        array.export.to_cnv((output_dir / file_name).with_suffix(".cnv"))


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
):
    """
    Applies a processing config to multiple .hex or. cnv files.
    """
    if isinstance(config, dict):
        proc_config = config
    else:
        proc_config = Configuration(config).data
    process(input_dir, other_settings=proc_config)


try:
    from ctdam.entry.gui import run_gui
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
    from ctdam.vis import basic_bokeh_plot, cruise_plots
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
            Path(__file__).parents[1].joinpath("vis", VIS_CONFIG_NAME),
            vis_config_path,
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
        from ctdam.entry.gui import run_gui  # noqa: F401
    except ImportError:
        print(
            "\nIf you want to use a GUI to edit your ctd processing workflows, install the additional dependencies via 'uvx --from ctdam[gui] ctdam'"
        )
    try:
        from ctdam.vis import (  # noqa: F401
            basic_bokeh_plot,
            cruise_plots,
        )
    except ImportError:
        print(
            "\nIf you want to use the plotting capabilities, install the additional dependencies via 'uvx --from ctdam[vis] ctdam'"
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
