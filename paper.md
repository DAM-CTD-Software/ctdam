---
title: "ctdam: Library for conversion, processing and plotting of CTD data"
tags:
  - Python
  - CTD
  - conversion
  - parser
  - processing
  - visualization
  - oceanography
  - seabird
  - data
authors:
  - name: Emil Michels
    orcid: 0009-0003-0300-9465
    affiliation: "1, 2"
affiliations:
  - name: Leibniz Institute for Baltic Sea Research Warnemünde
    index: 1
    ror: 03xh9nq73
  - name: German Marine Research Alliance
    index: 2
    ror: 03rgygs91
date: 19 October 2026
bibliography: paper.bib
---

# Summary

Two of the most important parameters that drive ocean processes are temperature and salinity, which both can vary substantially between the surface and the seafloor. In order to measure vertical profiles of these parameters, the CTD system has been developed. The acronym stands for conductivity, temperature, and depth, the base parameters measured by the instrument. Depth is derived from pressure sensor readings, and salinity is calculated from conductivity, temperature, and pressure. Extended with additional sensors (for example oxygen or optical chlorophyll sensors) and water sampling systems, CTDs form the backbone of marine research aboard research vessels worldwide. Hardware configurations vary as much as the applications they serve, which makes consistent handling of the resulting data a challenge.

`ctdam` is a Python package that standardizes CTD data handling. Regardless of the hardware, raw data format, or sensor configuration, working with CTD data in `ctdam` follows the same workflow. The package covers data conversion, parsing, and standard processing, with the goal of replacing vendor-specific software and enabling fully automated pipelines. Instead of proprietary, heterogeneous formats, `ctdam` uses NetCDF [@nsf_unidata_network_2024], the standard file format in oceanography, and follows community metadata conventions [@eaton_netcdf_2025]. It also uses the common SeaDataNet flags [@seadatanet_seadatanet_2022] to continuously display the quality of each parameter on a scale from 0-9. A simple API lowers the barrier to entry: users no longer need to learn hardware-specific tools, as `ctdam` relies purely on python code. This makes it on the one hand easier to handle CTD data when processing and analysing manually and on the other hand enables the full automation of the same process. With the effort required to publish CTD data reduced to a minimum, the availability of CTD data should greatly improve.

![ctdam capabilities overview.\label{fig:ctdam_overview}](ctdam_overview.pdf)

# Statement of need

CTD profilers are among the most widely used instruments in oceanography, and CTD casts underpin research on water mass properties, circulation, stratification, and ocean change. Handling these data efficiently is therefore important, yet the tools available for converting and processing raw instrument output remain limited. Existing solutions are often proprietary, tied to a specific instrument vendor or operating system, or require extensive manual intervention. As a result, researchers frequently write one-off scripts tailored to a single cruise or research question, and these scripts are rarely documented, tested, or reused.

This ad hoc approach has consequences beyond lost time. Once the data have served their immediate purpose, they typically remain on local hard drives in inconsistent formats, with incomplete metadata and no documented processing history. Such data are difficult to share, hard to reproduce, and seldom revisited, so a substantial amount of potentially valuable observations never reaches the wider community. This works against the FAIR principles (Findable, Accessible, Interoperable, Reusable) that funders and data repositories increasingly expect.

Simplifying and automating CTD processing should lower the barrier to publishing data directly, and more CTD data would be archived in public repositories. Automation also enables new workflows that are impractical with manual processing: reproducible, version-controlled pipelines; standardized quality control applied consistently across cruises; processing in near real time on board a research vessel; and the integration of CTD data into larger data-management and analysis systems.

`ctdam` addresses this need by offering a consistent API and data structure, regardless of the instrument, enables streamlined processing routines and can produce all kinds of output formats with a priority for metadata handling. It is targeted at scientists, engineers and data managers working with CTD data.

# State of the field

