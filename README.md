# ctdam

[![image](https://img.shields.io/badge/DAM-midnightblue)](https://www.allianz-meeresforschung.de/en)
[![image](https://img.shields.io/pypi/v/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://img.shields.io/pypi/pyversions/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://img.shields.io/badge/docs-darkorange?logo=readdotcv)](https://dam-ctd-software.github.io/ctdam)
[![image](https://img.shields.io/pypi/l/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://zenodo.org/badge/DOI/10.5281/zenodo.19233531.svg)](https://doi.org/10.5281/zenodo.19233531)

**ctdam** is a Python package designed to standardize and simplify the parsing, processing, and visualization of **Conductivity-Temperature-Depth (CTD) data** from diverse file formats. By converting raw CTD data into a **CF-compliant xarray Dataset**, the package enables seamless integration with the scientific Python ecosystem, leveraging the power of **xarray accessors** for data handling, analysis, and plotting.

## **Key Features**

### **1. Multi-Format Support**

Parse CTD data from a variety of file formats (e.g., `.hex`, `.cnv`, `.TOB`, `.nc`) into a **consistent, CF-compliant xarray Dataset**. The package abstracts away format-specific quirks, so you can focus on the data.

### **2. CF-Compliant Structure**

Outputs are structured as **xarray Datasets** with:

- Standardized variable names (e.g., `temperature`, `salinity`, `pressure`).
- Metadata (units, long names, coordinates) following **CF (Climate and Forecast) conventions** (e.g. `sea_water_temperature`, `sea_water_practical_salinity`, `sea_water_pressure`).
- Automatic handling of coordinate systems (e.g., depth, scan, time).

### **3. xarray Accessors for CTD Data**

Extend xarray’s functionality with **custom accessors** for CTD-specific operations:

- **Processing**: Smoothing, binning, spike removal, or unit conversion. Using enhanced Sea-Bird processing logic for compatibility.
- **Plotting**: Quick visualization of profiles, sections, or maps using Matplotlib or bokeh.
- **Data Handling**: Subsetting, merging, or exporting to NetCDF/CSV.

### **4. Modular and Extensible**

- Add support for new file formats via pluggable parsers.
- Customize processing pipelines with built-in or user-defined functions.

---

## **Installation**

The ctdam python package is distributed via PyPi, that means that you
can install it inside your python environment using your favorite
package manager:

```bash
uv add ctdam
```

```bash
pip install ctdam
```

This installs only the functionalities. To use features like the CLI,
plotting or a GUI to edit processing workflow files, you need to install
ctdam with extra optional dependencies. That looks differently
dependending on installation type:

```bash
uv add ctdam --extra cli
```

```bash
poetry add ctdam[gui]
```

```bash
pip install ctdam[vis]
```

If you don\'t care about find-grained dependency management, you can
also just install all of them with the \'all\' group.

---

## **Usage Examples**

### **1. Parse a CTD File**

```python
from ctdam import read_ctd_data

# Parse a .hex file into an xarray Dataset
ds = read_ctd_data("sbs_data/hex/EMB356_11-1.hex")
```

This assumes that the corresponding sensor metadata file (.XMLCON) resides in the same directory as the .hex and is also using a similar name.

```python
from ctdam import read_ctd_data
# Parse a .cnv file into an xarray Dataset
ds = read_ctd_data("sbs_data/cnv/EMB356_11-1.cnv")

# Parse a .TOB file into an xarray Dataset
ds = read_ctd_data("sbs_data/other/IB051044.TOB")

# Parse a NetCDF file
ds = ctd.parse("path/to/ctd_data.nc")
```

You can also add bottle information to the existing data:

```python
ds = read_ctd_data("sbs_data/cnv/EMB295_14-1.cnv")
ds.add.bottles("sbs_data/btl/EMB295_14-1.bl")
btl_ds = ds.access.btl_info()
```

### **2. Access Data and Metadata**

```python
# Print the Dataset
print(ds)

# Access a variable (e.g., temperature)
temperature = ds["temperature"]

# Check metadata (CF-compliant)
print(ds["temperature"].attrs)
```

### **3. Use xarray Accessors**

```python
# Plot a temperature profile
ds.vis.profile("temperature")

# Bin data by depth
ds.proc.module('binavg', {'bin_size': 1})

# Or apply a full processing workflow
ds.proc.workflow(modules=['loop_removal', 'wfilter', 'alignctd', 'celltm'])
```

Workflows can be defined in the form of .toml configuration files or as plain python dictionaries:

```python
processing_config = {
    "output_type": "cnv",
    "output_dir": ".",
    "modules": {
        "airpressure": {},
        "wildedit_geomar": {'std2': 7},
        "wfilter": {},
        "celltm": {},
        "alignctd": {'Oxygen': 3},
        "SA_from_SP_Baltic": {},
        "binavg": {},
    },

}
```

All processing module behaviour can be modified via key-values, as seen
for `wildedit_geomar` and `alignctd`. In the example
config you can also see, that the original Sea-Bird processing modules can
be mixed with custom ones (airpressure) and all gsw functions
(SA_from_SP_Baltic). Its also possible to use the original Sea-Bird processing binaries, as long as they are installed on your machine.

### **4. Export to NetCDF**

```python
ds.to_netcdf("processed_ctd_data.nc")
```

---

## **Supported File Formats**

| Format | Description           | Notes                        |
| ------ | --------------------- | ---------------------------- |
| `.hex` | Seabird HEX format    | Raw data                     |
| `.cnv` | Seabird CNV format    | Default for many CTD systems |
| `.nc`  | NetCDF                | CF-compliant or raw          |
| `.TOB` | Sea&Sun CTD format    | Small handheld-CTDs          |
| `.bl`  | Seabird bottle format | Bottle closing information   |

---

## **Contributing**

Contributions are welcome! To add support for a new file format or feature:

1. Fork the repository.
2. Implement your changes in a new branch.
3. Submit a pull request with tests and documentation.

Details can be found inside [Contributing](/CONTRIBUTING.md).

---

## Context

This software is developed for the [German Marine Research Alliance
(DAM)](https://www.allianz-meeresforschung.de/en) in the context of the [Underway Data: Marine Data - Research Vessels Project](https://www.allianz-meeresforschung.de/en/activities/data-management-and-digitalisation/underway-research-data). The converter and parser are tested
against a variety of data, acquired on different German research
vessels. Because of the ongoing efforts to harmonise these
infrastructures, the diversity of the test data may be smaller than
thought and your data may pose problems to converter, parser or
processing. Please feel free to contribute to this project in order to
develop a toolkit, that is as general as possible.

---
