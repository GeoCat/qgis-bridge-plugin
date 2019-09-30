import os
from .ftpupload import uploadFolder
from .serverbase import ServerBase
from bridgestyle.qgis import layerStyleAsMapfileFolder
from .exporter import exportLayer

from qgis.PyQt.QtCore import QCoreApplication

class MapserverServer(ServerBase): 

    def __init__(self, name, useLocalFolder=True, folder="", authid="", host="", port=1):
        self.name = name
        self.folder = folder
        self.useLocalFolder = useLocalFolder
        self.authid = authid
        self.host = host
        self.port = port
        self.url = ""

        self._isMetadataCatalog = False
        self._isDataCatalog = True

    def publishStyle(self, layer, upload = True):
        folder = self.folder if self.useLocalFolder else tempFolder()
        layerFilename = layer.name() + ".shp"        
        warnings = layerStyleAsMapfileFolder(layer, layerFilename, folder)        
        for w in warnings:
            self.logWarning(w)
        self.logInfo(QCoreApplication.translate("GeocatBridge", 
                                "Style for layer %s exported to %s") % (layer.name(), folder))
        if not self.useLocalFolder and upload:
            self.uploadFolder(folder)
        return folder
        
    def publishLayer(self, layer, fields=None):
        folder = self.publishStyle(layer, False)
        layerFilename = layer.name() + ".shp"
        layerPath = os.path.join(folder, layerFilename)         
        exportLayer(layer, fields, toShapefile=True, path=layerPath, force=True, log=self)
        if not self.useLocalFolder:
            self.uploadFolder(folder)

    def uploadFolder(self, folder):
        username, password = getCredentials()
        uploadFolder(folder, self.host, self.port, self.folder, username, password)

    def testConnection(self):
        return True

    def setupForProject(self):
        pass

    def prepareForPublishing(self, onlySymbology):
        pass

    def styleExists(self, name):
        return False        

    def deleteStyle(self, name):
        return False

    def layerExists(self, name):
        return False

    def deleteLayer(self, name):
        return False
    
    def openWms(self, names, bbox, srs):
        pass

    def layerWms(self, names, bbox, srs):
        return ""
        
    def setLayerMetadataLink(self, name, url):
        pass

    def createGroups(self, groups):
        pass
