from __future__ import annotations

from enum import IntEnum


class SeaDataNetFlag(IntEnum):
    """
    SeaDataNet-style quality flag values.
    """

    NO_QC = 0
    GOOD = 1
    PROBABLY_GOOD = 2
    PROBABLY_BAD = 3
    BAD = 4
    CHANGED = 5
    BELOW_DETECTION = 6
    IN_EXCESS = 7
    INTERPOLATED = 8
    MISSING = 9


FLAG_MEANINGS: dict[int, str] = {
    SeaDataNetFlag.NO_QC: "no quality control performed",
    SeaDataNetFlag.GOOD: "good value",
    SeaDataNetFlag.PROBABLY_GOOD: "probably good value",
    SeaDataNetFlag.PROBABLY_BAD: "probably bad value",
    SeaDataNetFlag.BAD: "bad value",
    SeaDataNetFlag.CHANGED: "changed value",
    SeaDataNetFlag.BELOW_DETECTION: "value below detection",
    SeaDataNetFlag.IN_EXCESS: "value in excess",
    SeaDataNetFlag.INTERPOLATED: "interpolated value",
    SeaDataNetFlag.MISSING: "missing value",
}


DEFAULT_INITIAL_FLAG = SeaDataNetFlag.NO_QC
FLAG_DTYPE = "int8"


__all__ = [
    "SeaDataNetFlag",
    "FLAG_MEANINGS",
    "DEFAULT_INITIAL_FLAG",
    "FLAG_DTYPE",
]