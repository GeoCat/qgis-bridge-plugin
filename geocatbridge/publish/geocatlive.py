import requests

from ..utils.gui import execute
from .serverbase import ServerBase
from .geoserver import GeoserverServer
from .geonetwork import GeonetworkServer
from ..utils.services import addServicesForGeodataServer

class GeocatLiveServer(ServerBase): 

    BASE_URL = "https://live-services.geocat.net/geocat-live/api/1.0/order"

    def __init__(self, name, userid="", geoserverAuthid="", geonetworkAuthid="", profile=0):
        super().__init__()
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

    @property
    def url(self):
        return "GeocatLive server"
        
    def _getUrls(self):
        def f():
            url = "%s/%s" % (self.BASE_URL, self.userid)
            response = requests.get(url).json()
            for serv in response["services"]:
                if serv["application"] == "geoserver":
                    self._geoserverUrl = serv["url"] + "/rest"
                if serv["application"] == "geonetwork":
                    self._geonetworkUrl = serv["url"]
        execute(f)

    def geoserverServer(self):
        if self._geoserverUrl is None:
            try:
                self._getUrls()
            except:
                self._geoserverUrl = ""
        if self._geoserverServer is None:            
            self._geoserverServer = GeoserverServer("GeoServer", self._geoserverUrl, 
                                                    self.geoserverAuthid)
        return self._geoserverServer

    def geonetworkServer(self):
        if self._geonetworkUrl is None:
            try:
                self._getUrls()
            except:
                self._geonetworkUrl = ""
        if self._geonetworkServer is None:
            self._geonetworkServer = GeonetworkServer("GeoNetwork", self._geonetworkUrl, 
                                                    self.geonetworkAuthid)
            self.addOGCServers()
        return self._geonetworkServer

    def setupForProject(self):
        self.geoserverServer().setupForProject()
    
    def prepareForPublishing(self, onlySymbology):
        self.geoserverServer().prepareForPublishing(onlySymbology)

    def closePublishing(self):
        self.geoserverServer().closePublishing()

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

    def unpublishData(self, layer):
        return self.geoserverServer().unpublishData(layer)

    def createGroups(self, groups):
        return self.geoserverServer().createGroups(groups)

    def styleExists(self, name):
        return self.geoserverServer().styleExists(name)

    def deleteStyle(self, name):
        return self.geoserverServer().deleteStyle(name)

    def layerExists(self, name):
        return self.geoserverServer().layerExists(name)

    def deleteLayer(self, name):
        self.geoserverServer().deleteLayer(name)
    
    def openPreview(self, names, bbox, srs):
        self.geoserverServer().openPreview(names, bbox, srs)    

    def fullLayerName(self, layerName):
        return self.geoserverServer().fullLayerName(layerName)

    def layerWfsUrl(self):
        return self.geoserverServer().layerWfsUrl()

    def layerWmsUrl(self, name):
        return self.geoserverServer().layerWmsUrl(name)
        
    def setLayerMetadataLink(self, name, url):
        return self.geoserverServer().setLayerMetadataLink(name, url)

    def publishLayerMetadata(self, layer, wms, wfs, layerName):
        return self.geonetworkServer().publishLayerMetadata(layer, wms, wfs, layerName)

    def metadataExists(self, uuid):
        return self.geonetworkServer().metadataExists(uuid)

    def openMetadata(self, uuid):
        self.geonetworkServer().openMetadata(uuid)

    def getMetadata(self, uuid):
        return self.geonetworkServer().getMetadata(uuid)

    def deleteMetadata(self, uuid):
        return self.geonetworkServer().deleteMetadata(uuid)

    def metadataUrl(self, uuid):
        return self.geonetworkServer().metadataUrl(uuid)

    def addOGCServers(self):
        if self._geoserverUrl is None:
            try:
                self._getUrls()
            except:
                return
        baseurl = "/".join(self._geoserverUrl.split("/")[:-1])
        addServicesForGeodataServer("GeoCat Live Geoserver - " + self.userid, baseurl, self.geoserverAuthid)

    def validateGeodataBeforePublication(self, errors, toPublish):
        return self.geoserverServer().validateGeodataBeforePublication(errors, toPublish)

    def validateMetadataBeforePublication(self, errors):    
        return self.geonetworkServer().validateMetadataBeforePublication(errors)