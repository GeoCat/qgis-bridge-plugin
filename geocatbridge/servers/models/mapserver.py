import os
import shutil

from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes
)

from bridgestyle.mapserver.fromgeostyler import convertDictToMapfile
from bridgestyle.qgis import layerStyleAsMapfileFolder
from geocatbridge.publish.exporter import exportLayer
from geocatbridge.publish.ftpupload import uploadFolder
from geocatbridge.servers.bases import DataCatalogServerBase
from geocatbridge.servers.views.mapserver import MapServerWidget
from geocatbridge.utils import files


class MapserverServer(DataCatalogServerBase):

    def __init__(self, name, url="", useLocalFolder=True, folder="", authid="", host="", port=80,
                 servicesPath="", projFolder=""):
        super().__init__(name, authid, url)
        self.folder = folder
        self.useLocalFolder = useLocalFolder
        self.host = host
        self.port = port
        self.servicesPath = servicesPath
        self.projFolder = projFolder or "/usr/share/proj"  # FTP project folder (not local)
        self._layers = []
        self._metadataLinks = {}
        self._folder = files.tempFolder()

    def getSettings(self) -> dict:
        return {
            'name': self.serverName,
            'url': self.baseUrl,
            'useLocalFolder': self.useLocalFolder,
            'folder': self.folder,
            'authid': self.authId,
            'host': self.host,
            'port': self.port,
            'servicesPath': self.servicesPath,
            'projFolder': self.projFolder
        }

    @classmethod
    def getWidgetClass(cls) -> type:
        return MapServerWidget

    @classmethod
    def getLabel(cls) -> str:
        return 'MapServer'

    def publishStyle(self, layer):
        self._layers.append(layer)

    def publishLayer(self, layer, fields=None):
        layerFilename = layer.name() + ".shp"
        layerPath = os.path.join(self.dataFolder(), layerFilename)
        exportLayer(layer, fields, to_shapefile=True, path=layerPath, force=True, logger=self)

    def uploadFolder(self, folder):
        username, password = self.getCredentials()
        uploadFolder(folder, self.host, self.port, self.folder, username, password)

    def testConnection(self, errors):
        # MapServer connections are not tested
        return True

    def prepareForPublishing(self, only_symbology):
        self._layers = []
        self._metadataLinks = {}
        self._folder = self.folder if self.useLocalFolder else files.tempFolder()

    @property
    def projectName(self):
        filename = QgsProject.instance().fileName()
        if filename:
            name = os.path.splitext(os.path.basename(filename))[0]
        else:
            name = "myMap"
        return name

    def mapsFolder(self):
        path = os.path.join(self._folder, self.projectName, "maps")
        os.makedirs(path, exist_ok=True)
        return path

    def dataFolder(self):
        path = os.path.join(self._folder, self.projectName, "data")
        os.makedirs(path, exist_ok=True)
        return path

    def templatesFolder(self):
        path = os.path.join(self._folder, self.projectName, "templates")
        os.makedirs(path, exist_ok=True)
        return path

    def closePublishing(self):
        name = self.projectName
        extent = QgsRectangle()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        for layer in self._layers:
            trans = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            layerExtent = trans.transform(layer.extent())
            extent.combineExtentWith(layerExtent)

        sExtent = " ".join([str(v) for v in [extent.xMinimum(), extent.yMinimum(),
                                             extent.xMaximum(), extent.yMaximum()]])

        def _quote(t):
            return '"%s"' % t

        for layer in self._layers:
            add = {}
            layerFilename = layer.name() + ".shp"
            add["DATA"] = _quote(layerFilename)
            if isinstance(layer, QgsRasterLayer):
                layerType = "raster"
            elif isinstance(layer, QgsVectorLayer):
                layerType = QgsWkbTypes.geometryDisplayString(layer.geometryType())
            else:
                self.logWarning(f"Skipped unsupported layer '{layer.name()}'")
                continue
            add["TYPE"] = layerType

            bbox = layer.extent()
            if bbox.isEmpty():
                bbox.grow(1)

            metadata = {
                "wms_abstract": _quote(layer.metadata().abstract()),
                "wms_title": _quote(layer.name()),
                "ows_srs": _quote("EPSG:4326 EPSG:3857 " + layer.crs().authid()),
                "wms_extent": _quote(" ".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(),
                                                                bbox.xMaximum(), bbox.yMaximum()]]))
            }
            if layer.name() in self._metadataLinks:
                metadata["ows_metadataurl_href"] = _quote(self._metadataLinks[layer.name()])
                metadata["ows_metadataurl_type"] = _quote("TC211")
                metadata["ows_metadataurl_format"] = _quote("XML")

            add["METADATA"] = metadata
            warnings = layerStyleAsMapfileFolder(layer, self.mapsFolder(), add)
            for w in warnings:
                self.logWarning(w)

        web = {"IMAGEPATH": '"../data/bridge/webdav/images"',
               "IMAGEURL": '"http://localhost/images"',
               "METADATA": {
                   '"wms_title"': _quote(name),
                   '"wms_onlineresource"': _quote(f"{self.getWmsUrl()}&layers={layer.name()}"),
                   '"ows_enable_request"': '"*"',
                   '"ows_srs"': '"EPSG:4326"',
                   '"wms_feature_info_mime_type"': '"text/html"'
               }}
        mapElement = {"NAME": _quote(name), "STATUS": 'ON', "CONFIG": '"PROJ_LIB" "%s"' % self.projFolder,
                      "EXTENT": sExtent, "PROJECTION": {'AUTO': ''}, "SYMBOLSET": '"symbols.txt"', "MAXSIZE": 8000,
                      "SHAPEPATH": '"../data"', "SIZE": "700 700", "UNITS": "METERS", "WEB": web,
                      "OUTPUTFORMAT": {"DRIVER": '"AGG/PNG"',
                                       "EXTENSION": '"png"',
                                       "IMAGEMODE": '"RGB"',
                                       "MIMETYPE": '"image/png"'}, "SCALEBAR": {"ALIGN": "CENTER",
                                                                                "OUTLINECOLOR": "0 0 0"},
                      "LAYERS": [{"INCLUDE": '"%s.txt"' % layer.name()} for layer in self._layers],
                      "SYMBOLS": [{"INCLUDE": '"%s_symbols.txt"' % layer.name()} for layer in self._layers]}
        mapfile = {"MAP": mapElement}

        s = convertDictToMapfile(mapfile)

        mapfilePath = os.path.join(self.mapsFolder(), name + ".map")
        with open(mapfilePath, "w") as f:
            f.write(s)

        src = files.getResourcePath(files.Path("mapserver") / "symbols.txt")
        dst = self.mapsFolder()
        shutil.copy2(src, dst)

        if not self.useLocalFolder:
            self.uploadFolder(dst)

    def layerExists(self, name: str):
        return

    def styleExists(self, name: str):
        return

    def deleteStyle(self, name):
        return False

    def deleteLayer(self, name):
        return False

    def openPreview(self, names, bbox, srs):
        pass

    def getWmsUrl(self):
        project = self.projectName
        return "%s?map=%s/maps/%s.map&service=WMS&version=1.1.0&request=GetCapabilities" % (
            self.baseUrl, project, project)

    def getWfsUrl(self):
        project = self.projectName
        return "%s?map=%s/maps/%s.map&service=WFS&version=2.0.0&request=GetCapabilities" % (
            self.baseUrl, project, project)

    def setLayerMetadataLink(self, name, url):
        self._metadataLinks[name] = url

    def createGroups(self, groups, qgis_layers):
        pass
