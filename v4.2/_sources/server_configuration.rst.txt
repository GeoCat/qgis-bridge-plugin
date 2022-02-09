.. _ServerConnections:

Server Connections
==================

Before you can publish data with |app_name|, you will have to configure one or more server connections.
This can be achieved in the *Servers* section of the |short_name| dialog:

.. image:: ./img/servers.png


Adding connections
##################

Click :guilabel:`New Server` and choose one of the supported server types to create a new server connection:

- GeoServer
- MapServer
- PostGIS
- GeoNetwork

| Fill in the required parameters and click the :guilabel:`Save` button to store the connection details.
| You can edit the parameters of a server at any given time. Just select the server connection in the left panel, and edit the fields you wish to change in the right panel.

If you wish to remove a server connection, select it from the left panel and click the :guilabel:`Remove` button.
The :guilabel:`Duplicate` button may come in handy if you wish to try out an alternative configuration based on an existing
server connection.

| |short_name| will automatically store all server connections in the QGIS settings for later use.
| However, sometimes you might want to backup or share all the configured server connections. The :guilabel:`Export` button will
  allow you to *save* a JSON file of the current configuration.
| The :guilabel:`Import` button will do the opposite and *load* server connections from a JSON file. Note that the imported connections will be
  *added* to the list (i.e. no existing connections will be removed). |short_name| will append a numeric suffix to server connections
  with a name that already exists.

Below you can find more info about the different types of services and connections supported by |short_name|.


GeoNetwork
----------

Configure a GeoNetwork connection to publish your metadata to an online catalog (CSW).

.. image:: ./img/servers_geonetwork.png


| You can set a (unique) name to identify the connection, the server URL, and the corresponding credentials (user with publish permissions).
| The default GeoNetwork node is ``srv``, which will be used if you leave the *Node* field empty.

Click :guilabel:`Test Connection` to verify that the connection can be established.


GeoServer
---------

| Configure a GeoServer connection to publish your geodata (layers and symbology) as a map service.
| When you add a new GeoServer connection, |short_name| will automatically add the corresponding WMS and/or WFS endpoints to QGIS, so you can easily add to the server layers to your project, if needed.

.. image:: ./img/servers_geoserver.png


| You can set a (unique) name to identify the connection, the server URL, and the corresponding credentials (user with publish permissions).
| The URL can point to the GeoServer base URL (e.g. ``http://localhost:8080/geoserver``) or the REST API URL (e.g. ``http://localhost:8080/geoserver/rest``). Both URLs will work.

If required, you can create and publish Mapbox styles for vector tiles. Mapbox styles and sprite sheets will be processed
after all layers were successfully published to GeoServer.

Click :guilabel:`Test Connection` to verify that the connection can be established.

You should also specify how layer data will be stored on the server. Three different methods are available:

File-based storage
^^^^^^^^^^^^^^^^^^

| The layer data is uploaded and stored as files in the GeoServer target workspace on the server.
| |short_name| prefers to upload vector data as GeoPackages and raster data as GeoTIFF files.

.. _PostGISDirectOption:

Import into PostGIS database (direct connect)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| The layer data is uploaded to tables in a PostGIS database directly (i.e. by |short_name|, see `PostGIS`_).
| GeoServer will *not* handle the database upload, but merely establish a link to the database table in the created layer(s). This will require a direct PostGIS connection, which you can set up in the *Servers* section of |short_name| as well (see below).
| Note that GeoServer should also have read access to that PostGIS connection.

Import into PostGIS database (handled by GeoServer)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| The layer data is uploaded to tables in a PostGIS database by GeoServer. This method requires the GeoServer Importer extension, which only handles Shapefile imports for vector data.
| This means that if the data is stored in a GeoPackage originally, attribute names may be renamed due to the 10 character limit of the Shapefile `.dbf` file upon export. Bridge handles this automatically and also makes sure that field names referenced in styles renamed accordingly.
| You must select a suitable PostGIS datastore on the GeoServer instance. Selecting this option will trigger a process that lists all the available datastores in each GeoServer workspace (which might take some time):

.. image:: ./img/servers_geoserver2.png


.. note::   | The listed datastores will be prefixed by the workspace name to which they belong.
            | This does **not** mean that the layers will be published to that workspace as well.
            | |short_name| always publishes layers to a (new) workspace named after the QGIS project name
              (see :ref:`HowToPublish`), but it will use the same datastore *connection details* as
              the datastore that you have selected.

| If you wish to add a new PostGIS-backed datastore, click the :guilabel:`Add datastore` button.
| This will open a dialog that allows you to specify the connection details. Make sure that GeoServer has full access to the specified PostGIS instance.
| For more options (or if you wish to specify a JNDI connection pool) please create the datastore using the GeoServer admin page instead.

.. warning::    | Neither the GeoServer REST API nor the Importer extension is authorized to delete underlying PostGIS layer data tables.
                | This means that Bridge also won't be able to clean up these data tables and that each publication will create new tables in the database,
                  adding a numeric suffix to the table name and GeoServer feature type to avoid conflicts. If you (re)publish frequently,
                  this may lead to a lot of redundant data!
                | Therefore, it's recommended to create a clean-up script on the database side that will remove any "orphaned" tables
                  that were created by GeoServer, but are no longer used by any feature type.


PostGIS
-------

Configure a PostGIS connection if you wish to upload layer data to PostGIS directly.
Setting up this connection is required when using the :ref:`PostGISDirectOption` in a `GeoServer`_ connection.

.. image:: ./img/servers_postgis.png


.. note::   JNDI connection pool support is currently unavailable.


MapServer
---------

Configure a MapServer connection to publish your map (layer data and symbology).
A MapServer endpoint (Mapfile) is created for each QGIS project.

.. image:: ./img/servers_mapserver.png


Under *Storage*, configure how |short_name| should save the MapServer data.
Choose *Local path* to store all files on the local file system. Choose *FTP service* to transmit the
files over FTP to the online MapServer instance. Depending on which option is selected, you will see some additional parameters that must be configured:

.. image:: ./img/servers_mapserver2.png


Proxies & certificates
######################

The GeoNetwork and GeoServer connections mentioned above communicate with the server over HTTP(S) and all their outgoing traffic is handled by the Python ``requests`` library.
Currently, |app_name| does *not* provide a way to set up a proxy server for these connections, and any QGIS proxy settings that may have been defined are ignored.
There are plans to add proxy support in future QGIS |short_name| releases.

Any QGIS SSL certificate settings are also ignored, which means that |short_name| will *not* be able to connect to servers that use self-signed certificates, for example.
However, there is a workaround to this problem. You could set a system environment variable called ``REQUESTS_CA_BUNDLE`` that points to a *.pem* certificate bundle.
This bundle should include the root certificate and any intermediate certificates that are required to verify the authenticity of the server certificate.
