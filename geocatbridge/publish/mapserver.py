import os
from .ftpupload import uploadFolder
from .serverbase import ServerBase
from bridgestyle.qgis import layerStyleAsMapfileFolder
from bridgestyle.mapserver.fromgeostyler import convertDictToMapfile
from .exporter import exportLayer

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProject, QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform

class MapserverServer(ServerBase): 

    def __init__(self, name, url="", useLocalFolder=True, folder="", authid="", host="", port=1, servicesPath=""):
        self.name = name
        self.folder = folder
        self.useLocalFolder = useLocalFolder
        self.authid = authid
        self.host = host
        self.port = port
        self.url = url
        self.servicesPath = servicesPath

        self._isMetadataCatalog = False
        self._isDataCatalog = True

    def publishStyle(self, layer, upload = True):        
        layerFilename = layer.name() + ".shp"        
        warnings = layerStyleAsMapfileFolder(layer, layerFilename, self._folder)        
        for w in warnings:
            self.logWarning(w)
        self.logInfo(QCoreApplication.translate("GeocatBridge", 
                                "Style for layer %s exported to %s") % (layer.name(), self._folder))
                
    def publishLayer(self, layer, fields=None):
        self._layers.append(layer)
        self.publishStyle(layer, False)
        layerFilename = layer.name() + ".shp"
        layerFolder = os.path.join(self._folder, "data")
        layerPath = os.path.join(layerFolder, layerFilename)
        os.makedirs(layerFolder, exist_ok=True)
        exportLayer(layer, fields, toShapefile=True, path=layerPath, force=True, log=self)

    def uploadFolder(self, folder):
        username, password = getCredentials()
        uploadFolder(folder, self.host, self.port, self.folder, username, password)

    def testConnection(self):
        return True

    def setupForProject(self):
        pass

    def prepareForPublishing(self, onlySymbology):
        self._layers = []
        self._folder = self.folder if self.useLocalFolder else tempFolder()

    def closePublishing(self):
        filename = QgsProject.instance().fileName()
        if filename:
            name = os.path.splitext(os.path.basename(filename))[0]
        else:
            name = "myMap"
        
        extent = QgsRectangle()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        for layer in self._layers:
            trans = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            layerExtent = trans.transform(layer.extent())
            extent.combineExtentWith(layerExtent)

        sExtent = " ".join([str(v) for v in [extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()]])

        def _quote(t):
            return '"%s"' % t

        web = {"IMAGEPATH": '"/data/bridge/webdav/images"',
                "IMAGEURL": '"http://localhost/images"',
                "METADATA": {
                            '"wms_title"': _quote(name),
                            '"wms_onlineresource"': _quote("%s?map=../maps/%s.map" % (self.url, name)),
                            '"ows_enable_request"': '"*"',                          
                            '"ows_srs"': '"EPSG:4326"',
                            '"wms_feature_info_mime_type"': '"text/html"'

                }}
        mapElement = {"NAME": _quote(name),
                "STATUS": '"ON"',
                "CONFIG": '"PROJ_LIB" "/usr/share/proj"',
                "EXTENT": sExtent,
                "PROJECTION": '"init=epsg:4326"',
                "MAXSIZE": 8000,
                "SHAPEPATH": '"./data"',
                "SIZE": "700 700",
                "UNITS": "METERS",
                "WEB": web,
                "OUTPUTFORMAT": {"DRIVER": '"AGG/PNG"',
                                "EXTENSION": '"png"',
                                "IMAGEMODE": '"RGB"',
                                "MIMETYPE": 'image/png"'},
                "SCALEBAR": {"ALIGN": "CENTER",
                                "OUTLINECOLOR": "0 0 0"}
                }
        mapElement["LAYERS"] = [{"INCLUDE":'"%s.txt"' % layer.name() for layer in self._layers}]
        mapElement["SYMBOLS"] = [{"INCLUDE": '"%s_symbols.txt"' % layer.name() for layer in self._layers}]
        mapfile = {"SYMBOLSET": '"symbols.txt"',
                    "MAP": mapElement}
        
        s = convertDictToMapfile(mapfile)

        mapfilePath = os.path.join(self._folder, name + ".map")
        with open(mapfilePath, "w") as f:
            f.write(s)

        if not self.useLocalFolder:
            self.uploadFolder(folder)

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
