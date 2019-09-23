import os
import json
import psycopg2
import requests
from requests.auth import HTTPBasicAuth
import lxml.etree as ET
from .exporter import exportLayer
from qgiscommons2.network.networkaccessmanager import NetworkAccessManager
from qgiscommons2.files import tempFilenameInTempFolder
from bridgestyle.qgis import saveLayerStyleAsZippedSld, layerStyleAsMapfileFolder
from qgis.PyQt.QtCore import QSettings, QSize, QCoreApplication
from qgis.PyQt.QtGui import QImage, QColor, QPainter
from bridgecommon import meftools
from geocatbridge.publish.metadata import uuidForLayer
from bridgecommon.geoservercatalog import GeoServerCatalog
from .mapservercatalog import MapServerCatalog
from bridgecommon.geonetworkcatalog import GeoNetworkCatalog
from bridgecommon.catalog import GeodataCatalog, MetadataCatalog
from qgis.core import (QgsMessageLog, Qgis, QgsVectorLayerExporter, QgsAuthMethodConfig, QgsApplication, 
                        QgsFeatureSink, QgsFields, QgsMapSettings, QgsMapRendererCustomPainterJob, QgsProject)

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

class GeoserverServer():

    UPLOAD_DATA = 0
    STORE_IN_POSTGIS = 1

    def __init__(self, name, url="", authid="", storage=0, workspace="", postgisdb=None):
        self.name = name
        
        if url:
            if url.endswith("rest"):
                self.url = url.strip("/")
            else:
                self.url = url.strip("/") + "/rest"
        else:
            self.url = url

        self.authid = authid
        self.storage = storage
        self.workspace = workspace
        self.postgisdb = postgisdb
        self._isMetadataCatalog = False
        self._isDataCatalog = True
        nam = NetworkAccessManager(self.authid, debug=False)
        self._catalog = GeoServerCatalog(self.url, nam, self.workspace)
        self.setupForProject()

    def dataCatalog(self):
        return self._catalog

    def setupForProject(self):
        if self.workspace is None:
            self._catalog.workspace = os.path.splitext(os.path.basename(QgsProject.instance().absoluteFilePath()))[0]
    
    def prepareForPublishing(self, onlySymbology):
        self. setupForProject()
        if self.workspace is None and not onlySymbology:
            self._catalog.delete_workspace()
        else:            
            self._catalog.workspace = self.workspace

    def publishStyle(self, layer):
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            QgsMessageLog.logMessage(w, 'GeoCat Bridge', level=Qgis.Warning)   
        self.dataCatalog().publish_style(layer.name(), zipfile = styleFilename)        
        
    def publishLayer(self, layer, fields=None):
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            QgsMessageLog.logMessage(w, 'GeoCat Bridge', level=Qgis.Warning)
        QgsMessageLog.logMessage(QCoreApplication.translate("GeocatBridge", "Style for layer %s exported as zip file to %s") % (layer.name(), styleFilename), 
                                'GeoCat Bridge', level=Qgis.Info)
        if layer.type() == layer.VectorLayer:
            if self.storage == self.UPLOAD_DATA:
                filename = exportLayer(layer, fields)
                self.dataCatalog().publish_vector_layer_from_file(filename, layer.name(), layer.crs().authid(), styleFilename, layer.name())
            else:
                try:
                    db = allServers()[self.postgisdb]
                except KeyError:
                    raise Exception(QCoreApplication.translate("GeocatBridge", "Cannot find the selected PostGIS database"))
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

    def unpublishData(self, layer):
        self.dataCatalog().delete_layer(layer.name())
        self.dataCatalog().delete_style(layer.name()) 


