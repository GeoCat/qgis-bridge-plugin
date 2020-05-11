# -*- coding: utf-8 -*-

import sys
import os
import site

site.addsitedir(os.path.abspath(os.path.dirname(__file__) + "/libs/bridgestyle"))


def classFactory(iface):
    from .plugin import GeocatBridge

    return GeocatBridge(iface)
