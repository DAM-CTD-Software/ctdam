CTD Data
========

.. role:: python(code)
   :language: python

A :python:`CTDData` object is meant to be the primary data and metadata storage of one
CTD cast. In Sea-Bird terms you can think of it to be the python internal
equivalent of a .cnv file. In fact, the ctdam parser of SBE9/11 .cnv files, :python:`CnvFile`
does feature an export method, :python:`to_ctd_data()`, to generate a :python:`CTDData` object.
Other parsers are meant to follow, for example for SBE19s and SBE37s, for the
Sea&Sun CTD format and the custom CTD file format used at GEOMAR.
And if you are in need of another, feel free to reach out!

I/O parsing
-----------

input parsing
"""""""""""""

A :python:`CTDData` object can be retrieved by conversion

.. code-block:: python

   from ctdam.conv import decode_hex

   ctd_data = decode_hex('sbs_data/hex/EMB356_11-1.hex')

or by parsing a .cnv file

.. code-block:: python

   from ctdam.parser import CnvFile

   ctd_data = CnvFile('sbs_data/cnv/EMB356_11-1.cnv').to_ctd_data()


output parsing
""""""""""""""

At the moment, you can parse a :python:`CTDData` object to Sea-Birds .cnv format

.. code-block:: python

   ctd_data.to_cnv()

as well as NetCDF

.. code-block:: python

   ctd_data.to_netCDF()

Information to access
---------------------

You can display all kinds of information from inside the source .hex or .cnv
files, like header, custom metadata, file_name and much more:

.. code-block:: python

   >>> ctd_data.header
   ['* Sea-Bird SBE 9 Data File:\n', '* FileName = C:\\CTD\\CTD_Data\\EMB356\\E
   MB356_011-01_CTD_0010.hex\n', '* Software Version Seasave V 7.26.7.121\n',
   ....]

   >>> ctd_data.metadata
   {'Cruise': 'EMB356', 'Station': 'EMB356_11-1', 'Platform': 'CTD', 'Cast': '0
   010', 'Operator': 'Johann Ruickoldt', 'GPS_Time': '08.02.2024 08:30:10', 'GP
   S_Lat': '54  9.308 N', 'GPS_Lon': '11 17.587 E', 'Echo_Depth': '25.7 m', 'Ai
   r_Pressure': '1000.8 hPa', 'WsStartID': '251', 'Pos_Alias': 'TF0021'}

   >>> ctd_data.file_name
   'EMB356_11-1'

Apart from these attributes, other interesting ones are parsed sensor
information

.. code-block:: python

   >>> ctd_data.sensor_info
   [{'Channel': '1', 'SensorName': 'Temperature', '@SensorID': '55', 'SerialNum
   ber': '5492', 'CalibrationDate': '2023-12-18', 'UseG_J': '1', 'A': '0.000000
   00e+000', 'B':...]

processing step information

.. code-block:: python

   >>> ctd_data.processing_steps
   [hex2py, wildedit, wfilter, alignctd, celltm, binning]

   >>> ctd_data.processing_steps[5].metadata
   {'metainfo': '2026.02.19 11:35:18, ctdam python package, v1.4.1', 'bin_varia
   ble': 'prDM', 'bin_size': '1', 'cast_type': 'down'}

and cast start and end points

.. code-block:: python

   >>> ctd_data.cast_borders
   {'down_start': 0, 'down_end': 42009, 'input_size': 78018}


Functionality
-------------

Noticeable methods to run on a :python:`CTDData` object are processing :python:`ctd_data.process()`,
and plotting :python:`ctd_data.plot()`, which run the given operations directly
on the :python:`CTDData` objects.


Full class description
----------------------

.. automodule:: ctdam.parser.ctddata
   :members:
   :undoc-members:

