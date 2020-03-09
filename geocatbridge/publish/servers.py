import json

from qgis.PyQt.QtCore import QSettings

from geocatbridge.publish.geonetwork import GeonetworkServer
from geocatbridge.publish.geoserver import GeoserverServer
from geocatbridge.publish.geocatlive import GeocatLiveServer
from geocatbridge.publish.mapserver import MapserverServer
from geocatbridge.publish.postgis import PostgisServer
    
SERVERS_SETTING = "geocatbridge/BridgeServers"

_servers = {}

def readServers():
    global _servers
    try:
        value = QSettings().value(SERVERS_SETTING)
        if value is not None:
            storedServers = json.loads(value)            
            for serverDef in storedServers:
                try:
                    s = serverFromDefinition(serverDef)
                    _servers[s.name] = s
                except:
                    pass
    except KeyError:
        pass
 
def serverFromDefinition(defn):
    return globals()[defn[0]](**defn[1])

def serversAsJsonString():
    servList = []
    for s in _servers.values():
        d = {k:v for k,v in s.__dict__.items() if not k.startswith("_")}
        servList.append((s.__class__.__name__, d)) 
    return json.dumps(servList)

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



class CswServer(): 
    pass