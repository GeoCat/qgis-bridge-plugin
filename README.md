# Bridge for QGIS

_GeoCat Bridge for QGIS_ is the light-weight open-source version of the proprietary _GeoCat Bridge for ArcGIS_ plugin.
It allows QGIS users to share geospatial (meta)data to cloud-based platforms like GeoServer, GeoNetwork, and MapServer.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.md)

## Installation

The easiest way to install the plugin, is through the [QGIS Plugin Repository](https://plugins.qgis.org/plugins/geocatbridge/).
If you install Bridge using the QGIS Plugin Manager dialog, you will automatically be notified if there is a new version.

Alternatively, you can install the plugin from this GitHub repository by following these steps:

- Clone this repository using `git clone --recursive`.
- Run `git submodule update --init` to fetch the code of the dependencies (e.g. [`bridgestyle`](https://github.com/GeoCat/bridge-style)) that are used by the plugin, which are contained in other repositories (submodules).
- Copy the `geocatbridge` folder into your QGIS 3.x Python plugins folder or leave the code where you cloned it and create a symbolic link to it (recommended for development).
- Start QGIS and you will find the Geocat Bridge plugin in the plugins menu. If you don't see it, you may still need to activate it in the QGIS Plugin Manager, where it will be listed as a so-called _core plugin_.
- When updating to a newer version you may run into challenges due to changed configuration parameters. Go to **QGIS settings > Advanced** settings, remove the 'geocatbridge' group and restart QGIS.

To find out QGIS version compatibility, please have a look at the [`metadata.txt`](/blob/master/geocatbridge/metadata.txt) file.

## Documentation

The Bridge documentation is available for all releases at [GitHub Pages](https://geocat.github.io/qgis-bridge-plugin/).

If you wish to build the documentation yourself or edit the source, please look for the [`docs`](/tree/master/docs) folder. The documentation is written in reStructuredText (reST) and can be built using [Sphinx](https://www.sphinx-doc.org).

A script named [`builddocs.py`](/blob/master/docs/builddocs.py) allows to build the documentation for different versions of the plugin. See the comments at the top of the script to find out how to use it, or simply call `python builddocs.py` in your terminal to display the CLI help.

## Support

GeoCat offers minimal support to Bridge community users and will reply to all questions and issues. However, please note that only GeoCat customers are entitled to full support  and will be prioritized.

If Bridge encounters a bug, it will display a crash report which you can send to GeoCat through a [support form](https://my.geocat.net/submitticket.php?step=2&deptid=4). We encourage all users to do this (please include a short description of what you were trying to do), so we gain insight how the community is using Bridge, allowing us to improve the software.

Alternatively, you can open a new [issue](/issues), if you have a GitHub account.

## Packaging

To package the plugin for QGIS, run the  [`build.py`](/blob/master/build.py) script. It creates a ZIP archive called `GeoCat_Bridge.zip` in the `build` folder of the cloned repository, that only includes the relevant plugin code for deployment and leaves out debug or test code.

## Translating the plugin

This project uses [transifex.com](https://www.transifex.com/geocat/bridge-common) to manage translations. Join a translation team (or request a new language) to bring Bridge to as many international users as possible.
