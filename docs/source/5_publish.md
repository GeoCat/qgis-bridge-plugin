# Publish data


## Supported Layers

GeoCat Bridge supports the following layer types:

-   Vector layers from any source
-   Raster layers from any source
-   Layer groups

## How to publish

Click on the Publish wizard icon ![publish_button](./img/publish_button.png) on the
Bridge toolbar to open the *Publish Wizard* dialog.

### Publish Wizard dialog

The *Publish Wizard* shows all the publishable layers in your project.

![Publish Wizard dialog.](./img/publish_layers1.png)

You can select the layers from the list to publish:

![Select layers to publish](./img/publish_layers2.png)

An icon ![published](./img/published.png) is shown next to the layer name
if the layer\'s metadata and/or map data is published in the currently
selected server(s).

### Edit metadata and select attributes

In the *Layer panel* the user can for each layer:

-   Edit the metadata (see
    [Metadata Editing](8_metadata_editing))
-   Select the attributes to publish as part of the map service.
    Attributes can only be selected for vector data.

![Layer panel, with open metadata tab](./img/publish_layers3.png)

![Layer panel, with open data tab](./img/publish_layers4.png)


### Publishing

When you finished configuring the properties for all map layers, click
on the *Publish* button to start the publishing process. During this
process, a progress bar is shown to indicate the status of the
publication proces:

![Progress dialog](./img/publish_layers5.png)

When the publication process is finished, a summary of the result is
shown:

![Publish result summary](./img/publish_layers_report.png)

## View published layers on server(s)


The context menu in the layers list provides a quick access to view the
published data on the server(s):

![Context menu](./img/publish_layers_context_menu.png)

-   *View metadata*: If the metadata is already published in a catalogue
    server, this option opens a browser to show the metadata from the
    server.

![Published metadata in the GeoNetwork Opensource catalog](./img/preview_gnmetadata.png)

-   *View WMS layer*: Opens up a layer preview page for the selected map
    server with the selected layer.
-   *View all WMS layers*: Opens up a layer preview page for the
    selected map server with all published layer in the map project
    (MXD).

![Layer preview of all published layers in map project](./img/preview_layers.png)

When a data or metadata server is selected and there are issues connecting to it, the server
box appears framed in a red box.

![Failed to retrieve data from servers](./img/retrievingFailed.png)

Unpublish data and metadata
---------------------------

### Remove data and metadata all layers

![remove](./img/remove.png) removes both the metadata and map data of all
selected layers from the publishing server(s).

![Remove all layer button is located in right upper corner of the layer list panel](./img/remove_all.png)

::: tip Note

When removing data from GeoServer, Bridge does not remove the spatial
data files, such as Shapefile, GeoPackage and GeoTIFF. GeoServer does
not allow to remove these files through the REST API. When publishing to
GeoServer with PostGIS, Bridge will not remove the data tables from
PostGIS.
:::

### Remove data and metadata individual layers

If you want to withdraw only metadata or map data for a specific layer,
use the context menu in the layers list.

-   *Unpublish metadata*: remove the metadata from the selected
    catalogue server.
-   *Unpublish data*: remove the map data from the selected map server.

![Context menu published layers](./img/publish_layers_context_menu.png)

### Export files

To export your files locally, use the offline export options in Bridge.
The offline export makes it possible to export the metadata and
symbology in the following formats:

-   SLD (symbology)
-   Geostyler (symbology)
-   MapboxGL (symbology)
-   ISO19319-XML (metadata)

![Offline export](./img/offline_export.png)

Select a folder and the corresponding files will be created in it for
all the layers currently selected.

