import importlib.metadata
import logging
import pprint
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Tuple

import pandas as pd
import typer
from platformdirs import user_config_dir, user_log_dir
from tomlkit.toml_file import TOMLFile
from typing_extensions import Annotated

from ctdam.entry.casts import Casts
from ctdam.entry.report.data import Hex2pyData
from ctdam.proc import settings

logger = logging.getLogger(__name__)

APPNAME = "pansub"
app = typer.Typer()
config_path = (
    Path(user_config_dir(APPNAME))
    .joinpath(f"{APPNAME.lower()}")
    .with_suffix(".toml")
)
log_file_path = (
    Path(user_log_dir(APPNAME)).joinpath(APPNAME).with_suffix(".log")
)


@app.command()
def init(
    cruise_label: Annotated[
        str, typer.Argument(help="The cruise label of the new submission.")
    ],
    data_dir: Annotated[
        str,
        typer.Argument(
            help="The directory that contains the raw CTD data files."
        ),
    ],
    email_language: Annotated[
        str,
        typer.Option(
            "--language",
            "-l",
            help="The language to write the email in. Needs text building blocks in the config file in that language.",
        ),
    ] = "german",
    auto_process: Annotated[
        bool,
        typer.Option(
            "--auto",
            "-a",
            help="Whether to run convertion.",
        ),
    ] = True,
):
    """
    Prepare a data submission to PANGAEA (runs most of the following commands).
    \n\n- mkdir\n
    - metadata\n
    - data\n
    - email\n
    - status\n

    """
    config_info = config(False)
    # check input information and exit if anything is missing
    for _, file_path in config_info["paths"].items():
        _check_input_path(file_path)

    # read paths from config file
    base_directory = str(config_info["paths"]["base_directory"])
    data_root_dir = Path(config_info["paths"]["data_root_dir"]).joinpath(
        cruise_label
    )
    data_work_dir = Path(config_info["paths"]["data_work_dir"]).joinpath(
        cruise_label
    )
    for directory in ["converted", "calibrated", "raw", "out"]:
        data_work_dir.joinpath(directory).mkdir(parents=True)
    cruise_sub_path = mkdir(base_directory, cruise_label)

    metadata(str(data_root_dir), str(cruise_sub_path))

    if Path(data_dir).is_absolute():
        data_path = Path(data_dir)
    else:
        data_path = data_root_dir.joinpath(data_dir)
    if data_path.exists():
        data(str(data_path), str(data_work_dir.joinpath("raw")))
    else:
        logger.error(f"Could not copy data from path: {data_path}")

    email(cruise_label, language=email_language)
    info = status(cruise_label, status_message="in preparation")
    search_cruise_head_online(info)
    if auto_process:
        con_dir = str(data_work_dir.joinpath("converted"))
        convert(
            data=str(data_work_dir.joinpath("raw")),
            out=con_dir,
        )
        process(
            input_dir=con_dir,
            workflow_file=str(
                Path(base_directory).joinpath(cruise_label, "proc_base.toml")
            ),
            output_dir=str(data_work_dir.joinpath("out")),
        )
    jupyter()


@app.command()
def jupyter():
    config_info = config(False)
    base_directory = Path(config_info["paths"]["base_directory"])
    subprocess.run(
        f"{base_directory.joinpath('.venv', 'bin', 'python')} -m jupyter lab",
        cwd=base_directory,
        shell=True,
        check=True,
    )


@app.command()
def config(
    print_config: Annotated[
        bool,
        typer.Argument(
            help="Whether to print the config information to stout."
        ),
    ] = True,
) -> dict:
    """
    Open configuration file at fixed location.
    """
    if not config_path.exists():
        sys.exit(f"Could not find user config file {config_path}. Aborting.")
    config = TOMLFile(config_path).read()
    if print_config:
        for key, value in config.items():
            if isinstance(value, dict):
                print(f"\n{key}\n")
                for k, v in value.items():
                    print(f"{k}:\t{v}")
            else:
                print(f"{key}:\t{value}")
    return config