class MapserverServer(): 

    def __init__(self, name, local=True, folder="", authid="", host="", port=""):
        self.name = name
        self.folder = folder
        self.useLocalFolder = local
        self.authid = authid
        self.host = host
        self.port = port

        self._isMetadataCatalog = False
        self._isDataCatalog = True

        if local:
            self._catalog = MapServerCatalog(folder=self.folder)
        else:
            authConfig = QgsAuthMethodConfig()
            QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
            username = authConfig.config('username')
            password = authConfig.config('password')
            self._catalog = MapServerCatalog(host=host, port=port, username=username, password=password)            
        
    def dataCatalog(self):
        return self._catalog

    def createStyleFolder(self, layer):
        layerFilename = layer.name() + ".shp"        
        warnings = layerStyleAsMapfileFolder(layer, layerFilename, self.folder)        
        for w in warnings:
            QgsMessageLog.logMessage(w, 'GeoCat Bridge', level=Qgis.Warning)
        QgsMessageLog.logMessage(QCoreApplication.translate("GeocatBridge", 
                                "Style for layer %s exported to %s") % (layer.name(), self.folder), 
                                'GeoCat Bridge', level=Qgis.Info)            
    
    def publishStyle(self, layer):
        self.createStyleFolder(layer)
        
    def publishLayer(self, layer, fields=None):
        self.publishStyle(layer)
        layerFilename = layer.name() + ".shp"
        layerPath = os.path.join(self.folder, layerFilename)         
        exportLayer(layer, fields, toShapefile=True, path=layerPath, force=True)

    def testConnection(self):
        return True

    def setupForProject(self):
        pass

    def prepareForPublishing(self):
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

    def publishLayerMetadata(self, layer, wms):
        self.geonetworkServer().publishLayerMetadata(layer, wms)

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
    
    def setTokenInHeader(self):
        if self.token is None:
            self.getToken()
        self.session.headers.update({"X-XSRF-TOKEN" : self.token}) 

    def request(self, url, method, data=None, headers={}):
        QgsMessageLog.logMessage(QCoreApplication.translate("GeocatBridge", "Making '%s' request to '%s'") % (method, url), 'GeoCat Bridge', level=Qgis.Info)
        self.setTokenInHeader()
        method = getatQCoreApplication.translate("GeocatBridge", self.session, method.lower())
        resp = method(url, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    def getToken(self):                
        xmlInfoUrl = self.url + '/info.xml'
        self.session.post(xmlInfoUrl)
        self.token = self.session.cookies.get('XSRF-TOKEN')
        self.session.headers.update({"X-XSRF-TOKEN" : self.token})

class GeonetworkServer():

    PROFILE_DEFAULT = 0
    PROFILE_INSPIRE = 1
    PROFILE_DUTCH = 2

    XSLTFILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "qgis-to-iso19139.xsl")

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

    def publishLayerMetadata(self, layer, wms):
        uuid = uuidForLayer(layer)
        filename = tempFilenameInTempFolder(layer.name() + ".qmd")
        layer.saveNamedMetadata(filename)
        thumbnail = self.saveLayerThumbnail(layer)
        transformedFilename = self.transformMetadata(filename, uuid, wms)
        mefFilename = tempFilenameInTempFolder(uuid + ".mef")
        meftools.createMef(uuid, transformedFilename, mefFilename, thumbnail)        
        self._catalog.publish_metadata(mefFilename)

    def testConnection(self):
        try:
            self._catalog.me()
            return True
        except:
            return False

    def saveLayerThumbnail(self, layer):
        filename = tempFilenameInTempFolder("thumbnail.png")
        img = QImage(QSize(800,800), QImage.Format_A2BGR30_Premultiplied)
        color = QColor(255,255,255,255)
        img.fill(color.rgba())
        p = QPainter()
        p.begin(img)
        p.setRenderHint(QPainter.Antialiasing)
        ms = QgsMapSettings()
        ms.setBackgroundColor(color)        
        ms.setLayers([layer])
        ms.setExtent(layer.extent())
        ms.setOutputSize(img.size())
        render = QgsMapRendererCustomPainterJob(ms, p)
        render.start()
        render.waitForFinished()
        p.end()
        img.save(filename)
        return filename

    def transformMetadata(self, filename, uuid, wms):
        def _ns(n):
            return '{http://www.isotc211.org/2005/gmd}' + n
        isoFilename = tempFilenameInTempFolder("metadata.xml")
        dom = ET.parse(filename)
        xslt = ET.parse(self.XSLTFILENAME)
        transform = ET.XSLT(xslt)
        newdom = transform(dom)
        for ident in newdom.iter(_ns('fileIdentifier')):
            ident[0].text = uuid
        if wms is not None:
            for root in newdom.iter(_ns('MD_Distribution')):
                trans = ET.SubElement(root, _ns('transferOptions'))
                dtrans = ET.SubElement(trans, _ns('MD_DigitalTransferOptions'))
                online = ET.SubElement(dtrans, _ns('onLine'))
                cionline = ET.SubElement(online, _ns('CI_OnlineResource'))
                linkage = ET.SubElement(cionline, _ns('linkage'))
                url = ET.SubElement(linkage, _ns('URL'))
                url.text = wms
                protocol = ET.SubElement(cionline, _ns('protocol'))
                cs = ET.SubElement(protocol, '{http://www.isotc211.org/2005/gco}CharacterString')
                cs.text = "OGC:WMS"
        for root in newdom.iter(_ns('MD_DataIdentification')):
            overview = ET.SubElement(root, _ns('graphicOverview'))
            browseGraphic = ET.SubElement(overview, _ns('MD_BrowseGraphic'))
            file = ET.SubElement(browseGraphic, _ns('fileName'))
            cs = ET.SubElement(file, '{http://www.isotc211.org/2005/gco}CharacterString')
            thumbnailUrl = "%s/srv/api/records/%s/attachments/thumbnail.png" % (self.url, uuid)
            cs.text = thumbnailUrl
        s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
        with open(isoFilename, "w", encoding="utf8") as f:
            f.write(s)
        
        return isoFilename


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
            raise Exception(QCoreApplication.translate("GeocatBridge", 'Error importing to PostGIS: {0}').format(exporter.errorMessage()))

        features = layer.getFeatures()
        for f in features:
            if not exporter.addFeature(f, QgsFeatureSink.FastInsert):
                raise Exception(QCoreApplication.translate("GeocatBridge", 'Error importing to PostGIS: {0}').format(exporter.errorMessage()))
        exporter.flushBuffer()
        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception(QCoreApplication.translate("GeocatBridge", 'Error importing to PostGIS: {0}').format(exporter.errorMessage()))

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