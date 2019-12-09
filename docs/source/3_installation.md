# Installation

The plugin is registered on the QGIS plugin repository as 'experimental'.

In settings of the plugin repository, enable experimental plugins. Then look for a plugin 'GeoCatBridge', install and enable it. Look for the plugin icon on the toolbar or in the 'web' menu.

![Bridge in plugin repository](./img/bridgepluginqgis.png) 

Bridge plugin requires [lxml](https://lxml.de/) helper to be available on the system. The module is made available via the plugin for windows. On Linux and MacOS install the helper using [pip](https://pypi.org/project/pip/).

```
pip install lxml
```
