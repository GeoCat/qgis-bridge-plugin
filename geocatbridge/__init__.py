# -*- coding: utf-8 -*-

__author__ = 'Victor Olaya'
__date__ = 'April 2019'
__copyright__ = '(C) 2019 Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

def classFactory(iface):
    from .plugin import Geocatbridge
    return Geocatbridge(iface)

