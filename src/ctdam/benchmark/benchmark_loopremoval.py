from pathlib import Path

import numpy as np

from ctdam.parser import CnvFile
from ctdam.proc.modules.seabird_functions import LoopRemoval

CNV_DIR = Path("../../../sbs_data/cnv")
_algo = LoopRemoval()


def load_datasets() -> list[dict]:
    """Return a list of dicts with keys: name, pressure, sample_interval."""
    datasets = []

    for path in sorted(CNV_DIR.glob("*.cnv")):
        try:
            ctd = CnvFile(path).to_ctd_data()
            pressure = ctd["prDM"].data
            sample_interval = 1.0 / ctd.sample_rate
            datasets.append(
                {
                    "name": path.name,
                    "pressure": pressure,
                    "sample_interval": sample_interval,
                }
            )
        except Exception as e:
            print(f"skipping {path.name}:{e}")

    return datasets


def _run_time_dependent(pressure: np.ndarray, delta=0.05):
    return _algo.time_dependent_loop_removal(pressure, delta)


def _run_jens(
    pressure: np.ndarray,
    sample_interval: float,
    precut_period: int = 5,
    cut_period: int = 10,
    mean_speed_percent: int = 20,
    delay: int = 2,
    filter_order: int = 4,
):
    return _algo.jens_loop_removal(
        pressure,
        sample_interval,
        precut_period,
        cut_period,
        mean_speed_percent,
        delay,
        filter_order,
    )


def flag_rate(flags: np.ndarray) -> float:
    return float(flags.sum()) / len(flags)


def report_flag_rate(datasets: list[dict]) -> None:
    print("running flag rate metric")
    print("1.0 = all points are flaged, 0.0 = nothing flagged")
    print(f"{'File':<35} {'time_dep':>10} {'jens':>10}")
    print("-" * 57)
    for ds in datasets:
        flags_td = _run_time_dependent(ds["pressure"])
        flags_jens = _run_jens(ds["pressure"], ds["sample_interval"])
        print(
            f"{ds['name']:<35} {flag_rate(flags_td):>10.3f} {flag_rate(flags_jens):>10.3f}"
        )


def monotonicity_score(pressure: np.ndarray, flags: np.ndarray) -> float:
    """Fraction of consecutive pairs in the unflagged pressure that are increasing. Heavily biased towards
    time dependent approach.
    """
    remaining = pressure[~flags]
    if len(remaining) < 2:
        return float("nan")
    diffs = np.diff(remaining)
    return float((diffs > 0).sum()) / len(diffs)


def report_monotonicity(datasets: list[dict]) -> None:
    print("running monotonicity metric")
    print(
        "1.0 = monotonically increasing pressure, 0 = not increasing or constant"
    )
    print(f"{'File':<35} {'time_dep':>10} {'jens':>10}")
    print("-" * 57)
    for ds in datasets:
        flags_td = _run_time_dependent(ds["pressure"])
        flags_jens = _run_jens(ds["pressure"], ds["sample_interval"])

        score_td = monotonicity_score(ds["pressure"], flags_td)
        score_jens = monotonicity_score(ds["pressure"], flags_jens)
        print(f"{ds['name']:<35} {score_td:>10.4f} {score_jens:>10.4f}")


def jaccard(flags_a: np.ndarray, flags_b: np.ndarray) -> float:
    """
    Calculate the Jaccard similarity (proportion of overlap) between two sets of flags
    """
    intersection = int((flags_a & flags_b).sum())
    union = int((flags_a | flags_b).sum())
    if union == 0:
        return 1.0
    return intersection / union


def report_overlap(datasets: list[dict]) -> None:
    print("running overlap metric")
    print("(1.0 = full overlap, 0.0 = no overlap)")
    print(f"{'File':<35} {'jaccard':>10}")
    print("-" * 47)
    for ds in datasets:
        flags_td = _run_time_dependent(ds["pressure"])
        flags_jens = _run_jens(ds["pressure"], ds["sample_interval"])

        print(f"{ds['name']:<35} {jaccard(flags_td, flags_jens):>10.4f}")


if __name__ == "__main__":
    datasets = load_datasets()

    report_flag_rate(datasets)
    report_monotonicity(datasets)
    report_overlap(datasets)
