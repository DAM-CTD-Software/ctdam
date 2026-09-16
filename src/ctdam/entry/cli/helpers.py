import importlib.metadata
import os
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import typer
import xarray as xr

from ctdam.entry.casts import Casts
from ctdam.exceptions import NoDataError
from ctdam.parser import PARSEABLE_FILE_FORMATS
from ctdam.parser.read_ctd_data import parse
from ctdam.proc.workflow import Workflow


def _collect_sources(target: Path, pattern: str = "") -> list[Path]:
    """
    Resolve the data files to operate on from a target path.

    Parameters
    ----------
    target : Path
        A data file or a directory of data files.
    pattern : str
        Only keep files whose name contains this text.

    Returns
    -------
    A sorted list of data file paths.
    """
    if target.is_file():
        return [target]
    if not target.is_dir():
        # TODO Log
        raise typer.BadParameter(
            f"Target is neither file nor directory: {target}"
        )
    sources = sorted(
        file
        for file in target.iterdir()
        if file.is_file()
        and file.suffix in PARSEABLE_FILE_FORMATS
        and pattern in file.name
    )
    if not sources:
        # TODO log
        raise typer.BadParameter(
            f"No parseable CTD data files found in {target}"
        )
    return sources


def _convert_one(source: Path):
    """
    Parse a single file into a dataset.

    Parameters
    ----------
    source : Path
        The file to parse.

    Returns
    -------
    A tuple of the source path, the dataset (or None) and an error message
    (or None).
    """
    try:
        return (source, parse(source), None)
    except Exception as error:
        return (source, None, str(error))


def _process_one(source: Path, config: dict):
    """
    Run a processing workflow on a single file.

    Parameters
    ----------
    source : Path
        The file to parse and process.
    config : dict
        The processing workflow configuration.

    Returns
    -------
    A tuple of the source path, the dataset (or None) and an error message
    (or None).
    """
    try:
        dataset = Workflow(parse(source), config).output
        return (source, dataset, None)
    except Exception as error:
        return (source, None, str(error))


def _target_path(
    dataset: xr.Dataset,
    output_dir: Path,
    output_name: str,
    extension: str = "cnv",
) -> Path:
    """
    Build the output path for a processed dataset.

    Parameters
    ----------
    dataset : xr.Dataset
        The dataset to write.
    output_dir : Path
        The directory to write into.
    output_name : str
        An explicit file name, or an empty string to use the source name.
    extension : str
        The output file extension, without a leading dot.

    Returns
    -------
    The path of the output file.
    """
    source = Path(dataset.attrs["path_to_source_file"])
    file_name = f"{output_name or source.stem}.{extension}"
    return output_dir / file_name


def _save_outputs(
    results,
    output_dir: Path,
    output_name: str,
    on_self_overwrite: str,
    file_type: str = "cnv",
) -> tuple[int, int, list[str]]:
    """
    Write all successful results to disk.

    Parameters
    ----------
    results : list[tuple]
        Worker result tuples of (source, dataset, error).
    output_dir : Path
        The directory to write into.
    output_name : str
        An explicit file name, or an empty string to use the source name.
    on_self_overwrite : str
        Either 'skip' or 'error', for outputs that would overwrite an input.
    file_type : str
        The output format, either 'nc' or 'cnv'.

    Returns
    -------
    A tuple of the number of written files, the number of skipped files and
    a list of error messages.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    errors = []
    for source, dataset, error in results:
        if error:
            errors.append(f"{source}: {error}")
            continue
        target = _target_path(dataset, output_dir, output_name, file_type)
        source_file = Path(dataset.attrs["path_to_source_file"])
        if target.resolve() == source_file.resolve():
            if on_self_overwrite == "skip":
                skipped += 1
            else:
                errors.append(
                    f"{target} would overwrite the input file, "
                    "choose a different --output-dir."
                )
            continue
        try:
            if file_type == "nc":
                dataset.to_netcdf(target)
            else:
                dataset.export.to_cnv(file_path=target)
        except Exception as error:
            errors.append(f"{target}: {error}")
            continue
        written += 1
    return written, skipped, errors


def _write_cruise_bottles(target: Path, bottle_log, output) -> tuple:
    """
    Collect all bottles closed during a cruise into a .csv file.

    Parameters
    ----------
    target : Path
        A cast file or a directory of casts.
    bottle_log : Path
        Directory holding the .bl files, if not next to the data.
    output : Path
        Path of the resulting .csv file.

    Returns
    -------
    A tuple of the bottle DataFrame and the output path.
    """

    try:
        casts = Casts(path_to_data=target, use_multiprocessing=False)
    except (NoDataError, FileNotFoundError) as error:
        raise typer.BadParameter(str(error))
    target = Path(target)
    output_dir = target if target.is_dir() else target.parent
    output = Path(output) if output else output_dir / "cruise_bottles.csv"
    frame = casts.get_cruise_bottles(
        path_to_bl_files=bottle_log, path_to_write=output
    )
    return frame, output


def _print_summary(
    written, skipped, errors, total, action: str, output_dir: Path
):
    """
    Report the outcome of a batch operation and set the exit code.

    Parameters
    ----------
    written : int
        The number of files written.
    skipped : int
        The number of files skipped.
    errors : list[str]
        The error messages collected.
    total : int
        The number of files that were attempted.
    action : str
        A label for the operation, e.g. 'Conversion'.
    output_dir : Path
        The directory the files were written to.
    """
    for error in errors:
        typer.echo(f"Error: {error}", err=True)
    if skipped:
        typer.echo(f"Skipped {skipped} file(s), already in .cnv format.")
    if written:
        typer.echo(
            f"{action}: wrote {written} of {total} file(s) to {output_dir}."
        )
    if errors:
        raise typer.Exit(1)
    if not written and not skipped:
        raise typer.Exit(1)


def _roff_escape(text: str) -> str:
    """
    Escape plain text for use inside a roff man page.

    Parameters
    ----------
    text : str
        The text to escape.

    Returns
    -------
    The escaped text.
    """
    return text.replace("\\", "\\\\").replace("-", "\\-")


def _command_doc_blocks(app) -> list[str]:
    """
    Generate roff subsections from the registered Typer commands.

    Parameters
    ----------
    app : typer.Typer
        The Typer application to introspect.

    Returns
    -------
    A list of roff source lines.
    """
    out = []

    def walk(typer_app, prefix: str) -> None:
        """Render all commands of one app, recursing into groups."""
        commands = sorted(
            typer_app.registered_commands,
            key=lambda info: info.name or info.callback.__name__,
        )
        for info in commands:
            name = (info.name or info.callback.__name__).replace("_", "-")
            heading = f"ctdam {prefix} {name}".strip()
            out.append(f".SS {heading}")
            out.append(f"\\fB{heading}\\fR [\\fIOPTIONS\\fR]")
            out.append(".br")
            description = (info.help or info.short_help or "").strip()
            if description:
                out.append(_roff_escape(description))
                out.append(".br")
            out.append(f"See \\fB{heading} \\-\\-help\\fR for options.")
            out.append("")

    walk(app, "")
    for group in app.registered_groups:
        walk(group.typer_instance, group.name)
    return out


def _manpage_text(app) -> str:
    """
    Assemble the complete roff source of the ctdam manual page.

    Parameters
    ----------
    app : typer.Typer
        The Typer application to introspect.

    Returns
    -------
    The man page as a string.
    """
    version = importlib.metadata.version("ctdam")
    month = date.today().strftime("%B %Y")
    commands = "\n".join(_command_doc_blocks(app))
    return f"""\
