import logging
import sys
from pathlib import Path

try:
    import typer
except (ImportError, ModuleNotFoundError):
    sys.exit("The 'cli' extra is required. Install it with: uv add ctdam[cli]")

from ctdam.entry.cli import helpers
from ctdam.proc.modules import available_modules
from ctdam.proc.settings import Configuration

app = typer.Typer(
    help="Parse, process and plot CTD data.", no_args_is_help=True
)
config_app = typer.Typer(
    help="Create and inspect processing workflow config files.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show debug level logging."
    ),
):
    """
    Configure logging for the command line interface.

    Parameters
    ----------
    verbose : bool
        Whether to emit debug level log messages.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command(help="Parse raw data files into standardized .nc or .cnv files.")
def convert(
    target: Path = typer.Argument(
        help="A data file (.hex, .cnv, .TOB) or a directory of data files."
    ),
    output_dir: Path = typer.Option(
        "",
        "--output-dir",
        "-o",
        help="Directory for the processed file(s). Defaults to the input "
        " location.",
    ),
    file_type: str = typer.Option(
        "nc",
        "--format",
        "-f",
        help="Output format: 'nc' (default) or 'cnv'.",
    ),
    pattern: str = typer.Option(
        "",
        "--pattern",
        "-p",
        help="Only convert files whose name contains this text.",
    ),
):
    """
    Parse raw data files into standardized .nc or .cnv files.

    Parameters
    ----------
    target : Path
        A data file or a directory of data files.
    output_dir : Path
        Directory for the resulting files. Defaults to the input location.
    file_type : str
        Output format, either 'nc' or 'cnv'.
    pattern : str
        Only convert files whose name contains this text.
    """
    if file_type not in ("nc", "cnv"):
        raise typer.BadParameter("--format must be 'nc' or 'cnv'.")
    sources = helpers._collect_sources(target, pattern)
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = target if target.is_dir() else target.parent
    results = [helpers._convert_one(source) for source in sources]
    written, skipped, errors = helpers._save_outputs(
        results,
        output_dir,
        "",
        on_self_overwrite="skip",
        file_type=file_type,
    )
    helpers._print_summary(
        written, skipped, errors, len(sources), "Conversion", output_dir
    )


@app.command(
    help="Apply processing workflow to one file or all files in a directory."
)
def process(
    target: Path = typer.Argument(
        help="A data file (.hex, .cnv, .TOB) or a directory of data files."
    ),
    workflow: Path = typer.Argument(
        help="A workflow .toml file that defines the processing modules."
    ),
    output_dir: Path = typer.Option(
        "",
        "--output-dir",
        "-o",
        help="Directory for the resulting .cnv files. Defaults to the current "
        "directory.",
    ),
    output_name: str = typer.Option(
        "",
        "--output-name",
        "-n",
        help="Name of the output file. Only valid for a single target file.",
    ),
):
    """
    Apply a processing workflow to one file or all files in a directory.

    Parameters
    ----------
    target : Path
        A data file or a directory of data files.
    workflow : Path
        A workflow .toml file that defines the processing modules.
    output_dir : Path
        Directory for the resulting .cnv files. Defaults to the current
        directory.
    output_name : str
        Name of the output file. Only valid for a single target file.
    """
    sources = helpers._collect_sources(target)
    if output_name and len(sources) > 1:
        raise typer.BadParameter(
            "--output-name can only be used with one file."
        )
    if not workflow.exists():
        raise typer.BadParameter(f"Workflow file not found: {workflow}")
    config = Configuration(workflow).data
    if "modules" not in config:
        raise typer.BadParameter(
            f"{workflow} contains no [modules.*] section. "
            "See 'ctdam config new' for a template."
        )

    config = {**config, "output_type": "internal"}
    output_dir = Path(output_dir) if output_dir else Path(".")
    results = [helpers._process_one(source, config) for source in sources]
    written, skipped, errors = helpers._save_outputs(
        results, output_dir, output_name, on_self_overwrite="error"
    )
    helpers._print_summary(
        written, skipped, errors, len(sources), "Processing", output_dir
    )


@app.command(
    help="Create interactive .html plots for a single file or a directory."
)
def plot(
    target: Path = typer.Argument(
        help="A data file (.hex, .cnv, .TOB) or a directory of data files."
    ),
    output_dir: Path = typer.Option(
        "html",
        "--output-dir",
        "-o",
        help="Directory for the resulting .html files.",
    ),
    output_name: str = typer.Option(
        "",
        "--output-name",
        "-n",
        help="Name of the overview .html file for a directory of plots.",
    ),
    title: str = typer.Option(
        "",
        "--title",
        "-t",
        help="Header shown inside the overview .html file.",
    ),
    file_type: str = typer.Option(
        "cnv",
        "--file-type",
        "-f",
        help="File extension to search for inside a directory.",
    ),
    filter: str = typer.Option(
        "",
        "--filter",
        "-p",
        help="Only plot files whose name contains this text.",
    ),
    size_limit: int = typer.Option(
        10,
        "--size-limit",
        "-s",
        help="Skip files larger than this size in MB.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-w",
        help="Overwrite existing .html plot files.",
    ),
    open: bool = typer.Option(
        False,
        "--open",
        help="Open the plots in a web browser.",
    ),
):
    """
    Create interactive .html plots for a single file or a directory.

    Parameters
    ----------
    target : Path
        A data file or a directory of data files.
    output_dir : Path
        Directory for the resulting .html files.
    output_name : str
        Name of the overview .html file for a directory of plots.
    title : str
        Header shown inside the overview .html file.
    file_type : str
        File extension to search for inside a directory.
    filter : str
        Only plot files whose name contains this text.
    size_limit : int
        Skip files larger than this size in MB.
    overwrite : bool
        Whether to overwrite existing .html plot files.
    open : bool
        Whether to open the plots in a web browser.
    """
    if target.is_file():
        from ctdam.vis import basic_bokeh_plot

        basic_bokeh_plot(
            ctd_data=target,
            print_plot=True,
            output_name=output_name,
            output_directory=str(output_dir),
            metadata=True,
            show_plot=open,
        )
        typer.echo(f"Plot written to {output_dir}.")
    elif target.is_dir():
        from ctdam.entry.functions import plot as plot_files

        plot_files(
            input=target,
            output_directory=output_dir,
            output_name=output_name,
            html_title=title,
            file_type=file_type,
            filter=filter,
            size_limit=size_limit,
            overwrite=overwrite,
            no_new_plots=False,
            show_html=open,
            use_multiprocessing=False,
        )
        typer.echo(f"Plots written to {output_dir}.")
    else:
        raise typer.BadParameter(
            f"Target is neither file nor directory: {target}"
        )


@app.command(help="List all built-in processing modules.")
def modules():
    """List all built-in processing modules."""
    for module in available_modules:
        info = module().info.strip().replace("\n", " ")
        typer.echo(f"{module().names[0]:<16} {info}")


@app.command(help="Create a cruise bottle file from all casts.")
def bottle_file(
    target: Path = typer.Argument(help="A cast file or a directory of casts."),
    bottle_log: Path = typer.Option(
        "",
        "--bottle-log",
        "-b",
        help="Directory holding the .bl files, if not next to the data.",
    ),
    output: Path = typer.Option(
        "",
        "--output",
        "-o",
        help="Path of the resulting .csv file.",
    ),
):
    """
    Create a cruise bottle file from all casts.

    Parameters
    ----------
    target : Path
        A cast file or a directory of casts.
    bottle_log : Path
        Directory holding the .bl files, if not next to the data.
    output : Path
        Path of the resulting .csv file.
    """
    frame, path = helpers._write_cruise_bottles(target, bottle_log, output)
    typer.echo(f"Wrote {len(frame)} bottles to {path}.")


@app.command(help="Open the ctdam manual in terminal pager.")
def man():
    """Open the ctdam manual in terminal pager."""
    helpers._show_manpage(app)


@config_app.command("new", help="Write a template workflow file to disk.")
def config_new(
    path: Path = typer.Argument(help="Path of the new workflow .toml file."),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite the file if it already exists.",
    ),
):
    """
    Write a template workflow file to disk.

    Parameters
    ----------
    path : Path
        Path of the new workflow .toml file.
    force : bool
        Whether to overwrite the file if it already exists.
    """
    if path.exists() and not force:
        raise typer.BadParameter(
            f"{path} already exists, use --force to overwrite."
        )
    path.write_text(helpers._TEMPLATE)
    typer.echo(f"Wrote template workflow to {path}.")


@config_app.command("show", help="Print the contents of a workflow file.")
def config_show(
    path: Path = typer.Argument(help="Path of the workflow .toml file."),
):
    """
    Print the contents of a workflow file.

    Parameters
    ----------
    path : Path
        Path of the workflow .toml file.
    """
    if not path.exists():
        raise typer.BadParameter(f"Workflow file not found: {path}")
    typer.echo(path.read_text(), nl=False)


if __name__ == "__main__":
    app()
