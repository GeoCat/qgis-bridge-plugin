# coding: utf-8

def classFactory(iface):
    from .plugin import GeocatBridge
    return GeocatBridge(iface)
