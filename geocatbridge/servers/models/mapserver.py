import os
import shutil
from typing import List

from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsWkbTypes
)

from geocatbridge.publish import export
from geocatbridge.publish.ftpupload import uploadFolder
from geocatbridge.publish.style import convertDictToMapfile, layerStyleAsMapfileFolder
from geocatbridge.servers.bases import DataCatalogServerBase
from geocatbridge.servers.views.mapserver import MapServerWidget
from geocatbridge.utils import files
from geocatbridge.utils.layers import BridgeLayer, layerById


class MapserverServer(DataCatalogServerBase):
    useLocalFolder: bool = True
    folder: str = ""
    host: str = ""
    port: int = 80
    servicesPath: str = ""
    projFolder: str = "/usr/share/proj"

    def __init__(self, name, authid="", url="", **options):
        """
        Creates a new MapServer model instance.

        :param name:                    Descriptive server name (given by the user)
        :param authid:                  QGIS Authentication ID (optional)
        :param url:                     MapServer FTP URL
        :param useLocalFolder:          Set to True if publication must take place to a local folder
        :param folder:                  Local folder path
        :param host:                    MapServer host name
        :param port:                    MapServer port (default = 80)
        :param servicesPath:            Relative path to map services
        :param projFolder:              Local path on server to projections folder
        """
        super().__init__(name, authid, url, **options)
        self._metadataLinks = {}
        self._folder = files.tempFolder()

    @classmethod
    def getWidgetClass(cls) -> type:
        return MapServerWidget

    @classmethod
    def getLabel(cls) -> str:
        return 'MapServer'

    def vectorLayersAsShp(self) -> bool:
        # MapServer exports should always be a Shapefile
        return True

    def publishStyle(self, layer: BridgeLayer):
        pass  # TODO?

    def publishLayer(self, layer: BridgeLayer, fields: List[str] = None, exporter=None):
        if layer.is_vector:
            shp_path = os.path.join(self.dataFolder(), f"{layer.file_slug}{export.EXT_SHAPEFILE}")
            export.exportVector(layer, fields, force_shp=True, target_path=shp_path)
        elif layer.type() == layer.RasterLayer:
            tif_path = os.path.join(self.dataFolder(), f"{layer.file_slug}{export.EXT_GEOTIFF}")
            export.exportRaster(layer, target_path=tif_path)

    def uploadFolder(self, folder):
        username, password = self.getCredentials()
        uploadFolder(folder, self.host, self.port, self.folder, username, password)

    def testConnection(self, errors):
        # TODO: MapServer connections are not tested
        return True

    def prepareForPublishing(self, only_symbology):
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

    def closePublishing(self, layer_ids):

        def _quote(t):
            return '"%s"' % t

        name = self.projectName
        extent = QgsRectangle()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        layers = [layerById(lyr_id) for lyr_id in layer_ids]
        for layer in layers:
            trans = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            layer_extent = trans.transform(layer.extent())
            extent.combineExtentWith(layer_extent)

        extent_str = " ".join([str(v) for v in [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]])  # noqa

        for layer in layers:
            add = {}
            layer_filename = layer.file_slug + ".shp"
            add["DATA"] = _quote(layer_filename)
            if layer.is_raster:
                layer_type = "raster"
            elif layer.is_vector:
                layer_type = QgsWkbTypes.geometryDisplayString(layer.geometryType())
            else:
                self.logWarning(f"Skipped unsupported layer '{layer.name()}'")
                continue
            add["TYPE"] = layer_type

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
            md_link = self._metadataLinks.get(layer.web_slug)
            if md_link:
                metadata["ows_metadataurl_href"] = _quote(md_link)
                metadata["ows_metadataurl_type"] = _quote("TC211")
                metadata["ows_metadataurl_format"] = _quote("XML")

            add["METADATA"] = metadata
            warnings = layerStyleAsMapfileFolder(layer, self.mapsFolder(), add)
            for w in warnings:
                self.logWarning(w)

        mapfile_obj = {
            "MAP": {
                "NAME": _quote(name),
                "STATUS": 'ON',
                "CONFIG": f'"PROJ_LIB" "{self.projFolder}"',
                "EXTENT": extent_str,
                "PROJECTION": {
                    'AUTO': ''
                },
                "SYMBOLSET": '"symbols.txt"',
                "MAXSIZE": 8000,
                "SHAPEPATH": '"../data"',
                "SIZE": "700 700",
                "UNITS": "METERS",
                "WEB": {
                    "IMAGEPATH": '"../data/bridge/webdav/images"',
                    "IMAGEURL": '"http://localhost/images"',
                    "METADATA": {
                        '"wms_title"': _quote(name),
                        '"wms_onlineresource"': _quote(f"{self.getWmsUrl()}&layers={','.join(l.web_slug for l in layers)}"),  # noqa
                        '"ows_enable_request"': '"*"',
                        '"ows_srs"': '"EPSG:4326"',
                        '"wms_feature_info_mime_type"': '"text/html"'
                    }
                },
                "OUTPUTFORMAT": {
                    "DRIVER": '"AGG/PNG"',
                    "EXTENSION": '"png"',
                    "IMAGEMODE": '"RGB"',
                    "MIMETYPE": '"image/png"'
                },
                "SCALEBAR": {
                    "ALIGN": "CENTER",
                    "OUTLINECOLOR": "0 0 0"
                },
                "LAYERS": [{"INCLUDE": f'"{layer.web_slug}.txt"'} for layer in layers],
                "SYMBOLS": [{"INCLUDE": f'"{layer.web_slug}_symbols.txt"'} for layer in layers]
            }
        }

        mapfile_str = convertDictToMapfile(mapfile_obj)
        mapfile_path = os.path.join(self.mapsFolder(), name + ".map")
        with open(mapfile_path, "w") as f:
            f.write(mapfile_str)

        src = files.getResourcePath(files.Path("mapserver") / "symbols.txt")
        dst = self.mapsFolder()
        shutil.copy2(src, dst)

        if not self.useLocalFolder:
            self.uploadFolder(dst)

    def layerNames(self):
        return {}  # TODO

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

    def createGroups(self, layer_ids):
        pass