def _check_input_path(file_path: Path | str):
    if not Path(file_path).exists():
        message = f"Cannot find the file {file_path}. Aborting."
        logger.error(message)
        sys.exit(message)


@app.command()
def email(
    cruise_label: Annotated[
        str,
        typer.Argument(
            help="The cruise label of the new submission.",
        ),
    ],
    language: Annotated[
        str, typer.Argument(help="The language to send the email in.")
    ] = "german",
):
    """
    Create a draft email to the cruise head.
    """
    config_info = config(False)

    subject = config_info["email"][language]["subject"].format(cruise_label)
    body = config_info["email"][language]["body"].format(cruise_label)

    params = urllib.parse.urlencode({"subject": subject, "body": body})

    # replace '+' with '%20' to ensure spaces are preserved
    params = params.replace("+", "%20")

    webbrowser.open(f"mailto:?{params}")


@app.command()
def metadata(
    data_dir: Annotated[
        str,
        typer.Argument(
            help="The directory holding the metadata files.",
        ),
    ],
    target_dir: Annotated[
        str,
        typer.Argument(
            help="The directory to copy to.",
        ),
    ],
):
    """
    Copies cruise metadata to the working directory.
    """
    try:
        shutil.copy(
            Path(data_dir).joinpath("dshipmeta", "actionlog.json"),
            Path(target_dir),
        )
    except FileNotFoundError as error:
        logger.error(f"Could not copy metadata: {error}")


@app.command()
def data(
    data_dir: Annotated[
        str,
        typer.Argument(
            help="The directory holding the target data.",
        ),
    ],
    target_dir: Annotated[
        str,
        typer.Argument(
            help="The directory to copy to.",
        ),
    ],
    raw_files: Annotated[
        bool, typer.Option("--raw_files", "-r", help="The data types to copy.")
    ] = True,
):
    """
    Copies target data files to the working directory.
    """
    target_suffices = [".hex", ".xmlcon"] if raw_files else [".cnv"]
    for file in [
        f
        for f in Path(data_dir).rglob("*")
        if f.suffix.lower() in list(target_suffices)
    ]:
        try:
            shutil.copy(file, target_dir)
        except Exception as error:
            print(f"Could not copy ctd data: {error}.")
            break


@app.command()
def mkdir(
    base_directory: Annotated[
        str,
        typer.Argument(
            help="The target parent directory containing the template directory.",
        ),
    ],
    cruise_label: Annotated[
        str,
        typer.Argument(
            help="The cruise label of the new submission.",
        ),
    ],
    template_directory: Annotated[
        str,
        typer.Argument(
            help="The path to the template directory inside the base directory."
        ),
    ] = "templates",
) -> Path:
    """
    Create a directory for the new submission from a template.
    """
    cruise_dir = Path(base_directory).joinpath(cruise_label)
    if cruise_dir.exists():
        override = typer.confirm(
            f"Cruise {cruise_label} already exists! Do you want to override the directory?",
            abort=True,
        )
        if override:
            shutil.rmtree(cruise_dir, ignore_errors=True)

    template_dir = Path(base_directory).joinpath(template_directory)
    if not template_dir.exists():
        logger.error(
            f"Could not find the template directory {template_dir}. No initial file directory structure copied."
        )
        return cruise_dir
    shutil.copytree(template_dir, cruise_dir)
    for file in cruise_dir.iterdir():
        if file.suffix in [".qmd", ".ipynb"]:
            file.rename(
                cruise_dir.joinpath(cruise_label).with_suffix(file.suffix)
            )
    return cruise_dir