.TH CTDAM 1 "{month}" "ctdam {version}" "User Commands"
.SH NAME
ctdam \\- parse, process and plot CTD data
.SH SYNOPSIS
\\fBctdam\\fR [\\fIOPTIONS\\fR] \\fICOMMAND\\fR [\\fIARGS\\fR]...
.PP
\\fBctdam man\\fR opens this manual in a terminal pager.

.SH DESCRIPTION
ctdam converts raw Conductivity-Temperature-Depth (CTD) data from
Sea-Bird (.hex, .cnv) and Sea & Sun (.TOB) sources into standardized
CF-compliant datasets, applies Sea-Bird style processing workflows to
them, and creates interactive HTML plots.
.PP
Every command carries its own short help, shown with:
.PP
\\fBctdam\\fR \\fICOMMAND\\fR \\fI\\-\\-help\\fR

.SH COMMANDS
{commands}
.SH GLOBAL OPTIONS
.TP
\\fB\\-v, \\-\\-verbose\\fR
Show debug level logging.

.SH EXIT STATUS
.TP
.B 0
Success, or nothing needed to be done.
.TP
.B 1
At least one file could not be processed or written.
.TP
.B 2
The command line was used incorrectly.

.SH EXAMPLES
Convert every raw file in a directory to .cnv:
.PP
\\fBctdam convert\\fR sbs_data/hex/EMB356_11-1.hex
.PP
Apply a workflow to a single hex cast:
.PP
\\fBctdam process\\fR sbs_data/hex/EMB356_11-1.hex workflow.toml
.PP
Plot all .cnv files and open the overview in a browser:
.PP
\\fBctdam plot\\fR sbs_data/hex/EMB356_11-1.hex \\-\\-open
.PP
Create a new workflow template and view it:
.PP
\\fBctdam config new\\fR my_workflow.toml
.PP
\\fBctdam config show\\fR my_workflow.toml

.SH FILES
.TP
.I .hex, .cnv, .TOB, .XMLCON
CTD raw data and sensor configuration files.
.TP
.I workflow.toml
Processing workflow definitions used by the process command.

.SH SEE ALSO
The full ctdam documentation and Python API:
.UR https://dam-ctd-software.github.io/ctdam
.UE
"""


def _show_manpage(app) -> None:
    """
    Render the manual page with man(1).

    Parameters
    ----------
    app : typer.Typer
        The Typer application to introspect.
    """
    if not shutil.which("man"):
        raise typer.BadParameter(
            "'man' was not found. Install man-db to view the manual page."
        )
    fd, path = tempfile.mkstemp(prefix="ctdam.", suffix=".1")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(_manpage_text(app))
        subprocess.run(["man", "-l", path])
    finally:
        os.unlink(path)


_TEMPLATE = """\
# ctdam processing workflow
# The target data is given via the 'process' command.
output_dir = "."
output_type = "internal"

[modules.wildedit_geomar]
[modules.wfilter]
[modules.alignctd]
[modules.celltm]
[modules.binavg]
"""