Most CTD users process their data with software supplied by the instrument manufacturer. For the majority of instruments this means Sea-Bird Scientific, whose systems dominate the market. Sea-Bird Scientific provides individual programs for converting, processing, and plotting data in its proprietary format. Chaining these steps into a processing pipeline requires custom scripting around these programs. Combined with limited error feedback and rigid configuration files, this ties each processing setup to a single workflow and demands expert knowledge of both the tools and the scripting language. Sea-Bird Scientific recently released a Python package [@sea-bird-scientific_sea-birdscientificseabirdscientific_2024] that reimplements its conversion and processing logic. However, its functions operate on inconsistent inputs and outputs, are slow, and remain specific to Sea-Bird instruments.

Other Python packages exist, but they typically target individual workflows [@denouden_seabird-processing_2023] or strictly parse Sea-Bird Scientific data CTD data files into non-standard formats [@castelao_castelaoseabird_2018; @holtermann_marinedatatoolspycnv_2016; @fernandes_python-ctd_2014]. Many oceanographers instead rely on custom MATLAB scripts that are not part of a shared toolbox. `ctdam` aims to provide such a common, vendor-independent toolbox, that is developed collaboratively.

# Software design

To organize the different functionalities of the python package, it has been split up into several subpackages:

- **conv**: conversion code to convert from raw CTD data formats
- **entry**: collects the entry points to the software, e.g. API functions, CLI and a GUI to define custom processing workflows
- **parser**: parsers for the different CTD data formats
- **proc**: covers processing and collects the different processing modules inside `proc.modules`
- **qc**: quality control code
- **vis**: visualization code

## API

The core functionalities are collected inside high level functions and classes to form an API. These reside in the top level package (allowing simple imports like `from ctdam import parse`) and cover parsing (`parse`), processing (`process`), plotting (`plot`), cast start and end point calculation (`get_cast_borders`) and the streamlined parsing, processing and plotting of whole cruise data in parallel (`Casts`).

## Data structure

The core data structure is an `xarray` Dataset whose metadata follows the CF conventions [@eaton_netcdf_2025]. This allows data to be read from and written to NetCDF files without loss of information. All functionality is implemented as lightweight `xarray` accessors. This preserves the full `xarray` ecosystem while extending it in a way consistent with its conventions. It also works well in interactive Jupyter notebooks, where users benefit from `xarray`s rich display and accessor tooltips.

## Processing

For processing, users define a `Workflow` that applies a sequence of routines to their data. A `Workflow` can be specified either as a .toml configuration file or as a standard Python dictionary; the two are interchangeable, since the configuration file is parsed into the dictionary internally. Each processing module accepts key-value pairs to control its behavior. To simplify setting these up, a graphical interface is available through the GUI dependency group. Ease of use is a central design goal, as existing tools largely lack it.

## Additional dependencies

To keep the core package slim, certain functionalities rely on extra dependencies that need to be additionally installed. These dependencies are collected inside "dependency groups" of the name of the functionality they relate to: `cli`, `gui`, `vis` and `report`. Via the `all` dependency group every additional dependency can be installed, if they are no space or bandwidth concerns that need a slim package.

# Research impact statement

`ctdam` is primarily used in the DAM [@dam_german_2026] Marine Data – Research Vessels project to support the standardized publication of CTD data from German research vessels in PANGAEA [@felden_pangaea_2023] via a common data flow [@wiemer_information_2026]. A couple of example publications are included [@michels_physical_2026; @michels_physical_2026-1; @michels_physical_2026-2]. These standardization efforts are intended to spread through the package. Several oceanographers outside the project have already adopted `ctdam` and report positive results.

# AI usage disclosure

AI tools were used occasionally to help in debugging and for simple
documentation generation. The first draft of Figure \ref{fig:ctdam_overview} has also been generated
and subsequently altered by hand. After writing the initial draft of this
manuscript generative AI was used for language refinement. All these
contributions were carefully checked by the author, who takes full
responsibility for the software package, its documentation and this article.

# Acknowledgements

This software is being developed inside the scope of the DAM Project
"Development and Expansion of Data Infrastructure and Management for German
Research Vessels (Marine Data - Research Vessels)", funded by the German
Federal Ministry of Research, Technology and Space (FKZ 03F1001).

# References