def _load_cruise_information(
    cruise_csv: str,
    cruise_label: str,
) -> Tuple[pd.DataFrame, pd.DataFrame] | Tuple[None, None]:
    if cruise_csv == "config_path":
        try:
            config_info = config(False)
            cruise_csv = config_info["paths"]["cruise_information_csv"]
        except KeyError:
            sys.exit(
                f"Could not find a valid cruise info path in config: {config_path}"
            )
    try:
        df = pd.read_csv(cruise_csv, delimiter="\t")
    except (pd.errors.ParserError, FileNotFoundError) as error:
        logger.error(f"Could not open cruise information: {error}")
        return (None, None)
    info = df.loc[df.Reise.str.startswith(cruise_label)]
    if info.size == 0:
        logger.error(f"Could find cruise information inside {cruise_csv}.")
        return (None, None)
    return (df, info)


def cruise_info(cruise_label: str, cruise_csv: str = "config_path") -> dict:
    """
    Return the cruise information as structured dictionary.

    Parameters
    ----------
    cruise_label: str :
        The cruise label of the new submission.

    cruise_csv: str :
        The path to the cruise overview .csv file. Uses path from config as default.

    Returns
    -------
    A dictionary holding the parsed information.

    """
    _, info = _load_cruise_information(cruise_csv, cruise_label)
    if not isinstance(info, pd.DataFrame):
        logger.error("Could not set cruise status.")
        return {}
    out_dict = {}
    # initial parsing of all cruise info parameters
    for index, column in enumerate(info.columns):
        out_dict[column.lower()] = str(info.iloc[0, index])
    out_dict = {
        **out_dict,
        **_parse_cruise_head_info(out_dict["fahrtleitung"]),
    }
    pprint.pp(out_dict, indent=4)
    return out_dict


def _parse_cruise_head_info(in_string: str) -> dict:
    out_dict = {}
    if len(in_string) == 0:
        return {}
    in_string = in_string.removeprefix("Chief scientists:")
    if "(" in in_string:
        in_string, institution = in_string.split("(")
        out_dict["institution"] = institution[:-1]
    if "," in in_string:
        name, surname = in_string.split(",")
        out_dict["surname"] = surname
    else:
        name = in_string
    out_dict["name"] = name
    return out_dict


@app.command()
def status(
    cruise_label: Annotated[
        str,
        typer.Argument(
            help="The cruise label of the new submission.",
        ),
    ],
    status_message: Annotated[
        str,
        typer.Argument(help="The status message to set the cruise status to."),
    ] = "in preparation",
    cruise_csv: Annotated[
        str,
        typer.Argument(
            help="The path to the cruise overview .csv file. Uses path from config as default."
        ),
    ] = "config_path",
) -> dict:
    """
    Update status information inside cruise overview file.
    """
    df, _ = _load_cruise_information(cruise_csv, cruise_label)
    if not isinstance(df, pd.DataFrame):
        logger.error("Could not set cruise status.")
        return {}
    if status_message:
        df.loc[df.Reise.str.startswith(cruise_label), ["Status"]] = (
            status_message
        )
        if cruise_csv == "config_path":
            config_info = config(False)
            cruise_csv = config_info["paths"]["cruise_information_csv"]
        df.to_csv(cruise_csv, sep="\t", index=False)
    return cruise_info(cruise_label)


def search_cruise_head_online(cruise_info: dict):
    if "fahrtleitung" not in cruise_info:
        return
    webbrowser.open_new_tab(
        f"https://start.duckduckgo.com/?q={cruise_info['fahrtleitung']}"
    )


@app.command()
def report(
    cruise_label: Annotated[
        str,
        typer.Argument(
            help="The cruise label of the new submission.",
        ),
    ],
    path_to_data: Annotated[
        str,
        typer.Argument(help="The path to the CTD data."),
    ] = "cnvs.pickle",
    ctdclient: Annotated[
        bool,
        typer.Option(
            "--ctdclient",
            "-c",
            help="Whether the data has been acquired using CTD-Client software.",
        ),
    ] = False,
):
    """
    Generate processing report using cnv information.
    """
    cnvs = Hex2pyData(path_to_data, cruise=cruise_label)
    cnvs.read_sensor_info_and_create_report(ctdclient_used=ctdclient)


