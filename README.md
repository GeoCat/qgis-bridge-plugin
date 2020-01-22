# QGIS Bridge Plugin

GeoCat Bridge making publishing geospatial data on the internet as easy as hitting the Publish button.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.md)

## QGIS Plugin repository

The plugin can be added to QGIS through the [QGIS Plugin Repository](https://plugins.qgis.org/plugins/geocatbridge/). The plugin is currently registered as 'experimental'.

## Installation

To install the latest version from this repository, follow these steps:

- Clone this repository using `git clone --recursive`.

- Run `git submodule update --init` to fetch the code of the dependencies that are used by the plugin, which are contained in other repos that are declared as submodules of this one.

- Copy the `geocatbridge` folder in your QGIS 3 plugins folder.

- Start QGIS and you will find the Geocat Bridge plugin in the plugins menu. If it's not available yet, activate it in the QGIS Plugin Manager.

- When updating to a newer version you may run into challenges due to changed configuration parameters. Go to QGIS settings > Advanced settings, remove the 'geocatbridge' group and restart QGIS.

This plugin is compatible with QGIS 3.4 or later.

## Documentation

The documentation is found in the `docs` folder. Documentation is based on [Sphinx](https://www.sphinx-doc.org).

A script named `builddocs.py` allows to build the documentation for different versions of the plugin. See the [comments in the script](https://github.com/GeoCat/qgis-bridge-plugin/blob/master/docs/builddocs.py#L7-L20) to know more about the options and modifiers it accepts

## Packaging

To package the plugin, run the `build.py` script. It builds the documentation and zips it along with the plugin code.

A `geocatbridge.zip` file is generated in the repo root.


## Translating the plugin

This project uses [transifex.com](https://www.transifex.com/geocat/bridge-common) to manage translations. Join a translation team (or request a new language) to bring Bridge to as many users as possible.

