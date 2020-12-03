import json

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMessageLog, Qgis

from geocatbridge.publish.geonetwork import GeonetworkServer
from geocatbridge.publish.geoserver import GeoserverServer
from geocatbridge.publish.mapserver import MapserverServer
from geocatbridge.publish.postgis import PostgisServer
from geocatbridge.utils import meta

SERVERS_SETTING = f"{meta.PLUGIN_NAMESPACE}/BridgeServers"

_servers = {}


def readServers():
    global _servers
    value = QSettings().value(SERVERS_SETTING)
    if value is None:
        return
    stored_servers = json.loads(value)
    for serverDef in stored_servers:
        try:
            s = serverFromDefinition(serverDef)
        except KeyError:
            known_types = ','.join(c.__name__ for c in (GeonetworkServer, GeoserverServer,
                                                        MapserverServer, PostgisServer))
            QgsMessageLog().logMessage(f"Failed to load '{serverDef[0]}' type: expected one of ({known_types})",
                                       meta.getAppName(), Qgis.Critical)
            continue
        _servers[s.name] = s


def serverFromDefinition(defn):
    return globals()[defn[0]](**defn[1])


def serversAsJsonString():
    serv_list = []
    for s in _servers.values():
        d = {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
        serv_list.append((s.__class__.__name__, d))
    return json.dumps(serv_list)


def _updateStoredServers():
    QSettings().setValue(SERVERS_SETTING, serversAsJsonString())


def allServers():
    return _servers


def addServer(server):
    _servers[server.name] = server
    server.addOGCServers()
    _updateStoredServers()


def removeServer(name):
    del _servers[name]
    _updateStoredServers()


def geodataServers():
    return {name: server for name, server in _servers.items() if server._isDataCatalog}


def metadataServers():
    return {name: server for name, server in _servers.items() if server._isMetadataCatalog}
