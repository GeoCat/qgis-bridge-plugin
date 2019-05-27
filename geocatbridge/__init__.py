# -*- coding: utf-8 -*-

__author__ = 'Victor Olaya'
__date__ = 'April 2019'
__copyright__ = '(C) 2019 Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import sys
import os
import site

site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/extlibs'))

def classFactory(iface):
    from .plugin import GeocatBridge
    return GeocatBridge(iface)

