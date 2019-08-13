import json
import psycopg2
import requests
from requests.auth import HTTPBasicAuth
from .exporter import exportLayer
from qgiscommons2.network.networkaccessmanager import NetworkAccessManager
from qgiscommons2.files import tempFilenameInTempFolder
from bridgestyle.qgis import saveLayerStyleAsZippedSld
from qgis.PyQt.QtCore import QSettings
from bridgecommon import meftools
from geocatbridge.publish.metadata import uuidForLayer
from bridgecommon.geoservercatalog import GeoServerCatalog
from bridgecommon.geonetworkcatalog import GeoNetworkCatalog
from bridgecommon.catalog import GeodataCatalog, MetadataCatalog
from qgis.core import QgsMessageLog, Qgis, QgsVectorLayerExporter, QgsAuthMethodConfig, QgsApplication, QgsFeatureSink, QgsFields

SERVERS_SETTING = "geocatbridge/BridgeServers"

_servers = {}

def readServers():
    global _servers
    try:
        value = QSettings().value(SERVERS_SETTING)
        if value is not None:
            storedServers = json.loads(value)            
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
        d = {k:v for k,v in s.__dict__.items() if not k.startswith("_")}
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
    return {name: server for name, server in _servers.items() if server._isDataCatalog}

def metadataServers():
    return {name: server for name, server in _servers.items() if server._isMetadataCatalog}


class GeodataServer():
    
    def unpublishData(self, layer):
        self.dataCatalog().delete_layer(layer.name())
        self.dataCatalog().delete_style(layer.name())    

class GeoserverServer(GeodataServer):

    UPLOAD_DATA = 0
    STORE_IN_POSTGIS = 1

    def __init__(self, name, url="", authid="", storage=0, workspace="", postgisdb=None):
        self.name = name
        if url.endswith("rest"):
            self.url = url.strip("/")
        else:
            self.url = url.strip("/") + "/rest"

        self.authid = authid
        self.storage = storage
        self.workspace = workspace
        self.postgisdb = postgisdb
        self._isMetadataCatalog = False
        self._isDataCatalog = True
        nam = NetworkAccessManager(self.authid, debug=False)
        self._catalog = GeoServerCatalog(self.url, nam, self.workspace)

    def dataCatalog(self):
        return self._catalog

    def publishStyle(self, layer):
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            QgsMessageLog.logMessage(w, 'GeoCat Bridge', level=Qgis.Warning)   
        self.dataCatalog().publish_style(layer.name(), zipfile = styleFilename)        
        
    def publishLayer(self, layer, fields):
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            QgsMessageLog.logMessage(w, 'GeoCat Bridge', level=Qgis.Warning)
        QgsMessageLog.logMessage("Style for layer %s exported as zip file to %s" % (layer.name(), styleFilename), 'GeoCat Bridge', level=Qgis.Info)
        if layer.type() == layer.VectorLayer:
            if self.storage == self.UPLOAD_DATA:
                filename = exportLayer(layer, fields)
                self.dataCatalog().publish_vector_layer_from_file(filename, layer.name(), layer.crs().authid(), styleFilename, layer.name())
            else:
                try:
                    db = allServers()[self.postgisdb]
                except KeyError:
                    raise Exception("Cannot find the selected PostGIS database")
                db.importLayer(layer, fields)                
                self.dataCatalog().publish_vector_layer_from_postgis(db.host, db.port, 
                                        db.database, db.schema, layer.name(), 
                                        db._username, db._password, layer.crs().authid(), 
                                        layer.name(), styleFilename, layer.name())
        elif layer.type() == layer.RasterLayer:
            filename = exportLayer(layer, fields)            
            self.dataCatalog().publish_raster_layer(filename, styleFilename, layer.name(), layer.name())

    def testConnection(self):
        try:
            self.dataCatalog().gscatalog.gsversion()
            return True
        except:
            return False


class MapserverServer(): 
    pass

class GeocatLiveServer(): 

    BASE_URL = "https://artemis.geocat.net/geocat-live/api/1.0/order/"

    def __init__(self, name, userid="", geoserverAuthid="", geonetworkAuthid="", profile=0):
        self.name = name
        self.userid = userid
        self.profile = profile
        self.geoserverAuthid = geoserverAuthid
        self.geonetworkAuthid = geonetworkAuthid
        self._isMetadataCatalog = True
        self._isDataCatalog = True
        self._geoserverUrl = None
        self._geonetworkUrl = None
        self._geoserverServer = None
        self._geonetworkServer = None

    def _getUrls(self):
        url = "%s/%s" % (self.BASE_URL, self.userid)
        nam = NetworkAccessManager(None, debug=False)
        response = nam.request(url, "get")
        res = json.loads(response.content)
        for serv in res["services"]:
            if serv["application"] == "geoserver":
                self._geoserverUrl = serv["url"] + "/rest"
            if serv["application"] == "geonetwork":
                self._geonetworkUrl = serv["url"]

    def geoserverServer(self):
        if self._geoserverUrl is None:
            self._getUrls()
        if self._geoserverServer is None:            
            self._geoserverServer = GeoserverServer("GeoServer", self._geoserverUrl, self.geoserverAuthid, workspace="geocatlive") #TODO:workspace
        return self._geoserverServer

    def geonetworkServer(self):
        if self._geonetworkUrl is None:
            self._getUrls()
        if self._geonetworkServer is None:
            self._geonetworkServer = GeonetworkServer("GeoNetwork", self._geonetworkUrl, self.geonetworkAuthid)
        return self._geonetworkServer

    def dataCatalog(self):
        return self.geoserverServer().dataCatalog()

    def metadataCatalog(self):
        return self.geonetworkServer().metadataCatalog()

    def publishLayerMetadata(self, layer):
        self.geonetworkServer().publishLayerMetadata(layer)

    def publishStyle(self, layer):
        self.geoserverServer().publishStyle(layer)
        
    def publishLayer(self, layer, fields): 
        self.geoserverServer().publishLayer(layer, fields)

    def testConnection(self):
        try:
            self._getUrls()
            return True
        except:
            return False        

