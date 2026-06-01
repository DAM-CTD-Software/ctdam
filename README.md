# ctdam

[![image](https://img.shields.io/badge/DAM-midnightblue)](https://www.allianz-meeresforschung.de/en)
[![image](https://img.shields.io/pypi/v/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://img.shields.io/pypi/pyversions/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://img.shields.io/badge/docs-darkorange?logo=readdotcv)](https://dam-ctd-software.github.io/ctdam)
[![image](https://img.shields.io/pypi/l/ctdam.svg)](https://pypi.python.org/pypi/ctdam)
[![image](https://zenodo.org/badge/DOI/10.5281/zenodo.19233531.svg)](https://doi.org/10.5281/zenodo.19233531)

## Intro

Welcome to the ctdam software package, a library to help with all the
different stages in working with CTD data. For now, it focuses only on
Sea-Bird CTD data, but we are open to extend to other CTD data types in
the future. At the moment, the focus remains on fast and reliable
conversion and processing of Sea-Birds .hex files. Data and metadata are
stored inside python objects, with the possibility to export native .cnv
files, as well as NetCDFs. In general, there are parsers for all the
different Sea-Bird file formats: .hex, .xmlcon, .bl, .btl and .cnv .

### Conversion

For conversion of raw CTD data, only a .hex file and its corresponding
.xmlcon file are needed. Then, you can simply do:

```python
from ctdam.conv import decode_hex

ctd_data = decode_hex('sbs_data/hex/EMB356_11-1.hex')
```

This assumes that the .xmlcon resides in the same directory as the .hex
and is also using a similar name. The code snippet would yield you a
`CTDData` object, a very general representation of CTD data and metadata
of a single cast. You could for example do some processing on this data.

### Processing

To process CTD data, one needs to define workflow files, called
'procedures', .toml files which correspond to python dictionaries and
e.g. look like this:

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
for \'wildedit_geomar\' and \'alignctd\'. In the example
config you can also see, that the native Sea-Bird processing modules can
be mixed with custom ones (airpressure) and all gsw functions
(SA_from_SP_Baltic). The Sea-Bird ones are either
taken from [seabirdscientific](https://github.com/Sea-BirdScientific/seabirdscientific)
or are more efficient rewrites that stick to the same core logic. Its
also possible to use the original Sea-Bird processing binaries, as long
as they are installed on your machine.

In order to process the converted data from above, you would go ahead
and do:

```python
ctd_data.process(processing_config)
```

This again results in a `CTDData` instance, which you now could plot.

### Plotting

This library uses [bokeh](https://bokeh.org/) for generating interactive
plots, that can be viewed inside your webbrowser:

```python
ctd_data.plot()
```

The resulting plot of this operation can be seen [here](https://dam-ctd-software.github.io/ctdam/plot.html).

The .html files generated like this, are self-contained and can be
shared easily without the need of the original data or external tooling.

### Data export

To write the data back to disk, two output methods are currently
supported, Sea-Bird-like .cnv and NetCDF. In order to write the
converted and processed \'EMB356[11-1.hex]{#hex}\' as .cnv to disk, just
do:

```python
ctd_data.to_cnv('processed_EMB356_11-1.cnv')
```

### CLI

Instead of working inside a python environment, the same results can
also be obtained by using a command line interface, also called
\'ctdam\':

```console
ctdam run sbs_data/hex/EMB356_11-1.hex proc_workflow.toml
ctdam plot EMB356_11-1.cnv -d '' -sm
```

With the first command, a processing workflow is used on a .hex file,
which also means, that its converted automatically. The second command
does plot the new .cnv file and save it in the same directory. Meaning
that we have literaly done the exact steps like above.

## Installation

The ctdam python package is distributed via PyPi, that means that you
can install it inside your python environment using your favorite
package manager:

```console
uv add ctdam
```

```console
poetry add ctdam
```

Or just plain old pip:

```console
pip install ctdam
```

This installs only the functionalities. To use features like the CLI,
plotting or a GUI to edit processing workflow files, you need to install
ctdam with extra optional dependencies. That looks differently
dependending on installation type:

```console
uv add ctdam --extra cli
```

```console
poetry add ctdam[gui]
```

```console
pip install ctdam[vis]
```

If you don\'t care about find-grained dependency management, you can
also just install all of them with the \'all\' group.

The CLI program can be installed similarly:

```console
$ uv tool install --from 'ctdam[all]' ctdam

$ uv run ctdam check
All set, you are ready to go.
```

```console
$ pipx install ctdam

$ ctdam check
All set, you are ready to go.
```

## Context

This software is developed for the [German Marine Research Alliance
(DAM)](https://www.allianz-meeresforschung.de/en) in the context of the
Underway Research Data Project. The converter and parser are tested
against a variety of data, acquired on different German research
vessels. Because of the ongoing efforts to harmonise these
infrastructures, the diversity of the test data may be smaller than
thought and your data may pose problems to converter, parser or
processing. Please feel free to contribute to this project in order to
develop a toolkit, that is as general as possible.
