import requests

from .serverbase import ServerBase

class GeocatLiveServer(ServerBase): 

    BASE_URL = "https://artemis.geocat.net/geocat-live/api/1.0/order/"

    def __init__(self, name, userid="", geoserverAuthid="", geonetworkAuthid="", profile=0):
        self.url = "GeocatLive server"
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
        response = requests.get(url).json()
        for serv in response["services"]:
            if serv["application"] == "geoserver":
                self._geoserverUrl = serv["url"] + "/rest"
            if serv["application"] == "geonetwork":
                self._geonetworkUrl = serv["url"]

    def geoserverServer(self):
        if self._geoserverUrl is None:
            self._getUrls()
        if self._geoserverServer is None:            
            self._geoserverServer = GeoserverServer("GeoServer", self._geoserverUrl, 
                                                self.geoserverAuthid, workspace="geocatlive")
        return self._geoserverServer

    def geonetworkServer(self):
        if self._geonetworkUrl is None:
            self._getUrls()
        if self._geonetworkServer is None:
            self._geonetworkServer = GeonetworkServer("GeoNetwork", self._geonetworkUrl, self.geonetworkAuthid)
        return self._geonetworkServer

    def setupForProject(self):
        pass
    
    def prepareForPublishing(self, onlySymbology):
        pass

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

    def createGroup(self, groupname, layernames):
        return self.geoserverServer().createGroup(groupname, layernames)

    def styleExists(self, name):
        return self.geoserverServer().styleExists(name)

    def deleteStyle(self, name):
        return self.geoserverServer().deleteStyle(name)

    def layerExists(self, name):
        return self.geoserverServer().layerExists(name)

    def deleteLayer(self, name):
        self.geoserverServer().deleteLayer(name)
    
    def openWms(self, names, bbox, srs):
        self.geoserverServer().openWms(names, bbox, srs)

    def layerWms(self, names, bbox, srs):
        return self.geoserverServer().layerWms(names, bbox, srs)
        
    def setLayerMetadataLink(self, name, url):
        return self.geoserverServer().setLayerMetadataLink(name, url)

    def publishLayerMetadata(self, layer, wms):
        return self.geonetworkServer().publishLayerMetadata(layer, wms)

    def metadataExists(self, uuid):
        return self.geonetworkServer().metadataExists(uuid)

    def getMetadata(self, uuid):
        return self.geonetworkServer().getMetadata(uuid)

    def deleteMetadata(self, uuid):
        return self.geonetworkServer().deleteMetadata(uuid)

    def metadataUrl(self, uuid):
        return self.geonetworkServer().metadataUrl(uuid)