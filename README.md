# Bridge for QGIS

_GeoCat Bridge for QGIS_ is the light-weight open-source version of the proprietary _GeoCat Bridge for ArcGIS_ plugin.
It allows QGIS users to share geospatial (meta)data to cloud-based platforms like GeoServer, GeoNetwork, and MapServer.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) 
[![Latest Documentation](https://img.shields.io/badge/Documentation-chocolate?logo=readthedocs&logoColor=white)](https://geocat.github.io/qgis-bridge-plugin/latest/) 
[![Join the chat at https://gitter.im/GeoCat/Bridge](https://img.shields.io/badge/Gitter-Chat-gray?logo=gitter&labelColor=ED1965)](https://gitter.im/GeoCat/Bridge?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) 
[![Minimal QGIS version](https://img.shields.io/badge/QGIS-3.16%2B-white?logo=qgis&logoColor=white&labelColor=589632)](#)

## Installation

The easiest and recommended way to install the plugin, is through the [QGIS Plugin Repository](https://plugins.qgis.org/plugins/geocatbridge/).
If you install Bridge using the QGIS Plugin Manager dialog, you will automatically be notified if there is a new version.

Alternatively, you can install the plugin from this GitHub repository by following these steps:

- Clone this repository using `git clone` (or `git clone --recurse-submodules`, in which case you can skip the next step).
- Run `git submodule update --init` to fetch the code of the dependencies (e.g. [`bridgestyle`](https://github.com/GeoCat/bridge-style)) that are used by the plugin, which are contained in other repositories (submodules).
- Copy the `geocatbridge` folder into your QGIS 3.x Python plugins folder or leave the code where you cloned it and create a symbolic link to it (recommended for development).
- Start QGIS and you will find the GeoCat Bridge plugin in the Web menu. If you don't see it, you may still need to activate it in the QGIS Plugin Manager, where it will be listed as a so-called _core plugin_.
- When updating to a newer version you may run into challenges due to changed configuration parameters. Go to **QGIS settings > Advanced** settings, remove the 'geocatbridge' group and restart QGIS.

To find which QGIS version is compatible with Bridge, please have a look at the badge above or refer to the [`metadata.txt`](/geocatbridge/metadata.txt) file.

## Documentation

The Bridge documentation is available for all releases at [GitHub Pages](https://geocat.github.io/qgis-bridge-plugin/).

If you wish to build the documentation yourself or edit the source, please look for the [`docs`](/docs) folder. The documentation is written in reStructuredText (reST) and can be built using [Sphinx](https://www.sphinx-doc.org).

A script named [`builddocs.py`](/docs/builddocs.py) allows to build the documentation for different versions of the plugin. See the comments at the top of the script to find out how to use it, or simply call `python builddocs.py` in your terminal to display the CLI help.

## Support

[GeoCat](https://www.geocat.net) offers minimal support to Bridge community users and will reply to all questions and issues. However, please note that only paying GeoCat customers are entitled to full support and will be prioritized.

If Bridge encounters a bug, it will display a crash report which you can send to GeoCat through a [support form](https://my.geocat.net/submitticket.php?step=2&deptid=4). We encourage all users to do this (please include a short description of what you were trying to do), so we gain insight how the community is using Bridge, allowing us to improve the software.

Alternatively, you can open a new [issue](https://github.com/GeoCat/qgis-bridge-plugin/issues), if you have a GitHub account.

## Packaging

To package the plugin for QGIS, run the  [`build.py`](/build.py) script. It creates a ZIP archive called `GeoCat_Bridge.zip` in the `build` folder of the cloned repository, that only includes the relevant plugin code for deployment and leaves out debug or test code.

## Contributing

We welcome all useful contributions to the plugin, whether it is a bug fix, a new feature, or a translation.

### Development

At [GeoCat](https://www.geocat.net), we primarily use [PyCharm](https://www.jetbrains.com/pycharm/) for development, but you can use any IDE you like. The plugin is written in Python and uses the Qt framework for the user interface (PyQt5).  

For Qt UI development, you can use the Qt Designer that comes with the QGIS installation. 

#### Debugging

If you are using PyCharm like us, you can use its remote debugger while running QGIS to set breakpoints and step through the code.  
To make this work, you could:

- Set up a symbolic link (directory junction) in the QGIS python plugin directory called `geocatbridge` that points to the `geocatbridge` folder in the cloned repository.
- Using pip, install the `pydevd-pycharm` package in the QGIS Python environment.
- Run the [`setup_debug.py`](/debug/setup_debug.py) script, which will inject some code in the [`plugin.py`](/geocatbridge/plugin.py) file that connects to the remote debugger.
- In PyCharm's _Run/Debug Configurations_, create a new _Python Debug Server_ configuration with the correct host and port settings.
- Start the remote debugger configuration in PyCharm and then start QGIS. The plugin will connect to the debugger and automatically set a breakpoint at the `__init__` step of the `plugin.py`.
- When you are done coding, don't forget to roll back the changes made to `plugin.py` by the `setup_debug.py` script.

#### Developing new server types

Perhaps you may be interested in developing a new kind of server for Bridge to connect to.  

Server types are discovered and loaded dynamically by Bridge in a plugin-like fashion.  
This means that you can develop and add new servers to the [`servers`](/geocatbridge/servers) folder.

To create a new server type, you need to:

- Think of a good module name for the server type, e.g. `myserver`. This name must be used consistently for all related files (e.g. `myserver.py`, `myserver.ui`, etc.).
- Add the business logic for the server to a new Python file in the [`models`](/geocatbridge/servers/models) folder. The model should inherit from the `ServerBase` class in [`bases.py`](/geocatbridge/servers/bases.py) or one if its more concrete bases.
- Add a new Qt UI file to the [`views`](/geocatbridge/servers/views) folder, along with the view model Python file.

Take a look at the existing server types to see how they are implemented.

### Translating the plugin

This project uses [transifex.com](https://www.transifex.com/geocat/bridge-common) to manage translations. Join a translation team (or request a new language) to bring Bridge to as many international users as possible.
