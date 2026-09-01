xarray structure how to
=======================

.. role:: python(code)
   :language: python

An :python:`xarray` instance is meant to be the primary data and metadata storage of one
CTD cast. In Sea-Bird terms you can think of it to be the python internal
equivalent of a .cnv file. 

-----------

input parsing
"""""""""""""

A cf-compliant :python:`xarray` can be retrieved by conversion or by parsing a
file, but the usage is the same:

.. code-block:: python

   from ctdam import read_ctd_data

   ds = read_ctd_data('sbs_data/cnv/EMB356_11-1.cnv')
   ds = read_ctd_data('sbs_data/hex/EMB356_11-1.hex')
   ds = read_ctd_data("sbs_data/other/IB051044.TOB")


output parsing
""""""""""""""

At the moment, you can parse an :python:`xarray` to Sea-Birds .cnv format

.. code-block:: python

   ds.export.to_cnv()

as well as NetCDF

.. code-block:: python

   ds.to_netcdf()

Information to access
---------------------

.. code-block:: python

    >>> print(ds)
    <xarray.Dataset> Size: 380kB
    Dimensions:                          (sensor: 2, scan: 3067)
    Coordinates:
    * sensor                           (sensor) <U9 72B 'primary' 'secondary'
        time                             (scan) float64 25kB 1.707e+09 ... 1.707e+09
    Dimensions without coordinates: scan
    Data variables: (12/17)
        pressure                         (scan) float64 25kB 0.648 0.696 ... 23.06
        pressure_qc                      (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        temperature                      (scan, sensor) float64 49kB 3.562 ... 3.744
        temperature_qc                   (scan, sensor) int8 6kB 0 0 0 0 ... 0 0 0 0
        conductivity                     (scan, sensor) float64 49kB 15.33 ... 17.36
        conductivity_qc                  (scan, sensor) int8 6kB 0 0 0 0 ... 0 0 0 0
        ...                               ...
        turbidity_qc                     (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        par_biosphericallicorchelsea     (scan) float64 25kB 9.24 9.267 ... 0.04539
        par_biosphericallicorchelsea_qc  (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        salinity                         (scan, sensor) float64 49kB 15.55 ... 17.69
        salinity_qc                      (scan, sensor) int8 6kB 0 0 0 0 ... 0 0 0 0
        flag                             (scan) float64 25kB 0.0 0.0 0.0 ... 0.0 0.0
    Attributes:
        start_time:           2024-02-08 08:31:25
        position:             (54.155166666666666, 11.293333333333333)
        cruise:               EMB356
        station:              EMB356_11-1
        path_to_source_file:  /home/emil/Projects/ctdam/sbs_data/cnv/EMB356_11-1.cnv
        sample_rate:
        instrument_metadata:  Sea-Bird SBE 9 Data File:\nFileName = C:\CTD\CTD_Da...
        custom_metadata:      Cruise = EMB356\nStation = EMB356_11-1\nPlatform = ...
        sensor_metadata:      <Sensors count="15" >\n  <sensor Channel="1" >\n   ...
        provenance_metadata:  datcnv_date = Nov 17 2025 13:21:17, 7.26.7.129 [dat...

You can display all kinds of information from inside the source .hex or .cnv
files, like header, custom metadata, file_name and much more:

.. code-block:: python

   >>> ds.attrs['instrument_metadata']
   ['* Sea-Bird SBE 9 Data File:\n', '* FileName = C:\\CTD\\CTD_Data\\EMB356\\E
   MB356_011-01_CTD_0010.hex\n', '* Software Version Seasave V 7.26.7.121\n',
   ....]

   >>> ds.meta.custom
   {'Cruise': 'EMB356', 'Station': 'EMB356_11-1', 'Platform': 'CTD', 'Cast': '0
   010', 'Operator': 'Johann Ruickoldt', 'GPS_Time': '08.02.2024 08:30:10', 'GP
   S_Lat': '54  9.308 N', 'GPS_Lon': '11 17.587 E', 'Echo_Depth': '25.7 m', 'Ai
   r_Pressure': '1000.8 hPa', 'WsStartID': '251', 'Pos_Alias': 'TF0021'}

   >>> ds.access.path
   Path('sbs_data/hex/EMB356_11-1.hex')

   >>> ds.meta.provenance.keys()
   [hex2py, wildedit, wfilter, alignctd, celltm, binning]

   >>> ds.meta.provenance['binning']
   {'metainfo': '2026.02.19 11:35:18, ctdam python package, v1.4.1', 'bin_varia
   ble': 'pressure', 'bin_size': '1', 'cast_type': 'down'}



Functionality
-------------

As CTD is often measured using a dual-sensor setup, a few handy functions have
been written to work with dual-sensor data. In general, the data of two sensors
is saved inside the same xarray variable.

.. code-block:: python

   >>> ds.temperature
   <xarray.DataArray 'temperature' (scan: 3067, sensor: 2)> Size: 49kB
    array([[3.5616, 3.561 ],
        [3.5614, 3.561 ],
        [3.5617, 3.5609],
        ...,
        [3.7476, 3.7436],
        [3.7475, 3.7433],
        [3.7473, 3.7436]], shape=(3067, 2))
    Coordinates:
        time     (scan) float64 25kB 1.707e+09 1.707e+09 ... 1.707e+09 1.707e+09
    * sensor   (sensor) <U9 72B 'primary' 'secondary'
    Dimensions without coordinates: scan
    Attributes:
        standard_name:        sea_water_temperature
        units:                degree_C
        ancillary_variables:  temperature_qc

You can specificly access only the primary sensor data via:

.. code-block:: python

    >>> ds.temperature.sel(sensor='primary')
    <xarray.DataArray 'temperature' (scan: 3067)> Size: 25kB
    array([3.5616, 3.5614, 3.5617, ..., 3.7476, 3.7475, 3.7473], shape=(3067,))
    Coordinates:
        time     (scan) float64 25kB 1.707e+09 1.707e+09 ... 1.707e+09 1.707e+09
        sensor   <U9 36B 'primary'
    Dimensions without coordinates: scan
    Attributes:
        standard_name:        sea_water_temperature
        units:                degree_C
        ancillary_variables:  temperature_qc


If you want to access the whole secondary sensor strand, you can also do so:

.. code-block:: python

    >>> ds.access.sensor_strand('secondary')
    <xarray.Dataset> Size: 270kB
    Dimensions:                          (scan: 3067)
    Coordinates:
        time                             (scan) float64 25kB 1.707e+09 ... 1.707e+09
    Dimensions without coordinates: scan
    Data variables: (12/17)
        pressure                         (scan) float64 25kB 0.648 0.696 ... 23.06
        pressure_qc                      (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        temperature                      (scan) float64 25kB 3.561 3.561 ... 3.744
        temperature_qc                   (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        conductivity                     (scan) float64 25kB 15.33 15.33 ... 17.36
        conductivity_qc                  (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        ...                               ...
        turbidity_qc                     (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        par_biosphericallicorchelsea     (scan) float64 25kB 9.24 9.267 ... 0.04539
        par_biosphericallicorchelsea_qc  (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        salinity                         (scan) float64 25kB 15.55 15.55 ... 17.69
        salinity_qc                      (scan) int8 3kB 0 0 0 0 0 0 ... 0 0 0 0 0 0
        flag                             (scan) float64 25kB 0.0 0.0 0.0 ... 0.0 0.0

    >>> ds.access.sensor_strand('secondary').salinity
    <xarray.DataArray 'salinity' (scan: 3067)> Size: 25kB
    array([15.5515, 15.5517, 15.5517, ..., 17.694 , 17.6903, 17.6891],
        shape=(3067,))
    Coordinates:
        time     (scan) float64 25kB 1.707e+09 1.707e+09 ... 1.707e+09 1.707e+09
    Dimensions without coordinates: scan
    Attributes:
        standard_name:        sea_water_practical_salinity
        units:                PSU
        ancillary_variables:  salinity_qc

Apart from this custom functionality, there is a ton of features you can do
out of the box on xarrays, so its worth `checking out their documentation<https://docs.xarray.dev/en/latest/api.html>`_.
Additionally, you can use all gsw functions on-top of your arrays, like so:



.. code-block:: python

   ds.gsw.sigma0()


And through cf-compliance, the correct variables will be picked automatically.
This is made possible by `gsw-xarray <https://gsw-xarray.readthedocs.io/en/latest/index.html>`_,
which is an amazing python package and is included in ctdam. For ease of use,
you can calculate the base TEOS-10 variables, absolute salinity, conservative
temperature and density, via this handy shortcut:


.. code-block:: python

   ds.add.teos10_vars()

