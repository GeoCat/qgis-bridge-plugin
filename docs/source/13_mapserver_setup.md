# Mapserver Setup

Besides mapserver make sure proj is available. Configure the proj path as part of the mapserver configuration. You can also install [mapcache](https://mapserver.org/mapcache/) and expose datasets as WMTS. 

Files published by bridge need to be uploaded to a server. You can either configure a path on the local network or set up an ftp connection to upload files to a server. FTP needs to be enabled on the server, for example using [mod_ftp](https://httpd.apache.org/mod_ftp/ftp) in apache. 

To use some of the functionality in Bridge Mapserver needs to be build with some modules required. You can download pre-build binaries with modules enabled on the [Mapserver download page](https://www.mapserver.org/download.html). Alternative is to build mapserver from sources.

## GeoPackage

Mapserver needs support for OGR to be able to load the GeoPackage format. Verify OGR is available and contains the [GeoPackage driver](https://www.mapserver.org/input/vector/sqlite.html). 

## Oracle 

To publish layers from an Oracle database in Mapserver it is required to have the *Oracle* [support](https://www.mapserver.org/input/vector/oracle.html) available. 
