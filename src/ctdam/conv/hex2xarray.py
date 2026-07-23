import logging
from pathlib import Path

import ctdproc
from odf.sbe.io import read_hex
import xarray as xr
import os
from pathlib import Path
import xmltodict
import pandas as pd
from munch import Munch, munchify
import numpy as np
import odf.sbe.accessors 


logger = logging.getLogger(__name__)


def reading_hex(
    hex: Path | str
) -> xr.Dataset:
    
    raw_ds = read_hex(hex)
    return raw_ds


def find_xmlconfig(hex):
    """Generate path to xml config file for current hex file.
    Config file needs to be in the same directory as the hex file. -> aus ctdproc"""
    pp = Path(hex)
    name = pp.stem
    # try upper case filename
    xmlfile = name.upper() + ".XMLCON"
    p = pp.parent
    xmlfile = p.joinpath(xmlfile)
    # use os.listdir to find the actual case of the filename if the upper
    # case did not work.
    if xmlfile.name not in os.listdir(os.path.dirname(xmlfile)):
        xmlfile = name.lower() + ".XMLCON"
        xmlfile = p.joinpath(xmlfile)    

    return xmlfile    


def read_xml_config(hex):
        """
        Parse the companion ``.xmlcon`` calibration file into ``self.cfgp``.

        Locates the xmlcon file alongside the hex file, parses the
        ``SensorArray`` block, and converts coefficient strings to floats.
        Sensors not in the supported set are skipped.
        """
        hexfile = hex
        xmlfile = find_xmlconfig(hexfile)
        try:
            with open(xmlfile) as fd:
                tmp = xmltodict.parse(fd.read())
        except OSError as e:
            raise FileNotFoundError(e.filename)
        sa = tmp["SBE_InstrumentConfiguration"]["Instrument"]["SensorArray"]["Sensor"]
        # parse only valid sensors
        cfg = {}
        ti = 0
        ci = 0
        oi = 0
        for si in sa:
            keys = list(si.keys())
            for k in keys:
                if "@" not in k and k != "NotInUse":
                    if k == "TemperatureSensor":
                        ti += 1
                        kstr = "{}{}".format(k, ti)
                    elif k == "ConductivitySensor":
                        ci += 1
                        kstr = "{}{}".format(k, ci)
                    elif k == "OxygenSensor":
                        oi += 1
                        kstr = "{}{}".format(k, oi)
                    else:
                        kstr = k
                    cfg[kstr] = si.copy()
                    cfg[kstr]["cal"] = munchify(cfg[kstr][k])
                    del cfg[kstr][k]
        cfgp = pd.DataFrame(cfg)
        coefficients = xml_coeffs_to_float(cfgp)
        return coefficients

def xml_coeffs_to_float(cfgp):
    # Convert calibration coefficients to floats.
    keep_strings = [
        "@SensorID",
        "SerialNumber",
        "CalibrationDate",
        "UseG_J",
    ]
    for k in cfgp.keys():
        for ki in cfgp[k].cal.keys():
            if isinstance(cfgp[k]["cal"][ki], str):
                if ki not in keep_strings:
                    cfgp[k]["cal"][ki] = float(cfgp[k]["cal"][ki])
            elif isinstance(cfgp[k]["cal"][ki], list):
                for i, li in enumerate(cfgp[k]["cal"][ki]):
                    for kli in li.keys():
                        cfgp[k]["cal"][ki][i][kli] = float(
                            cfgp[k]["cal"][ki][i][kli]
                        )
        # We can't have None values in the xarray.Dataset later on
        # or otherwise it won't properly write to netcdf. Therefore,
        # convert any None items to 'N/A'
        for ki, v in cfgp[k].cal.items():
            if v is None:
                cfgp[k].cal[ki] = "N/A"

        return cfgp      

# data muss hier serialized_ds = raw_ds.sbe.serialize() sein, also nicht komplette raw

def freq2temp(data, cfgp):
    """Calculate  temperature given frequency and
    temperature calibration structure tcal
    D. Rudnick 01/06/05"""
    freq = data.f0
    tcal = cfgp.TemperatureSensor1.cal
    logf0f = np.log(tcal.F0 / freq)
    temp = (
        1 / (tcal.G + logf0f * (tcal.H + logf0f * (tcal.I + logf0f * tcal.J)))
    ) - 273.15
    return temp



def decode_hex(
    hex: Path | str,
    downcast_only: bool = True,
    **kwargs,
) -> xr.Dataset:
    
    raw_ds = reading_hex(hex)
    serialized_ds = raw_ds.sbe.serialize()
    coefficients = read_xml_config(hex)
    temp = freq2temp(serialized_ds, coefficients)
    return temp

