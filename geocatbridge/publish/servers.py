import json
from .sldadapter import getCompatibleSldAsZip
from .exporter import exportLayer
from qgiscommons2.network.networkaccessmanager import NetworkAccessManager
from qgis.PyQt.QtCore import QSettings
from geocatbridgecommons.geoservercatalog import GeoServerCatalog
from geocatbridgecommons.catalog import GeodataCatalog, MetadataCatalog
from qgis.core import QgsMessageLog, Qgis

SERVERS_SETTING = "geocatbridge/BridgeServers"

_servers = {}

def readServers():
    global _servers
    try:
        storedServers = json.loads(QSettings().value(SERVERS_SETTING))
        print(storedServers)
        for serverDef in storedServers:
            s = _serverFromDefinition(serverDef)
            _servers[s.name] = s
    except KeyError:
        pass

def _serverFromDefinition(defn):
    return globals()[defn[0]](**defn[1])

def _updateStoredServers():
    servList = []
    for s in _servers.values():
        d = {k:v for k,v in s.__dict__.items() if k not in ["isDataCatalog", "isMetadataCatalog"]}
        servList.append((s.__class__.__name__, d))    
    QSettings().setValue(SERVERS_SETTING, json.dumps(servList))

def allServers():
    return _servers

def addServer(server):
    _servers[server.name] = server
    _updateStoredServers()

def removeServer(name):
    del _servers[name]
    _updateStoredServers()

def geodataServers():
    return {name: server for name, server in _servers.items() if server.isDataCatalog}

def metadataServers():
    return {name: server for name, server in _servers.items() if server.isMetadataCatalog}


class GeodataServer():
    
    def unpublishData(self, layer):
        self.catalog().delete_layer(layer.name())
        self.catalog().delete_style(layer.name())    

class GeoserverServer(GeodataServer):

    UPLOAD_DATA = 0
    STORE_IN_POSTGIS = 1

    def __init__(self, name, url="", authid="", storage=0, workspace="", datastore="", postgisdb=None):
        self.name = name
        self.url = url
        self.authid = authid
        self.storage = storage
        self.workspace = workspace
        self.datastore = datastore
        self.postgisdb = postgisdb
        self.isMetadataCatalog = False
        self.isDataCatalog = True

    def catalog(self):
        nam = NetworkAccessManager(self.authid, debug=False)
        return GeoServerCatalog(self.url, nam, self.workspace)

    def publishStyle(self, layer):
        style = getCompatibleSldAsZip(layer)
        self.catalog().publishStyle(layer.name(), zipfile = style)
        
    def publishLayer(self, layer, fields):        
        if layer.type() == layer.VectorLayer:
            if self.storage == self.UPLOAD_DATA:
                filename = exportLayer(layer, fields)
                style = getCompatibleSldAsZip(layer)
                self.catalog().publish_vector_layer_from_file(self, filename, layer.name(), style, layer.name())
            else:
                self.postgisdb.importLayer(layer, fields)
                authConfig = QgsAuthMethodConfig()                
                QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
                username = authConfig.config('username')
                passwd = authConfig.config('password')
                self.catalog().publish_vector_layer_from_postgis(self, postgisdb.host, postgisdb.port, 
                                        postgisdb.database, postgisdb.schema, layer.name(), username, passwd, 
                                        layer.crs().authid(), layer.name(), style, layer.name())
        elif layer.type() == layer.RasterLayer:
            filename = exportLayer(layer, fields)
            style = getCompatibleSldAsZip(layer)
            self.catalog().publish_raster_layer_file(self, filename, layer.name(), style, layer.name())



class MapserverServer(): 
    pass

class GeocatLiveServer(): 
    pass

class GeonetworkServer():

    def __init__(self, name, url="", authid="", profile=""):
        self.name = name
        self.url = url
        self.authid = authid
        self.profile = profile
        self.isMetadataCatalog = True
        self.isDataCatalog = False

    def publishLayerMetadata(self, layer):
        pass

class PostgisServer(): 
    
    def __init__(self, name, authid="", host="localhost", port="5432", schema="public", database="db"):
        self.name = name
        self.host = host
        self.port = port
        self.schema = schema
        self.database = database
        self.authid = authid
        self.isMetadataCatalog = False
        self.isDataCatalog = False

    def importLayer(self, layer, fields):
        pass

class CswServer(): 
    pass