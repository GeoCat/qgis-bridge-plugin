# coding: utf-8

import os
import site

# Make sure that QGIS and Bridge can find the bridgestyle lib
site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/libs/bridgestyle'))


def classFactory(iface):
    from .plugin import GeocatBridge
    return GeocatBridge(iface)
