Publishing Data
###############

.. _LayerTypes:

Supported layer types
=====================

|app_name| supports the following layer types:

-   Standard vector layers (i.e. a `QgsVectorLayer <https://api.qgis.org/api/classQgsVectorLayer.html#details>`_ object)
-   Standard raster layers (i.e. a `QgsRasterLayer <https://api.qgis.org/api/classQgsRasterLayer.html#details>`_ object)
-   Layer groups

.. note::   You may experience that even if your layer is of one of the types listed above,
            |short_name| still does not seem to support it. This could be the case if:

            -   The layer data source is non-spatial (e.g. a CSV)
            -   The layer is a third-party plugin layer (i.e. a `QgsPluginLayer <https://api.qgis.org/api/classQgsPluginLayer.html#details>`_ object)
            -   The layer does not have a CRS (coordinate reference system) or it is invalid
            -   The layer data source is broken or missing
            -   The layer is virtual and stored in memory (i.e. not on disk)
            -   The layer is a web map layer (e.g. WMS)

            In most of the cases you should be able to easily fix these issues, for example by exporting
            the layer, assigning a spatial reference etc. etc.


.. _HowToPublish:

How to publish
==============

If you wish to publish data *online*, you will first need to set up one or more server connections.
Please see :ref:`ServerConnections` for more information on how to add these. Then come back to this page
to continue the publication process.

In the |short_name| dialog, navigate to the :guilabel:`Publish` section.

.. image:: ./img/publish_section.png

Here you can choose the supported layers that you wish to publish, by (un)ticking the checkboxes for each layer:

.. image:: ./img/publish_layers_list.png


If you click on one of the layers in the *Layers panel*, you can see that the :guilabel:`Metadata` and :guilabel:`Attributes` tabs on the right side update
their contents based on the currently selected layer. This will allow you to:

-   Edit the layer metadata (see :ref:`MetadataEditing`)

.. image:: ./img/publish_metadata.png

-   Select the attributes (fields) to publish as part of the map service.
    Attributes can only be selected for vector data.

.. image:: ./img/publish_fields.png

Once you have finished configuring the properties for all map layers that you wish to publish,
please select the destinations server(s) that you would like to use in the :guilabel:`Online` tab at the bottom,
or specify the things you wish to export to a local file on the :guilabel:`Offline` tab.

When publishing online, you can publish your layers to a geodata server, their metadata to a metadata server, or both in one go.
Those servers must be selected from the two available drop-down lists in the :guilabel:`Online` tab.
As mentioned before, these servers should be added beforehand in the :guilabel:`Connections` section of the |short_name| dialog,
as described in :ref:`ServerConnections`.

.. note::   If you are publishing layers to GeoServer, the destination workspace name will be taken from the
            QGIS project name. Therefore, it is important that you save your work *before* publishing it to GeoServer.
            |short_name| will warn you if the current QGIS project has not been saved yet.

When a geodata or metadata server is selected and there are issues connecting to it, the server
drop-down list will show a red border around it and an error message may be shown at the top of the
|short_name| dialog (e.g. bad credentials). Please go to the :ref:`ServerConnections` section to fix the issue(s).

.. image:: ./img/publish_server_error.png

Once you have selected the layers you wish to publish and the destination(s) have been set, click
on the :guilabel:`Publish` button to start the publication process. Note that the :guilabel:`Publish` button
is context-aware, meaning that when the :guilabel:`Online` tab is active, the data will be published online only.

Alternatively, if the :guilabel:`Offline` tab is active and the :guilabel:`Publish` button is pressed, the data will only be
published offline. Please see `Export files`_ and `Removing geodata and metadata`_ as well.

.. tip::    | If you have a lot of data and you wish to continue working with QGIS while layer data is being published,
              you can tick the :guilabel:`Background` checkbox next to the :guilabel:`Publish` button.
            | After you hit the :guilabel:`Publish` button, the |short_name| dialog will close and you will be able to continue working with QGIS.
              Once the publication process has finished, a result dialog (see below) will be shown.

During the publication process, a progress dialog is shown. This may only show up briefly if there is little data to publish:

.. image:: ./img/publish_layers_progress.png

Once the publication process has finished, a result dialog is displayed:

.. image:: ./img/publish_layers_report.png

If there are any warnings or errors, there will be a little warning sign button in the layer result field.
Click on this button to open another dialog that will display all the warning or error messages for each layer.

| Once you have uploaded your geodata and wish to update the symbology of your server layers without uploading all layer data again, check the :guilabel:`Symbology only` option.
  The styles of the selected (checked) layers will then be updated, but no layer data will be uploaded and/or overwritten.
| For more information about how |short_name| handles symbology, please read the :ref:`Symbology` section.

.. warning::    **It is currently not possible to add layers to an existing workspace.**

                Each time you publish layers to a GeoServer workspace that already exists, that workspace will be purged and recreated.
                |short_name| will warn you if this is about to happen:

                .. image:: ./img/publish_workspace_warning.png
                   :align: center

                |

                *New in version 4.4.2*: Even though all datastores and styles in the workspace will be removed, the old workspace settings
                and ACL rules will be preserved. This means that you do not have to manually restore those settings.

                If you do not want to clear the entire workspace and keep the old one, you could rename your QGIS project or save it
                under a different name and re-publish the layers. This will create a new workspace on the server using the default settings,
                and preserve the old one.


View published layers on server(s)
==================================

The context menu in the layers list provides quick access to view the
published data on the server(s):

.. image:: ./img/publish_layers_context_menu.png

-   :guilabel:`View metadata`: If the metadata is already published to a catalog
    server, this option opens a browser to show the metadata from the
    server.

.. image:: ./img/preview_gnmetadata.png

-   :guilabel:`View WMS layer`: Opens up a layer preview page for the selected map
    server with the selected layer.
-   :guilabel:`View all WMS layers`: Opens up a layer preview page for the
    selected map server with all published layers in the map project (i.e. GeoServer workspace).

.. image:: ./img/preview_layers.png


Removing geodata and metadata
=============================

| In case you wish to undo the publication process, there is an option to remove all layer data from the server(s).
| If the :guilabel:`Online` tab is active and one or more servers have been selected for publication, a :guilabel:`Clear All` button becomes available.
| Clicking this button will remove all the geodata from the selected data server (if any) and all metadata from the selected
  metadata server (if any). You will be asked for confirmation before any removal takes place.

.. image:: ./img/remove_all.png

.. warning::

    | When removing data from GeoServer, |short_name| cannot always remove all uploaded data,
      because GeoServer does not allow to remove these files through the REST API.
    | For example, if you publish data to GeoServer using a PostGIS datastore,
      the database tables will not be removed when you hit the :guilabel:`Clear All` button.
    | Only the feature type and layer will be removed from GeoServer, but you will have
      to manually remove the underlying table from PostGIS. This also means that republishing
      a certain layer to PostGIS will import its data into a *new* table.


Export files
============

To export your (meta)data and/or style files locally, use the :guilabel:`Offline` export tab in |short_name|.
The offline export functionality makes it possible to export symbology in the following formats:

-   SLD (XML)
-   GeoStyler (JSON)
-   Mapbox GL style (JSON)

Metadata will be exported to the ISO19319 XML format.

.. image:: ./img/offline_export.png

Select a folder and the corresponding files will be created in it for
all the current selected (checked) layers when you click the :guilabel:`Publish` button.
