import logging
import multiprocessing
from pathlib import Path
from typing import List

import xarray as xr
from tqdm import tqdm

from ctdam.exceptions import MissingParameterError
from ctdam.parser.read_ctd_data import read_ctd_data
from ctdam.proc.workflow import Workflow


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
        elif len(target_data) == 0:
            return target_data[0].proc.workflow(other_settings=proc_settings)
        else:
            raise TypeError("Could not determine processing target.")


def _process_item(a, proc_settings):
    try:
        return Workflow(a, proc_settings).output
    except MissingParameterError as error:
        logger.error(
            f"Could not perform processing workflow on {a.attrs['path_to_source_file']}: {error}"
        )