@app.command()
def convert(
    data: Annotated[
        str, typer.Argument(help="The path to the raw data directory.")
    ] = "raw",
    out: Annotated[
        str,
        typer.Argument(
            help="The directory to store the converted .cnv files in."
        ),
    ] = "converted",
    xmlcon: Annotated[
        str, typer.Argument(help="The directory to look for .xmlcon files.")
    ] = "raw",
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="A name pattern to filter the target .hex files with.",
        ),
    ] = "",
    cruise: Annotated[
        str,
        typer.Option("--cruise", "-c", help="The cruise label of the data."),
    ] = "",
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="Whether to test the config on the first file only.",
        ),
    ] = False,
):
    """
    Converts raw CTD .hex files.
    Needs either a correct path to the target data or a cruise label in order
    to run this command.

    When a path to one specific .hex file is given, the conversion will run
    in 'window' mode, to allow more specific conversion configuration and
    testing of the .psa config file.
    """
    if not Path(data).exists():
        if not cruise:
            sys.exit(
                "Either a correct path to the target data or a cruise label needs to be given, in order to run this command."
            )
        try:
            config_info = config(False)
            base_directory = Path(
                config_info["paths"]["base_directory"]
            ).joinpath(cruise)
        except KeyError:
            sys.exit(
                "Data path could not be found and no base_directory configured. Aborting."
            )
        else:
            data = str(base_directory.joinpath(data))
            out = str(base_directory.joinpath(out))
            xmlcon = str(base_directory.joinpath(xmlcon))
    if test:
        data = str(
            [file for file in Path(data).iterdir() if file.suffix == ".hex"][0]
        )
    else:
        ctds = Casts(data, pattern=pattern)
        for cast in ctds:
            if cast.event_name:
                cast.file_name = cast.event_name
            cast.to_cnv(Path(out).joinpath(cast.file_name).with_suffix(".cnv"))


@app.command()
def process(
    input_dir: Annotated[
        str, typer.Argument(help="The data directory with the target files.")
    ] = "converted",
    workflow_file: Annotated[
        str, typer.Argument(help="A path to a .toml config file.")
    ] = "processing_config.toml",
    output_dir: Annotated[
        str,
        typer.Option(
            "--output_dir",
            "-o",
            help="Overwrite output settings in workflow_file.",
        ),
    ] = "",
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="A name pattern to filter the target files with.",
        ),
    ] = ".cnv",
    cruise: Annotated[
        str,
        typer.Option("--cruise", "-c", help="The cruise label of the data."),
    ] = "",
    test: Annotated[
        bool,
        typer.Option(
            "--test",
            "-t",
            help="Whether to test the config on the first file only.",
        ),
    ] = False,
):
    """
    Applies a processing config to multiple .hex or. cnv files.
    """
    if not Path(input_dir).exists():
        if not cruise:
            sys.exit(
                "Either a correct path to the target data or a cruise label needs to be given, in order to run this command."
            )
        try:
            config_info = config(False)
            base_directory = Path(
                config_info["paths"]["base_directory"]
            ).joinpath(cruise)
        except KeyError:
            sys.exit(
                "Data path could not be found and no base_directory configured. Aborting."
            )
        else:
            input_dir = str(base_directory.joinpath(input_dir))
            workflow_file = str(base_directory.joinpath(workflow_file))
    if test or Path(input_dir).is_file():
        if Path(input_dir).is_file():
            target = input_dir
        else:
            target = str(
                [
                    file
                    for file in Path(input_dir).iterdir()
                    if file.suffix == ".cnv"
                ][0]
            )
    else:
        target = input_dir
    proc_settings = settings.Configuration(workflow_file).data
    if output_dir:
        proc_settings["output_type"] = "cnv"
        proc_settings["output_dir"] = output_dir
    Casts(
        target,
        processing_info=proc_settings,
        pattern=pattern,
        plot=True,
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
    if not log_file_path.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(),
        ],
    )
    app()
