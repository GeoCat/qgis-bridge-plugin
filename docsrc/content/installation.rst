Installation
############

Requirements
************

Client-side
-----------

|app_name| requires QGIS |min_qgis_ver| or newer.
Both the standalone QGIS installation or the OSGeo distribution should work.

.. note::   If you access the internet through a proxy server,
            you might experience some issues while publishing data or connecting to a server.

Server-side
-----------

GeoNetwork
^^^^^^^^^^

|app_name| currently supports GeoNetwork 3 starting at version 3.4 and higher.
GeoNetwork 2 support has been deprecated and version 4 is not supported yet.

GeoServer
^^^^^^^^^

-   Support starts at GeoServer version 2.13 and up. However, other
    versions since 2.4 are expected to run fine in most of the
    cases.
-   If you wish to use a direct connection to PostGIS (i.e. let |short_name|
    handle the data upload instead of the GeoServer REST API), you will
    need to have access to that database instance.
-   If you wish to let GeoServer import your data into PostGIS (i.e. through
    the REST API), you need to make sure that the
    `Importer extension <https://docs.geoserver.org/latest/en/user/extensions/importer/index.html>`_
    is available on GeoServer.

MapServer
^^^^^^^^^

-   MapServer support starts at version 6.2 and up.
    However, other versions since 5.6 are expected to run fine in most of the cases.
-   FTP connection or file write access to MapServer project path.


How to install
**************

To install the |plugin_name|, please follow these steps:

1. Open the :guilabel:`QGIS Plugin Manager`. The Plugin Manager can be opened using the :menuselection:`Plugins --> Manage and Install plugins` menu entry.

    .. image:: ./img/pluginmanagermenu.png

    You will see the following dialog:

    .. image:: ./img/pluginmanager.png

2. Select the :guilabel:`all` section to show all available plugins.

    .. image:: ./img/pluginmanagerall.png

3. In the search box, type `bridge` to filter the list of available plugins.

    .. image:: ./img/pluginmanagerfiltered.png

4. Click on the |gui_name| plugin entry to display the information about the plugin:

    .. image:: ./img/pluginmanagerbridge.png

5. Click on :guilabel:`Install` to install the plugin.

6. Once the plugin is installed, close the Plugin Manager and you will find a new menu entry under the :menuselection:`Web` menu,
which contains the menu items for the |short_name| plugin.

    .. image:: ./img/bridgemenuentry.png

7. You'll also notice a new toolbar button, that will open the |short_name| Publish dialog.

    .. image:: ./img/bridgetoolbarbutton.png
