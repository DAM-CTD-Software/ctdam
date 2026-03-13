ctdam
=====

.. image:: https://img.shields.io/pypi/v/ctdam.svg
        :target: https://pypi.python.org/pypi/ctdam

.. image:: https://img.shields.io/pypi/l/ctdam.svg
        :target: https://pypi.python.org/pypi/ctdam

.. image:: https://img.shields.io/pypi/pyversions/ctdam.svg
        :target: https://pypi.python.org/pypi/ctdam

.. image:: https://github.com/DAM-CTD-Software/ctdam/actions/workflows/main_push.yaml/badge.svg
        :target: https://github.com/DAM-CTD-Software/ctdam/actions/workflows/main_push.yaml

.. image:: https://github.com/DAM-CTD-Software/ctdam/actions/workflows/pull_request.yaml/badge.svg
        :target: https://github.com/DAM-CTD-Software/ctdam/actions/workflows/pull_request.yaml

Intro
-----

Welcome to the ctdam software package, a library to help with all the
different stages in working with CTD data. For now, it focuses only on
Sea-Bird CTD data, but we are open to extend to other CTD data types in
the future. At the moment, the focus remains on fast and reliable
conversion and processing of Sea-Birds .hex files. Data and metadata are
stored inside python objects, with the possibility to export native .cnv
files, as well as NetCDFs. In general, there are parsers for all the
different Sea-Bird file formats: .hex, .xmlcon, .bl, .btl and .cnv .

To process CTD data, one needs to define workflow files, called
‘procedures’, .toml files which correspond to python dictionaries and
e.g. look like this:

.. code:: python

   processing_config = {
       "output_type": "cnv",
       "output_dir": "somewhere",
       "modules": {
           "airpressure": {},
           "wildedit_geomar": {},
           "wfilter": {},
           "celltm": {},
           "alignctd": {},
           "Helmholtz_energy_ice": {},
           "binavg": {'bin_size': 0.1},
       },

   }

All processing module behaviour can be modified via key-values, as seen
for ‘binavg’. In the example config you can also see, that the native
Sea-Bird processing modules can be mixed with custom ones (airpressure)
and all gsw functions (Helmholtz_energy_ice). The Sea-Bird ones are
either taken from
`seabirdscientific <https://github.com/Sea-BirdScientific/seabirdscientific>`__
or are more efficient rewrites that stick to the same core logic. Its
additionally possible to use the original Sea-Bird processing binaries,
as long as they are installed on your machine.

Context
-------

This software is developed for the `German Marine Research Alliance
(DAM) <https://www.allianz-meeresforschung.de/en>`__ in the context of
the Underway Research Data Project. The converter and parser are tested
against a variety of data, acquired on different German research
vessels. Because of the ongoing efforts to harmonise these
infrastructures, the diversity of the test data may be smaller than
thought and your data may pose problems to converter, parser or
processing. Please feel free to contribute to this project in order to
develop a toolkit, that is as general as possible.
