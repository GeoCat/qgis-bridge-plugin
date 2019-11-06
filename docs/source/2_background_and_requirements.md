# Background and Requirements

## Background

When publishing data on the Internet it is a common practice to provide
the data using standardized exchange protocols. Adopting standards
facilitates a wide usage of the data. In the geospatial domain the OGC
and ISO TC211 data exchange standards are the industry standards, and
for example required by the European INSPIRE regulations. The Bridge
extension takes care of exporting your map, data, styles and metadata to
opensource mapping platforms that provide data exchange and catalog
services that comply with these standards.

The servers currently supported by Bridge are GeoServer and MapServer
map servers, GeoNetwork Opensource catalogue server and any CSW
transactional compliant catalogue server. The Premium version of Bridge
supports publishing map data to a PostGIS server (in combination with
GeoServer or MapServer, or standalone).

You can also choose to save the metadata and map symbology (as Styled
Layer Descriptor (OGC-SLD)) documents on your computer as files or in a
GeoPackage so you can use them to publish on other software platforms
(deegree, QGIS).

Although not required, it is recommended that you have a GeoServer or
Mapserver and a GeoNetwork Opensource or CSW available and that you have
accounts on those servers with enough privileges to publish map data and
metadata.

[GeoServer](http://geoserver.org/) is the reference implementation of
the Open Geospatial Consortium (OGC) Web Feature Service (WFS) and Web
Coverage Service (WCS) standards, as well as a high performance
certified compliant Web Map Service (WMS).

[MapServer](http://mapserver.org) is an Open Source platform for
publishing spatial data and interactive mapping applications to the web.
Originally developed in the mid-1990's at the University of Minnesota,
MapServer is released under an MIT-style license, and runs on all major
platforms (Windows, Linux, Mac OS X). MapServer is not a full-featured
GIS system, nor does it aspire to be.

[GeoNetwork Opensource](http://geonetwork-opensource.org) is the
reference implementation of the Open Geospatial Consortium (OGC) Catalog
Service for the Web (CSW). It also supports the ISO19115, ISO19119 and
ISO19110 metadata standards. The GeoNetwork Opensource software complies
with the requirements of INSPIRE.

## Requirements

### Client requirements

Bridge supports the following versions of ArcGIS® Desktop (including
minor releases such as 10.5.1):

-   10.1
-   10.2
-   10.3
-   10.4
-   10.5
-   10.6
-   10.7

### Server requirements

#### GeoNetwork

GeoCat Bridge is officially supported on any GeoNetwork latest (3.8) and
2 versions before (3.4 and 3.6). However most of the functionality will
be operational from GeoNetwork version 2.6+.

#### MapServer

Requirement for MapServer are:

-   Officially supported is the latest minor version of Mapserver and 2
    versions before, currently 7.0, 6.4 and 6.2. However any version
    from 5.6.0 is expected to operate fine in most of the cases.
-   FTP connection or file write access to MapServer project path

::: tip Note

When using MapServer 5.X and PostGIS 2.X it is required to load
legacy.sql from your PostGIS installation folder on your spatial
database.
[Legacy.sql](http://postgis.net/docs/PostGIS_FAQ.html#legacy_faq) can be
found in in your PostGIS installation folder.
:::

#### GeoServer

Requirement for GeoServer are:

-   Officially supported versions are 2.15, 2.14 and 2.13. However other
    versions since 2.4 are expected to operate fine in most of the
    cases.
-   On a Linux server it is recommended to install the *msttcorefonts*
    package. Some of the symbols from the default Esri® fonts are mapped
    to equivalent Webdings and Wingdings symbol fonts.