class TokenNetworkAccessManager():
    def __init__(self, url, username, password):        
        self.url = url.strip("/")
        self.token = None
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
    
    def request(self, url, method, data=None, headers={}):
        if self.token is None:
            self.getToken()
        self.session.headers.update({"X-XSRF-TOKEN" : self.token})    
        method = getattr(self.session, method.lower())
        resp = method(url, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    def getToken(self):                
        xmlInfoUrl = self.url + '/xml.info'
        self.session.post(xmlInfoUrl)
        self.token = self.session.cookies.get('XSRF-TOKEN')
        self.session.headers.update({"X-XSRF-TOKEN" : self.token})

class GeonetworkServer():

    PROFILE_DEFAULT = 0
    PROFILE_INSPIRE = 1
    PROFILE_DUTCH = 2

    def __init__(self, name, url="", authid="", profile=0):
        self.name = name
        self.url = url
        self.authid = authid
        self.profile = profile
        self._isMetadataCatalog = True
        self._isDataCatalog = False
        authConfig = QgsAuthMethodConfig()
        QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
        username = authConfig.config('username')
        password = authConfig.config('password')        
        nam = TokenNetworkAccessManager(self.url, username, password)
        self._catalog = GeoNetworkCatalog(self.url, nam)

    def metadataCatalog(self):
        return self._catalog

    def publishLayerMetadata(self, layer):
        uuid = uuidForLayer(layer)
        filename = tempFilenameInTempFolder(layer.name() + ".qmd")
        layer.saveNamedMetadata(filename)
        transformedFilename = self.transformMetadata(filename)
        mefFilename = tempFilenameInTempFolder(uuid + ".mef")
        meftools.createMef(uuid, transformedFilename, mefFilename)        
        self._catalog.publish_metadata(mefFilename)

    def testConnection(self):
        try:
            self._catalog.me()
            return True
        except:
            return False

    def transformMetadata(self, filename):
        xmlFilename = tempFilenameInTempFolder("metadata.xml")
        with open(filename) as f:
            content = f.read()
        with open(xmlFilename, "w") as f:
            f.write(content)
        return xmlFilename #TODO

class PostgisServer(): 
    
    def __init__(self, name, authid="", host="localhost", port="5432", schema="public", database="db"):
        self.name = name
        self.host = host
        self.port = port
        self.schema = schema
        self.database = database
        self.authid = authid
        self._isMetadataCatalog = False
        self._isDataCatalog = False
        authConfig = QgsAuthMethodConfig()                
        QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
        self._username = authConfig.config('username')
        self._password = authConfig.config('password')

    def importLayer(self, layer, fields):
        uri = "dbname='%s' key='id' host=%s port=%s user='%s' password='%s' table=\"%s\".\"%s\" (geom) sql=" % (self.database, 
                    self.host, self.port, self._username, self._password, self.schema, layer.name())
        
        qgsfields = QgsFields()
        for f in layer.fields():
            if fields is None or f.name() in fields:
                qgsfields.append(f)
        exporter = QgsVectorLayerExporter(uri, "postgres", qgsfields,
                                          layer.wkbType(), layer.sourceCrs(), True)

        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception('Error importing to PostGIS: {0}'.format(exporter.errorMessage()))

        features = layer.getFeatures()
        for f in features:
            if not exporter.addFeature(f, QgsFeatureSink.FastInsert):
                raise Exception('Error importing to PostGIS: {0}').format(exporter.errorMessage())
        exporter.flushBuffer()
        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception('Error importing to PostGIS: {0}').format(exporter.errorMessage())

    def testConnection(self):
        con = None
        try:
            con = psycopg2.connect(dbname=self.database, user=self._username, password=self._password, host=self.host, port=self.port)
            cur = con.cursor()
            cur.execute('SELECT version()')
            cur.fetchone()[0]
            return True
        except:
            return False
        finally:
            if con:
                con.close()

class CswServer(): 
    pass