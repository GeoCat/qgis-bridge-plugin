Testing
========

Below you can find some ideas about the plugin testing

Automated tests
----------------

At the moment there are no automated test for the Bridge plugin

Semi-automated test
--------------------

A suite of tests for visual inspection of the style conversion between QGIS and GeoServer is available. These tests take a set of sample styles, convert them to SLD, and upload them to a GeoServer instance. An image of the original QGIS rendering, along with an image of the geoserver rendering are produced, so they can be compared side by side.

To know more about these tests and how to run them, read the comments in the header of the `script file <./visualstyletests.py>`_

Manual testing
---------------

A test project is provided, which can be used to test several elements of Bridge and its interaction with data and metadata servers. It can be found in the ``test/data`` folder of the repo. Layers in the project contain metadata and are styled using different symbols. 

A detailed list of operations to manually test (with or without the above mentioned project) are available in the `test operations file <./testoperations.txt>`_.