Requirements
#############

Client requirements
********************

Bridge requires QGIS 3.6 or more recent.

Server requirements
********************

GeoNetwork
-----------

GeoCat Bridge is officially supported on any GeoNetwork latest (3.8)_ and
2 versions before (3.4 and 3.6)_. However most of the functionality will
be operational from GeoNetwork version 2.6+.

MapServer
---------------

Requirement for MapServer are:

-   Officially supported is the latest minor version of Mapserver and 2
    versions before, currently 7.0, 6.4 and 6.2. However any version
    from 5.6.0 is expected to operate fine in most of the cases.
-   FTP connection or file write access to MapServer project path


GeoServer
----------

Requirements for GeoServer are:

-   Officially supported versions are 2.15, 2.14 and 2.13. However other
    versions since 2.4 are expected to operate fine in most of the
    cases.


Installation
#############

To install the Bridge plugin for QGIS, follow these steps:

1. Open the :guilabel:`QGIS Plugin Manager`. The Plugin Manager can be opened using the :menuselection:`Plugins-->Manage and install plugins` menu entry.

	.. image:: ./img/pluginmanagermenu.png

	You will see the following dialog:

	.. image:: ./img/pluginmanager.png

2. Select the :guilabel:`all` section to show all available plugins.

	.. image:: ./img/pluginmanagerall.png

3. In the search box, type `bridge` to filter the list of available plugins.

	.. image:: ./img/pluginmanagerfiltered.png

4. Click on the :guilabel:`GeoCat Bridge` plugin entry to display the information about the plugin:

	.. image:: ./img/pluginmanagerbridge.png

5. Click on :guilabel:`Install` to install the plugin.

6. Once the plugin is installed, close the Plugin Manager and you will find a new menu entry under the :menuselection:`Web` menu, which contains the menus from the Bridge plugin.

	.. image:: ./img/bridgemenuentry.png

7. You will also find a new toolbar button.

	.. image:: ./img/bridgetoolbarbutton.png
