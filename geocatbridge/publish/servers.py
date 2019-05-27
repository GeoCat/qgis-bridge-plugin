import json
from .sldadapter import getCompatibleSldAsZip
from .exporter import exportLayer
from qgiscommons2.network.networkaccessmanager import NetworkAccessManager
from qgiscommons2.settings import pluginSetting, setPluginSetting
from geocatbridgecommons.geoserver import GeoServerCatalog
from geocatbridgecommons.server import GeodataCatalog, MetadataCatalog

SERVERS_SETTING = "BridgeServers"

_servers = {}

try:
    storedServers = json.loads(pluginSetting(SERVERS_SETTING))
    for serverDef in storedServers:
        s = _serverFromDefinition(serverDef)
        _servers[s.name] = s
except KeyError:
    pass

def _serverFromDefinition(defn):
    return globals()[defn[0]](*defn[1])

def _updateStoredServers():
    servList = [(s.__class__.__name__, s.__dict__) for s in _servers.values()]
    print (servList)
    # setPluginSetting(SERVERS_SETTING, json.dumps(servList))

def allServers():
    return _servers

def addServer(server):
    _servers[server.name] = server
    _updateStoredServers()

def removeServer(server):
    del _servers[server.name]
    _updateStoredServers()

def geodataServers():
    return {name: server for name, server in _servers.items() if isinstance(server.catalog(), GeodataCatalog)}

def metadataServers():
    return {name: server for name, server in _servers.items() if isinstance(server.catalog(), MetadataCatalog)}


class GeodataServer():
    
    def unpublishData(self, layer):
        self.catalog().delete_layer(layer.name())
        self.catalog().delete_style(layer.name())    

class GeoserverServer():

    UPLOAD_DATA = 0
    STORE_IN_POSTGIS = 1

    def __init__(self, name, url="", authid="", storage=0, workspace="", datastore=""):
        self.name = name
        self.url = url
        self.authid = authid
        self.storage = storage
        self.workspace = workspace
        self.datastore = datastore

    def catalog(self):
        nam = NetworkAccessManager(self.authid, debug=False)
        return GeoServerCatalog(self.url, nam, self.workspace)

    def publishLayer(self, layer, fields):
        if layer.type() == layer.VectorLayer:
            if self.storage == self.UPLOAD_DATA:
                filename = exportLayer(layer, fields)
                style = getCompatibleSldAsZip(layer)
                self.catalog().publish_vector_layer_from_file(self, filename, layer.name(), style, layer.name())
            else:
                #TODO
                pass
        elif layer.type() == layer.RasterLayer:
            filename = exportLayer(layer, fields)
            style = getCompatibleSldAsZip(layer)
            self.catalog().publish_raster_layer_file(self, filename, layer.name(), style, layer.name())



class MapserverServer(): 
    pass

class GeocatLiveServer(): 
    pass

class GeonetworkServer(): 
    pass

class PostgisServer(): 
    pass

class CswServer(): 
    pass