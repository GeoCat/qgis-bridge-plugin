# QGIS Bridge Plugin

GeoCat Bridge making publishing geospatial data on the internet as easy as hitting the Publish button.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.md)

## Installation

To install, follow these steps:

- Clone this repository using `git clone --recursive`.

- Run `git submodule update --init` to fetch the code of the dependencies that are used by the plugin, which are contained in other repos that are declared as submodules of this one.

- Copy the `geocatbridge` folder in your QGIS 3 plugins folder.

- Start QGIS and you will find the Geocat Bridge plugin in the plugins menu. If it's not available yet, activate it in the QGIS Plugin Manager.

- When updating to a newer version you may run into challenges due to changed configuration parameters. Go to QGIS settings > Advanced settings, remove the 'geocatbridge' group and restart QGIS.

This plugin is compatible with QGIS 3.4 or later.

## Using GeoCat Bridge

While GeoCat Bridge is new to QGIS using the plugin is very close to the ArcGIS extension described below:

* [GeoCat Bridge Manual](http://bridge-manual.geocat.net/3/3.1/index.html)

## Translating the plugin

This project uses [transifex.com](https://www.transifex.com/geocat/bridge-common) to manage translations. Join a translation team (or request a new language) to bring bridge to as many users as possible.

