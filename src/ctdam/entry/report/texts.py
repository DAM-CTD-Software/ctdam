import datetime
import importlib.metadata
import re
import subprocess
import sys
from pathlib import Path

from pylatex import (
    Command,
    Document,
    Head,
    MiniPage,
    Package,
    PageStyle,
    Section,
    StandAloneGraphic,
    Subsection,
    Table,
    Tabu,
)
from pylatex.utils import NoEscape, bold, escape_latex
from tomlkit.toml_file import TOMLFile


class ProcessingReport(Document):
    def __init__(
        self,
        cruise_label: str,
        sensor_info: list,
        processing_modules: set[str],
        text_blocks_file: (
            Path | str
        ) = "text_blocks_ctd_processing_report.toml",
        validated: bool = False,
        ctdclient_used: bool = False,
        header_logo_1: Path | str | None = None,
        header_logo_2: Path | str | None = None,
    ):
        geometry_options = {
            "margin": "2.5cm",
            "bottom": "3.5cm",
        }
        super().__init__(geometry_options=geometry_options)

        self.cruise_label = cruise_label.replace("_", "/")
        self.text_blocks = TOMLFile(text_blocks_file).read()
        self.ship_name = self.extract_ship_name()
        self.title = self.make_title()
        self.sensor_info = sensor_info
        self.ctdclient_used = ctdclient_used
        self.abstract = self.make_abstract()
        self.processing_modules = processing_modules
        self.validated = validated
        try:
            author_info = self.text_blocks["author"]
            assert isinstance(author_info, dict)
            general_text = self.text_blocks["general_text"]
            assert isinstance(general_text, dict)
            processing_info = self.text_blocks["processing"]
            assert isinstance(processing_info, dict)
        except AssertionError:
            sys.exit(
                "Missing text information in text block file. Check example file for further assistance."
            )
        general_text = (
            general_text
            | self.text_blocks["validated"][str(validated).lower()]
        )
        author = author_info["author_name"]
        author_email = author_info["author_email"]
        author_institute = author_info["institute_name"]
        author_address = author_info["institute_address"]

        self.packages.append(Package("setspace"))
        self.packages.append(Package("float"))
        self.packages.append(
            Package("hyperref", options=["hidelinks", "colorlinks=false"])
        )
        self.packages.append(
            Package("biblatex", options=["style=numeric", "backend=biber"])
        )
        if header_logo_1 and header_logo_2:
            self.create_header(header_logo_1, header_logo_2)

        # create title section
        self.preamble.append(
            Command(
                "title",
                NoEscape(bold(f"{self.title}") + "\\\\Data Processing Report"),
            )
        )
        self.preamble.append(
            Command(
                "author",
                NoEscape(
                    f"{author}\\\\{author_institute}\\\\{author_address}\\\\{
                        author_email
                    }"
                ),
            )
        )
        self.preamble.append(
            Command("date", datetime.datetime.today().strftime("%d.%m.%Y"))
        )
        self.preamble.append(
            Command(
                "addbibresource",
                arguments=[NoEscape(r"report.bib")],
            )
        )
        self.append(NoEscape(r"\maketitle"))
        self.append(NoEscape(r"\setstretch{1.5}"))

        self.fill_document(general_text, processing_info)
        self.append(Command("printbibliography"))

        self.build_pdf()

    def build_pdf(self):
        report_name = (
            f"{self.cruise_label.replace('/', '_')}_processing_report"
        )
        self.generate_tex(report_name)
        subprocess.run(["pdflatex", report_name + ".tex"])
        subprocess.run(["biber", report_name])
        subprocess.run(["pdflatex", report_name + ".tex"])

    def extract_ship_name(self) -> str:
        mapper = {k: v["name"] for k, v in self.text_blocks["ship"].items()}
        try:
            ship_label = re.search("[A-Z]+", self.cruise_label).group()
            assert ship_label in list(mapper.keys())
            assert ship_label in list(self.text_blocks["ship"].keys())
        except (AttributeError, AssertionError):
            sys.exit("Cruise label has an unknown format.")
        else:
            # map citation keys to ship name, to cite ship manual
            ship_citations = {
                k: v["citation"] for k, v in self.text_blocks["ship"].items()
            }
            self.ship_citation = ship_citations[ship_label]
            return mapper[ship_label]

    def make_title(self) -> str:
        return f"Physical oceanography during {self.ship_name} cruise {self.cruise_label}"

    def make_abstract(self) -> str:
        abstract = f"Physical oceanography data was acquired by a ship-based Seabird SBE911plus CTD-Rosette system onboard {self.ship_name} during research cruise {self.cruise_label}. The CTD system is comprised of a Seabird SBE911plus including dual respectively redundant sensor and pump packages. The SBE11plus Deck Unit remains on board in a laboratory and supplies on one hand power to the SBE9plus underwater unit, on the other hand data telemetry between the SBE9plus and a measurement PC. The SBE9plus underwater unit itself holds a pressure sensor and is interfacing with"
        sensor_names = [
            sensor["SensorName"] for sensor in self.sensor_info if sensor
        ]
        # handle one or two oxygen sensors
        if (
            len(
                [
                    sensor
                    for sensor in sensor_names
                    if sensor.startswith("Oxygen")
                ]
            )
            == 2
        ):
            abstract += " dual SBE3 temperature, SBE4 conductivity and SBE43 oxygen sensors, as well as two SBE5 pumps to provide a pumped water supply past each sensor."
        else:
            abstract += " dual SBE3 temperature and SBE4 conductivity sensor as well as two SBE5 pumps to provide a pumped water supply past each sensor. Additionally, a single SBE43 oxygen sensor is attached."
        # handle FLNTU sensor pack
        if "Fluorometer" in sensor_names:
            abstract += " The system also carries an optical FLNTU sensor to measure a combination of back-scattering, turbidity, and chlorophyll-a."
        # handle PAR sensor
        if "PAR/Irradiance" in sensor_names:
            abstract += " To quantify the photo-synthetically active radiation a PAR sensor is installed as well."
        # handle CTD-Client usage
        if self.ctdclient_used:
            abstract += " The measurement process has been supported by the CTD-Client \\cite{michels_ctd-client_2026} a program made available by the German Marine Research Alliance \\cite{dam_german_2026}, that standardizes the measurement, adds metadata to data files and runs flexible processing workflows using the ctdam python package \\cite{michels_ctdam_2026}."

        return NoEscape(abstract)

    def create_header(self, header_logo_1, header_logo_2):
        self.header_logo_1 = Path(header_logo_1)
        self.header_logo_2 = Path(header_logo_2)
        first_page = PageStyle("header")

        # Header image
        with first_page.create(Head("L")) as header_left:
            with header_left.create(
                MiniPage(width=NoEscape(r"0.49\textwidth"), pos="c")
            ) as logo_wrapper:
                logo_wrapper.append(
                    StandAloneGraphic(
                        image_options="width=120px",
                        filename=self.header_logo_1,
                    )
                )
        self.preamble.append(first_page)

    def hyperlink(self, url, text):
        text = escape_latex(text)
        return NoEscape(r"\href{" + url + "}{" + text + "}")

    def fill_document(self, general_text: dict, processing_info: dict):
        self.append(Command("tableofcontents"))
        self.append(NoEscape(r"\newpage"))
        with self.create(Section("Introduction")):
            self.append(
                NoEscape(
                    f"This document serves as data processing report of the research cruise {self.cruise_label} conducted with {self.ship_name} \\cite{{{self.ship_citation}}}. It provides the individual steps conducted to generate the data file that belongs to the PANGAEA \\cite{{felden_pangaea_2023}} entry with the same title as this document."
                )
            )
            if not self.validated and len(general_text["intro_validation"]):
                self.append("\n")
                self.append(general_text["intro_validation"])
        with self.create(Section("CTD system")):
            self.append(self.abstract)
        with self.create(Section("Sensor information")) as sensors:
            with sensors.create(Table(position="H")) as table:
                self.sensor_table(table)
        with self.create(Section("Software")):
            self.append(
                NoEscape(
                    general_text["software"].format(
                        version=importlib.metadata.version("ctdam")
                    )
                    + "\\cite{michels_ctdam_2026}"
                )
            )
        if self.validated and len(general_text["intro_validation"]) > 0:
            with self.create(Section("Field calibration")):
                self.append(general_text["intro_validation"])
        with self.create(Section("Processing")):
            self.append(
                NoEscape(
                    general_text["processing_intro"]
                    + "\\cite{michels_ctdam_docs_2026}"
                )
            )
            for processing_module in self.processing_modules:
                for name, texts in processing_info.items():
                    if name.lower() == processing_module.lower():
                        with self.create(Subsection(texts["title"])):
                            self.append(texts["text"])
        with self.create(Section("Quality flagging")):
            qc_texts = general_text["quality_flagging"]
            self.append(
                NoEscape(
                    "The quality flagging applied in this dataset follow the SeaDataNet \\cite{seadatanet_seadatanet_2022} guidelines which can be seen in table 2."
                )
            )
            with self.create(Table(position="H")) as table:
                self.quality_flag_table(table)
            self.append(qc_texts[0])
            self.append("\n")
            self.append(qc_texts[1])
            with self.create(Table()) as table:
                self.parameter_range_table(table)
        with self.create(Section("Exported data format")):
            self.append(
                NoEscape(
                    f"The exported data file '{self.cruise_label}\\_CTD.tab' is comprised of one data table of all CTD cast data of this cruise, in sequental order, concatenated one after the other. The column names adhere to the standard specified in the PANGAEA wiki \\cite{{pangaea_ctd_2026}} and includes quality flags. It also features an 'Event' column that links the individual cast data to DSHIP entries, the data management system aboard German research vessels \\cite{{werum_dship_2020}}. With these, a lot of extra cruise-specific metadata can be mapped to the individual data points \\cite{{pangaea_expiditions}}."
                )
            )

    def create_tabu(
        self, column_names: list[str], col_space: str = "0.5cm"
    ) -> Tabu:
        table_spec = "X[l] |" * len(column_names)
        tabu = Tabu(
            table_spec=table_spec[0:-1],
            row_height=1.5,
            col_space=col_space,
        )
        tabu.omit_if_empty = True
        tabu.add_row(column_names, mapper=[bold])
        tabu.add_hline()
        return tabu

    def quality_flag_table(self, table: Table):
        header_row = [
            "Flag",
            "Term",
            "Definition",
            "Usage during this processing",
        ]
        tabu = self.create_tabu(header_row)
        tabu.add_row(
            "0", "no qc", "No quality control has been applied.", "not used"
        )
        tabu.add_row(
            "1",
            "good",
            "Good quality data value which has been verified.",
            "Verified with additional data and passed range test.",
        )
        tabu.add_row(
            "2",
            "probably good",
            "Good quality data value which has not been verifed.",
            "Value passed the range test.",
        )
        tabu.add_row(
            "3",
            "probably bad",
            "Data value which is obviously inconsistent to the phenomenon.",
            "not used",
        )
        tabu.add_row(
            "4",
            "bad",
            "Obviously erroneous value.",
            "Value failed the range test.",
        )
        tabu.add_row("5-7", "not used", "", "")
        tabu.add_row(
            "8", "interpolated", "Value derived by interpolation.", "not used"
        )
        tabu.add_row(
            "9",
            "missing",
            "Value is missing.",
            "Value is missing or could not be converted to a number.",
        )
        table.append(tabu)
        table.add_caption(
            "Description of the quality flags and the rules according to which these flags were applied."
        )

    def sensor_table(self, table: Table):
        header_row = [
            "Sensor",
            "Serial Number",
            "Last Calibrated",
        ]
        tabu = self.create_tabu(header_row)
        for sensor in self.sensor_info:
            if not sensor:
                continue
            try:
                sensor_type = self._format_sensor_name(sensor["SensorName"])
                sensor_num = sensor["SerialNumber"]
                sensor_cali = sensor["CalibrationDate"]
            except KeyError:
                continue
            else:
                tabu.add_row(sensor_type, sensor_num, sensor_cali)
        table.append(tabu)
        table.add_caption(
            "Overview over the sensors in use and their calibration status."
        )

    def _format_sensor_name(self, name: str) -> str:
        if "afl" in name.lower():
            name = "Fluorometer"
        elif "cdom" in name.lower():
            name = "Fluorometer"
        elif "spar" in name.lower():
            name = "SPAR"
        elif "par" in name.lower():
            name = "PAR"
        elif ("ntu" in name.lower()) or ("turbidity" in name.lower()):
            name = "Turbidity Meter"
        elif "2" in name:
            name = name[:-1].strip() + " 2"
        return name

    def parameter_range_table(self, table: Table):
        header_row = ["Parameter", "Minimum", "Maximum"]
        tabu = self.create_tabu(header_row)
        tabu.add_row("Oxygen [umol/kg]", "0", "300")
        tabu.add_row("Temperature [C]", "-2", "50")
        tabu.add_row("Conductivity [mS/cm]", "0", "100")
        tabu.add_row("Salinity [PSU]", "0", "60")
        tabu.add_row("Pressure [db]", "0", "10000")
        table.append(tabu)
        table.add_caption(
            "The parameter ranges that were used for the plausability check during quality control."
        )
