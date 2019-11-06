# Server Connections

Configure your server connections to publish your data and metadata to.



## Add new connection

Click *New* ![](./img/add_button.png) and choose one of the supported
server connection types to create a new server:

-   GeoCat Live
-   GeoServer
-   MapServer
-   PostGIS
-   GeoNetwork
-   CSW

![Add a new server](./img/new_server.png)


## GeoCat Live

GeoCat Live is a SDI platform hosted by GeoCat. Depending on your GeoCat
Live configuration Bridge is able to publish metadata to a catalogue
server (CSW) and the layers of the map to a mapserver
(WMS/WFS/WCS/WMTS). Components used

![GeoCat Live server configuration](./img/geocatlive_server.png)

To configure a GeoCat Live connection first fill in the instance
identifier and then click connect. This will retrieve the available
server connections for the GeoCat Live instance you are connecting to.
GeoCat Live connection in the figure above has a GeoServer and
GeoNetwork connection available. For both the credentials need to be
supplied. When publishing Bridge will publish automatically to all
available server connections of your Live instance.

| Name                          | Name of the server connection                       |
| ----------------------------- | --------------------------------------------------- |
| Instance identifier           | Identifier that uniquely identifies the instance    |
| GeoServer username/password   | Credentials of a user with privileges to publish    |
| GeoNetwork username/password  | Credentials of a user with privileges to publish    |

## GeoNetwork or generic CSW connection

Configure a GeoNetwork or generic CSW connection to publish your
metadata to an online catalogue. If the catalog is GeoNetwork then
preferably use a GeoNetwork connection. Using the GeoNetwork connection
allows to publish also a thumbnail for the dataset.

A CSW server should support CSW-transactions to be able to publish to it
with Bridge.

![GeoNetwork server configuration](./img/publish_servers1.png)

![CSW server configuration](./img/publish_servers2.png)

| Label              | Content  |
| ------------------ | --------------------------------------- |
| Name               | Name of the server connection |
| Url                | Base url of the catalog server |
| Username/password  | Credentials of a user with privileges to publish |
| Default server     | Set as default server |
| Metadata profile   | Choose the metadata profile |

Click *Connect* to test the server connection.

![Server connection test](./img/publish_servers5.png)

## GeoServer connection

Configure a GeoServer connection to publish your data to GeoServer.

![GeoServer server configuration](./img/publish_servers3.png)

Fill the form fields.

| Name | Name of the server connections                |                            |
| ---- | --------------------------------------------- |--------------------------- |
| Default | Set as default server           |                            |
| Url  | Base url of the GeoServer server      |                            |
| Username/password | Credentials of a user with privileges to publish     |                            |
| Managed workspace | Each ArcMap project (.mxd) represents 1 geoserver workspace     |                            |
| Workspace | If not `managed workspace`, layers from various projects are published to this workspace |                            |
| Data store | Select the datastore to store data in                         |                            |
| *Data management* |                                 |                            |
|      | Upload data                     | Upload data to GeoServer using Shapefile or GeoPackage and GeoTIFF.    |
|      | Store in PostGIS                | Store data in PostGIS through direct connection with PostGIS database. This option requires the database to be accessible locally (by ArcMAP).       |
|      | Reference data                  | Publish data in GeoServer by referencing existing data from a database.      |

<!-- 
+\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--+\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--+\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--+

With the option `Upload data` there is an additional option to select a
File based storage or Database storage. To enable storage in a database
select an existing GeoServer Datastore or create a new Datastore by
clicking \"+\". The database connection details are relative to the
remote GeoServer. There is no need to expose the database locally. The
database user should have `create` and `write` privileges on the
database.

When using `Reference data`, Bridge currently only supports Oracle
databases. Make sure to use MDSYS.SDO\_GEOMETRY in stead of
SDE.ST\_GEOMETRY to store geometries in Oracle and the data is spatially
indexed. Oracle layers can be exposed to ArcMAP via ArcSDE. -->

### Managed Workspace

When this option is turned on, Bridge will manage about the workspaces
in GeoServer by enforcing a one to one relationship between ESRI map
projects (.mxd) and workspaces. When publishing a `mapdocument_a.mxd`
with layer `layer_a` and `layer_b`, bridge will create a new workspace
`mapdocument_a` in GeoServer and publish both layers in this workspace.
Workspace mode is required if you want to publish layers in a hierarchy
similar to the ArcMAP Table of Contents. Note that layers will be
removed from GeoServer if they don\'t exist in the local mxd anymore.
When this option is turned off you have to select a workspace in which
published layers will be published as part of the server configuration,
no layers are removed automatically.

## PostGIS connection

Configure a PostGIS connection to publish your map data to PostGIS. The
PostGIS connection can be used in three different publish scenarios:

1.  Publish only map data to PostGIS
2.  Publish map layers to GeoServer and store data directly in PostGIS
    using a direct database connection
3.  Publish map layers to MapServer and store data directly in PostGIS
    using a direct database connection

![PostGIS server configuration](./img/publish_server_postgis.png)

## MapServer connection

MapServer uses `Managed Workspaces` mode by default. A mapserver
endpoint (mapfile) is created for each local ArcMAP project.

Configure a MapServer connection to publish your maps from ArcGIS
Desktop® to MapServer. When using [Mapserver 4
Windows](http://www.ms4w.org) choose *Use default MS4W values* to fill
out the MapServer details form.

![MapServer server configuration](./img/publish_servers6.png)

In the *Uploading data* tab configure how Bridge stores data for your
MapServer connection. Choose *Local path* to store the files in a
location on the local file system. Choose *FTP service* to transmit the
files over FTP to the MapServer server.

![Managed workspace](./img/publish_servers8.png)

Bridge currently does not offer functionality to deactivate managed
workspace for Mapserver. This means that each ArcMap project is
published as a single service endpoint (mapfile).

## MapServer data connection

In the *Data settings* tab enable *Store data in PG* to have Bridge
store vector data in a PostGIS database. When enabled you can choose a
connection from the available PostGIS connections. To create a new
PostGIS connection see [PostGIS connection](7_server_configuration.html#postgis-connection).

![MapServer PostGIS configuration](./img/publish_servers10.png)

### Copy fonts to MapServer

Bridge can be configured to copy the fonts used in your symbology to
MapServer. See [CopyFontsMapServer](6_configuration_extension.html#CopyFontsMapServer) for more details.
