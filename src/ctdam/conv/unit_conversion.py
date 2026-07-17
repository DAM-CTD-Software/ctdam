import gsw
import numpy as np


def oxygen_mlperl_to_umolperkg(
    data: np.ndarray,
    potential_density: np.ndarray,
) -> np.ndarray:
    return oxygen_mlperl_to_umolperl(data) / (potential_density + 1000)


def oxygen_mlperl_to_umolperl(data: np.ndarray) -> np.ndarray:
    factor = 44660
    return data * factor


def oxygen_umolperkg_to_umolperl(
    data: np.ndarray,
    potential_density: np.ndarray,
) -> np.ndarray:
    return data * potential_density / 1000


def oxygen_umolperl_to_umolperkg(
    data: np.ndarray,
    potential_density: np.ndarray,
) -> np.ndarray:
    return data / (potential_density + 1000)


def get_potential_density(
    practical_salinity: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
    longitude: np.ndarray,
    latitude: np.ndarray,
) -> np.ndarray:
    absolute_salinity = gsw.SA_from_SP(
        SP=practical_salinity,
        p=pressure,
        lon=longitude,
        lat=latitude,
    )
    conservative_temperature = gsw.conversions.CT_from_t(
        SA=absolute_salinity,
        t=temperature,
        p=pressure,
    )
    return gsw.density.sigma0(
        SA=absolute_salinity,
        CT=conservative_temperature,
    )
