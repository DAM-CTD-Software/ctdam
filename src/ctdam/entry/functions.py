import functools
import logging
import multiprocessing
from pathlib import Path
from typing import List

import xarray as xr
from tqdm import tqdm

from ctdam.exceptions import MissingParameterError
from ctdam.parser.read_ctd_data import read_ctd_data
from ctdam.proc.workflow import Workflow
from ctdam.vis.visualize import basic_bokeh_plot, create_main_html

logger = logging.getLogger(__name__)


def process(
    input: Path | str | xr.Dataset | list = "",
    modules: dict | list = [
        "loop_removal",
        "wildedit_geomar",
        "wfilter",
        "alignctd",
        "celltm",
        "binavg",
    ],
    other_settings: dict = {},
    use_multiprocessing: bool = True,
    **kwargs,
) -> xr.Dataset | List[xr.Dataset]:
    # check and handle input appropiately
    input = Path(input) if isinstance(input, str) else input
    target_data = []
    if isinstance(input, Path):
        if input.is_dir():
            files = sorted(list(input.iterdir()))
            if use_multiprocessing:
                with multiprocessing.Pool() as pool:
                    target_data = list(
                        tqdm(
                            pool.imap_unordered(read_ctd_data, files),
                            total=len(files),
                            desc="Cast conversion",
                            unit="cast",
                        )
                    )
            else:
                target_data = [read_ctd_data(file) for file in files]

    elif isinstance(input, xr.Dataset):
        target_data = [input]
    elif isinstance(input, list):
        target_data = [e for e in input if isinstance(e, xr.Dataset)]
    else:
        raise TypeError(f"Unsupported input data for processing {type(input)}")
    # build proc_settings dictionary
    proc_settings = {**other_settings, **kwargs}
    if not "modules" in other_settings.keys():
        if isinstance(modules, list):
            modules = {k: {} for k in modules}
        proc_settings["modules"] = modules
    # run workflow
    #

    if use_multiprocessing and len(target_data) > 1:
        with multiprocessing.Pool() as pool:
            return list(
                tqdm(
                    pool.starmap(
                        _process_item,
                        [(a, proc_settings) for a in target_data],
                    ),
                    total=len(target_data),
                    desc="Processing",
                    unit="cast",
                )
            )
    else:
        if len(target_data) > 1:
            return [Workflow(ds, proc_settings).output for ds in target_data]
        elif len(target_data) == 1:
            target_data[0].proc.workflow(other_settings=proc_settings)
            return target_data
        else:
            raise TypeError("Could not determine processing target.")


def _process_item(a, proc_settings):
    try:
        return Workflow(a, proc_settings).output
    except MissingParameterError as error:
        logger.error(
            f"Could not perform processing workflow on {a.attrs['path_to_source_file']}: {error}"
        )


def plot(
    input: Path | str | xr.Dataset | list,
    output_directory: Path | str = "",
    output_name: str = "",
    embed_contents: bool = False,
    html_title: str = "",
    overwrite: bool = False,
    no_new_plots: bool = False,
    size_limit: int = 10,
    filter: str = "",
    show_html: bool = True,
    config_path: Path | str = "vis_config.toml",
    file_type: str = "cnv",
    use_multiprocessing: bool = True,
    **kwargs,
):
    """
    Run basic_bokeh_plot and create_main_html and handle inputs.

    Parameters
    ----------
    directory: Path | str
        The directory to look for data files to plot (Default value = "")
    output_directory: Path | str
        The directory to save .html file to (Default value = "html")
    output_name: str
        The name of the main html file (Default value = "main.html")
    embed_contents: bool
        Whether to embed plot htmls into main html (Default value = False)
    html_title: str
        The header of the main html (Default value = "")
    overwrite: bool
        Whether to overwrite an existing main html (Default value = False)
    no_new_plots: bool
        Whether to not overwrite existing plot htmls (Default value = False)
    size_limit: int
        Data file size limit in MB (Default value = 10)
    filter: str
        A search filter for files (Default value = "")
    show_html: bool
        Whether to open main html in browser (Default value = True)
    config_path: Path | str
        The path to vis configuration info (Default value = "vis_config.toml")
    file_type: str
        The file type to search for (Default value = "cnv")
    use_multiprocessing: bool
        Whether to use paralleliztion for plotting (Default value = True)
    """
    input = Path(input) if isinstance(input, str) else input
    targets = []
    # one plain file to plot
    if isinstance(input, xr.Dataset):
        output_name = (
            output_name if output_name else input.attrs["path_to_source_file"]
        )
        basic_bokeh_plot(
            ctd_data=input,
            print_plot=True,
            output_name=output_name,
            output_directory=output_directory,
            show_plot=True,
            config_path=config_path,
            **kwargs,
        )
        return
    elif isinstance(input, Path):
        # plot every file inside the directory, that fullfils filter, and
        # collect these inside one main html file
        if input.is_dir():
            if not no_new_plots:
                output_directory = (
                    Path(output_directory)
                    if str(output_directory)
                    else Path(input)
                )
                if not output_directory.exists():
                    output_directory.mkdir()
                if not file_type:
                    file_type = ".cnv"

                file_type = (
                    f".{file_type}" if not file_type[0] == "." else file_type
                )
                file_filter = f"*{filter}*" if filter else "*"

                for file in Path(input).glob(f"{file_filter}{file_type}"):
                    if file.stat().st_size > size_limit * 1000000:
                        logger.info(
                            f"{file} above size limit of {size_limit}MB"
                        )
                        continue
                    if (
                        Path(output_directory)
                        .joinpath(file.name)
                        .with_suffix(".html")
                        .exists()
                    ) and not overwrite:
                        continue
                    targets.append(file)

    # also main main html after individual plots
    elif isinstance(input, list):
        targets = [d for d in input if isinstance(d, xr.Dataset)]

    else:
        raise TypeError(f"Unsupported input data for plotting {type(input)}")

    arguments = {
        "output_directory": output_directory,
        "print_plot": True,
        "metadata": True,
        "show_plot": False,
        "config_path": config_path,
        **kwargs,
    }

    func = functools.partial(basic_bokeh_plot, **arguments)

    # run collection plotting code
    if use_multiprocessing:
        with multiprocessing.Pool() as pool:
            pool.map(func, targets)
    else:
        for file in targets:
            func(file)

    output_name = output_name if output_name else "main.html"

    create_main_html(
        directory_path=output_directory,
        output_name=output_name,
        output_directory=output_directory,
        embed_contents=embed_contents,
        title=html_title,
        show_html=show_html,
    )
