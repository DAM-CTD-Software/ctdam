import json
import xml.etree.ElementTree as ET
from collections import UserDict
from pathlib import Path

import pandas as pd
import xmltodict
from munch import munchify

from ctdam.exceptions import UnexpectedFileFormat


class XMLFile(UserDict):
    """
    Parent class for XML and psa representation that loads XML as a
    python-internal tree and as a dict.
    """

    def __init__(self, path_to_file: Path | str):
        self.path_to_file = Path(path_to_file)
        self.file_name = self.path_to_file.name
        self.file_dir = self.path_to_file.parents[0]
        self.input = ""
        with open(self.path_to_file, "r") as file:
            for line in file:
                self.input += line
        self.xml_tree = ET.fromstring(self.input)
        self.data = xmltodict.parse(self.input)

    def __str__(self) -> str:
        return str(self.path_to_file)

    def __eq__(self, other) -> bool:
        """
        Allows comparison of two instances of this class.

        Uses the parsed xml information to determine equality.

        Parameters
        ----------
        other: XMLFile
            An instance of this class.

        Returns
        -------
        Whether the given instance and this one are equal.
        """
        return self.data == other.data

    def to_xml(self, file_name=None, file_path=None):
        """
        Writes the dictionary to xml.

        Parameters
        ----------
        file_name : str
            the original files name (Default value = self.file_name)
        file_path : pathlib.Path
            the directory of the file (Default value = self.file_dir)
        """
        file_path = self.file_dir if file_path is None else file_path
        file_name = self.file_name if file_name is None else file_name
        with open(Path(file_path).joinpath(file_name), "w") as file:
            file.write(xmltodict.unparse(self.data, pretty=True))

    def to_json(self, file_name=None, file_path=None):
        """
        Writes the dictionary representation of the XML input to a json
        file.

        Parameters
        ----------
        file_name : str
            the original files name (Default value = self.file_name)
        file_path : pathlib.Path
            the directory of the file (Default value = self.file_dir)
        """
        file_path = self.file_dir if file_path is None else file_path
        file_name = self.file_name if file_name is None else file_name
        with open(Path(file_path).joinpath(file_name + ".json"), "w") as file:
            json.dump(self.data, file, indent=4)


class XMLCONFile(XMLFile):
    """A representation of a Sea-Bird .XMLCON file."""

    def __init__(self, path_to_file):
        super().__init__(path_to_file)
        self.sensor_info = self.get_sensor_info()
        self.coefficients = self.read_xml_config()

    def read_xml_config(self):
        """
        Parse the companion ``.xmlcon`` calibration file into ``self.cfgp``.

        Locates the xmlcon file alongside the hex file, parses the
        ``SensorArray`` block, and converts coefficient strings to floats.
        Sensors not in the supported set are skipped.
        """
        sa = self.data["SBE_InstrumentConfiguration"]["Instrument"][
            "SensorArray"
        ]["Sensor"]
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

                    if "@index" in si:
                        cfg[kstr]["channel"] = int(si["@index"]) + 1
                    elif "@Channel" in si:
                        cfg[kstr]["channel"] = int(si["@Channel"])

        cfgp = pd.DataFrame(cfg)
        coefficients = self.xml_coeffs_to_float(cfgp)
        return coefficients

    def xml_coeffs_to_float(self, cfgp):
        """Returns float-parsed xml coefficients."""
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
                        try:
                            cfgp[k]["cal"][ki] = float(cfgp[k]["cal"][ki])
                        except ValueError:
                            continue
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

    def get_sensor_info(self) -> list[dict]:
        """
        Creates a multilevel dictionary, dropping the first four dictionaries,
        to retrieve pure sensor information.
        """
        try:
            sensors = self.data["SBE_InstrumentConfiguration"]["Instrument"][
                "SensorArray"
            ]["Sensor"]
        except KeyError as error:
            raise UnexpectedFileFormat("XMLCON", error)
        else:
            # create a tidied version of the xml-parsed sensor dict
            sensor_names = []
            tidied_sensor_list = []
            for entry in sensors:
                sensor_key = list(entry.keys())[-1]
                if not sensor_key.endswith(("Sensor", "Meter")):
                    continue
                sensor_name = sensor_key.removesuffix("Sensor")
                # the wetlab sensors feature a suffix _Sensor
                sensor_name = sensor_name.removesuffix("_")
                # assuming, that the first sensor in the xmlcon is also on the
                # first sensor strand, the second occurence of the name is
                # suffixed with '2'
                if sensor_name in sensor_names:
                    sensor_name += "2"
                sensor_names.append(sensor_name)
                # move the calibration info one dictionary level up
                calibration_info = entry[sensor_key]
                # build the new dictionary
                try:
                    new_dict = {
                        "Channel": str(int(entry["@index"]) + 1),
                        "SensorName": sensor_name,
                        **calibration_info,
                    }
                except TypeError:
                    new_dict = {
                        "Channel": entry["@Channel"],
                        "SensorName": sensor_name,
                        "Info": calibration_info,
                    }
                tidied_sensor_list.append(new_dict)
            return tidied_sensor_list


class PsaFile(XMLFile):
    """A representation of a .psa file."""

    def __init__(self, path_to_file):
        super().__init__(path_to_file)
