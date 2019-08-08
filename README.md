# GeoCatBridge

A plugin to publish data and metadata from QGIS.

Usage is almost completely identical to the ArcGIS version, which is documented [here](http://bridge-manual.geocat.net/3/3.1/index.html)

To install:

- Clone this repository using `git clone --recursive`.

- Run `git submodule update --init` to fetch the code of the dependencies that are used by the plugin, which are contained in other repos that are declared as submodules of this one.

- Copy the `geocatbridge` folder in your QGIS 3 plugins folder.

- Start QGIS and the plugin should be already available. If it's not, make sure that it's active in the QGIS Plugin Manager.

