import os
import shutil
import json
import webbrowser
from zipfile import ZipFile
import sqlite3
import secrets

from requests.exceptions import ConnectionError, HTTPError

from qgis.core import QgsProject, QgsDataSourceUri
from qgis.PyQt.QtCore import QCoreApplication, QByteArray, QBuffer, QIODevice
from qgis.PyQt.QtWidgets import QMessageBox

from bridgestyle import mapboxgl
from bridgestyle.qgis import saveLayerStyleAsZippedSld, layerStylesAsMapboxFolder

from .exporter import exportLayer
from .serverbase import ServerBase
from ..utils import layers as layerUtils
from ..utils.files import tempFilenameInTempFolder, tempFolderInTempFolder
from ..utils.services import addServicesForGeodataServer


class GeoserverServer(ServerBase):
    FILE_BASED = 0
    POSTGIS_MANAGED_BY_BRIDGE = 1
    POSTGIS_MANAGED_BY_GEOSERVER = 2

    def __init__(
        self,
        name,
        url="",
        authid="",
        storage=0,
        postgisdb=None,
        useOriginalDataSource=False,
        useVectorTiles=False
    ):
        super().__init__()
        self.name = name

        self.url = url.rstrip("/")
        if not self.url.endswith("/rest"):
            self.url += "/rest"

        self.authid = authid
        self.storage = storage
        self.postgisdb = postgisdb
        self.useOriginalDataSource = useOriginalDataSource
        self.useVectorTiles = useVectorTiles
        self._isMetadataCatalog = False
        self._isDataCatalog = True
        self._layersCache = {}

    @property
    def _workspace(self):
        """ Returns the QGIS project name if the file has been saved. """
        path = QgsProject.instance().absoluteFilePath()
        if path:
            # Return project name from file path with spaces replaced by underscores
            return (os.path.splitext(os.path.basename(path))[0]).replace(' ', '_')
        return ""

    def prepareForPublishing(self, onlySymbology):
        if not onlySymbology:
            self.clearWorkspace()
        self._ensureWorkspaceExists()
        self._uploadedDatasets = {}
        self._exportedLayers = {}
        self._postgisDatastoreExists = False
        self._publishedLayers = set()

    def closePublishing(self):
        if not self.useVectorTiles:
            return
        folder = tempFolderInTempFolder()
        warnings = layerStylesAsMapboxFolder(self._publishedLayers, folder)
        for w in warnings:
            self.logWarning(w)
        self._editMapboxFiles(folder)
        self.publishMapboxGLStyle(folder)
        self._publishOpenLayersPreview(folder)

    def _publishOpenLayersPreview(self, folder):
        styleFilename = os.path.join(folder, "style.mapbox")
        with open(styleFilename) as f:
            style = f.read()
        template = "var style = %s;\nvar map = olms.apply('map', style);" % style

        jsFilename = os.path.join(folder, "mapbox.js")
        with open(jsFilename, "w") as f:
            f.write(template)
        src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "openlayers", "index.html")
        dst = os.path.join(folder, "index.html")
        shutil.copyfile(src, dst)
        self.uploadResource("%s/index.html" % self._workspace, src)
        self.uploadResource("%s/mapbox.js" % self._workspace, jsFilename)

    def uploadResource(self, path, file):
        with open(file) as f:
            content = f.read()
        url = "%s/resource/%s" % (self.url, path)
        self.request(url, content, "put")

    def _editMapboxFiles(self, folder):
        filename = os.path.join(folder, "style.mapbox")
        with open(filename) as f:
            mapbox = json.load(f)
        sources = mapbox["sources"]
        for name in sources.keys():
            url = ("%s/gwc/service/wmts?REQUEST=GetTile&SERVICE=WMTS"
                  "&VERSION=1.0.0&LAYER=%s:%s&STYLE=&TILEMATRIX=EPSG:900913:{z}"
                  "&TILEMATRIXSET=EPSG:900913&FORMAT=application/vnd.mapbox-vector-tile"
                  "&TILECOL={x}&TILEROW={y}" % (self.baseUrl(), self._workspace, name))
            sourcedef = {
                  "type": "vector",
                  "tiles": [url],
                  "minZoom": 0,
                  "maxZoom": 14
                }
            sources[name] = sourcedef
        with open(filename, "w") as f:
            json.dump(mapbox, f)

    def publishMapboxGLStyle(self, folder):
        name = "mb_" + self._workspace
        filename = os.path.join(folder, "style.mapbox")
        self._publishStyle(name, filename)

    def publishStyle(self, layer):
        lyr_title, lyr_name = layerUtils.getLayerTitleAndName(layer)
        export_layer = layerUtils.getExportableLayer(layer, lyr_name)
        styleFilename = tempFilenameInTempFolder(lyr_name + ".zip")
        warnings = saveLayerStyleAsZippedSld(export_layer, styleFilename)
        for w in warnings:
            self.logWarning(w)
        self.logInfo(QCoreApplication.translate("GeocatBridge", "Style for layer '%s' exported as ZIP file to '%s'")
                     % (lyr_title, styleFilename))
        self._publishStyle(lyr_name, styleFilename)
        self._publishedLayers.add(layer)
        return styleFilename

    def publishLayer(self, layer, fields=None):
        lyr_title, safe_name = layerUtils.getLayerTitleAndName(layer)
        if layer.type() == layer.VectorLayer:
            if layer.featureCount() == 0:
                self.logError("Layer '%s' contains zero features and cannot be published" % lyr_title)
                return

            if layer.dataProvider().name() == "postgres" and self.useOriginalDataSource:
                from .postgis import PostgisServer
                uri = QgsDataSourceUri(layer.source())
                db = PostgisServer("temp", uri.authConfigId(), uri.host(), uri.port(), uri.schema(), uri.database())
                self._publishVectorLayerFromPostgis(layer, db)
            elif self.storage in [self.FILE_BASED, self.POSTGIS_MANAGED_BY_GEOSERVER]:
                src_path, src_name, src_ext = layerUtils.getLayerSourceInfo(layer)
                filename = self._exportedLayers.get(src_path)
                if not filename:
                    if self.storage == self.POSTGIS_MANAGED_BY_GEOSERVER:
                        shp_name = exportLayer(layer, fields, toShapefile=True, force=True, log=self)
                        basename = os.path.splitext(shp_name)[0]
                        filename = basename + ".zip"
                        with ZipFile(filename, 'w') as z:
                            for ext in (".shp", ".shx", ".prj", ".dbf"):
                                filetozip = basename + ext
                                z.write(filetozip, arcname=os.path.basename(filetozip))
                    else:
                        filename = exportLayer(layer, fields, log=self)
                self._exportedLayers[src_path] = filename
                if self.storage == self.FILE_BASED:
                    self._publishVectorLayerFromFile(layer, filename)
                else:
                    self._publishVectorLayerFromFileToPostgis(layer, filename)
            elif self.storage == self.POSTGIS_MANAGED_BY_BRIDGE:
                try:
                    from .servers import allServers
                    db = allServers()[self.postgisdb]
                except KeyError:
                    raise Exception(
                        QCoreApplication.translate("GeocatBridge", "Cannot find the selected PostGIS database"))
                db.importLayer(layer, fields)
                self._publishVectorLayerFromPostgis(layer, db)
        elif layer.type() == layer.RasterLayer:
            if layer.source() not in self._exportedLayers:
                path = exportLayer(layer, fields, log=self)
                self._exportedLayers[layer.source()] = path
            filename = self._exportedLayers[layer.source()]
            self._publishRasterLayer(filename, safe_name)
        self._clearCache()

    def _getPostgisDatastores(self, ds_list_url=None):
        """
        Finds all PostGIS datastores for a certain workspace (typically only 1).
        If `ds_list_url` is not specified, the first PostGIS datastore for the current workspace is returned.
        Otherwise, `ds__list_url` should be the datastores REST endpoint to a specific workspace.

        :param ds_list_url: REST URL that returns a list of datastores for a specific workspace.
        :returns:           A generator with PostGIS datastore names.
        """

        if not ds_list_url:
            ds_list_url = "%s/workspaces/%s/datastores.json" % (self.url, self._workspace)

        res = self.request(ds_list_url).json().get("dataStores", {})
        if not res:
            # There aren't any dataStores for the given workspace
            return

        for ds_url in (s.get("href") for s in res.get("dataStore", [])):
            ds = self.request(ds_url).json().get("dataStore", {})
            ds_name, enabled, params = ds.get("name"), ds.get("enabled"), ds.get("connectionParameters", {})
            # Only yield dataStore if it is enabled and the "dbtype" parameter equals "postgis"
            # Using the "type" property does not work in all cases (e.g. for JNDI connection pools or NG)
            entries = {e["@key"]: e["$"] for e in params.get("entry", [])}
            if enabled and entries.get("dbtype").startswith("postgis"):
                yield ds_name

    def createPostgisDatastore(self):
        """
        Creates a new datastore based on the selected one in the Server widget if the workspace is created from scratch.

        :returns:   The existing or created PostGIS datastore name.
        """

        # Check if current workspaces has a PostGIS datastore (use first)
        for ds_name in self._getPostgisDatastores():
            return ds_name

        # Get workspace and datastore name from selected template in Server widget
        ws, ds_name = self.postgisdb.split(":")

        # Retrieve settings from datastore template
        url = "%s/workspaces/%s/datastores/%s.json" % (self.url, ws, ds_name)
        datastore = self.request(url).json()
        # Change datastore name to match workspace name
        datastore["dataStore"]["name"] = self._workspace
        # Change workspace settings to match the one for the current project
        datastore["dataStore"]["workspace"] = {
          "name": self._workspace,
          "href": "%s/workspaces/%s.json" % (self.url, self._workspace)
        }
        # Fix featureTypes endpoint
        datastore["dataStore"]["featureTypes"] = "%s/workspaces/%s/datastores/%s/featuretypes.json" % (self.url, self._workspace, self._workspace)
        # Fix namespace connection parameter for current workspace
        self._fixNamespaceParam(datastore["dataStore"].get("connectionParameters", {}))
        # Post copy of datastore with modified workspace
        url = "%s/workspaces/%s/datastores.json" % (self.url, self._workspace)
        self.request(url, datastore, "post")
        return self._workspace

    def testConnection(self):
        try:
            url = "%s/about/version" % self.url
            self.request(url)
            return True
        except (ConnectionError, HTTPError):
            return False

    def unpublishData(self, layer):
        self.deleteLayer(layer.name())
        self.deleteStyle(layer.name())

    def baseUrl(self):
        return "/".join(self.url.split("/")[:-1])

    def _publishVectorLayerFromFile(self, layer, filename):
        self.logInfo("Publishing layer from file: %s" % filename)
        title, name = layerUtils.getLayerTitleAndName(layer)
        isDataUploaded = filename in self._uploadedDatasets
        if not isDataUploaded:
            with open(filename, "rb") as f:
                self._deleteDatastore(name)
                url = "%s/workspaces/%s/datastores/%s/file.gpkg?update=overwrite" % (self.url, self._workspace, name)
                self.request(url, f.read(), "put")
            conn = sqlite3.connect(filename)
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM gpkg_geometry_columns")
            tablename = cursor.fetchall()[0][0]
            self._uploadedDatasets[filename] = (name, tablename)

        datasetName, geoserverLayerName = self._uploadedDatasets[filename]
        url = "%s/workspaces/%s/datastores/%s/featuretypes/%s.json" % (
            self.url, self._workspace, datasetName, geoserverLayerName)
        r = self.request(url)
        ft = r.json()
        ft["featureType"]["name"] = name
        ft["featureType"]["title"] = title
        ext = layer.extent()
        ft["featureType"]["nativeBoundingBox"] = {
            "minx": round(ext.xMinimum(), 5),
            "maxx": round(ext.xMaximum(), 5),
            "miny": round(ext.yMinimum(), 5),
            "maxy": round(ext.yMaximum(), 5),
            "srs": layer.crs().authid()
        }
        if isDataUploaded:
            url = "%s/workspaces/%s/datastores/%s/featuretypes" % (self.url, self._workspace, datasetName)
            self.request(url, ft, "post")
        else:
            self.request(url, ft, "put")
        self.logInfo("Successfully created feature type from GeoPackage file '%s'" % filename)
        self._setLayerStyle(name)

    def _publishVectorLayerFromPostgis(self, layer, db):
        name = layer.name()
        username, password = db.getCredentials()

        def _entry(k, v):
            return {"@key": k, "$": v}
        ds = {
            "dataStore": {
                "name": name,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "entry": [
                        _entry("schema", db.schema),
                        _entry("port", str(db.port)),
                        _entry("database", db.database),
                        _entry("passwd", password),
                        _entry("user", username),
                        _entry("host", db.host),
                        _entry("dbtype", "postgis")
                    ]
                }
            }
        }
        dsUrl = "%s/workspaces/%s/datastores/" % (self.url, self._workspace)
        self.request(dsUrl, data=ds, method="post")
        ft = {
            "featureType": {
                "name": name,
                "srs": layer.crs().authid()
            }
        }
        ftUrl = "%s/workspaces/%s/datastores/%s/featuretypes" % (self.url, self._workspace, name)
        self.request(ftUrl, data=ft, method="post")
        self._setLayerStyle(name)

    def _getImportResult(self, importId, taskId):
        """ Get the error message on the import task (if any) and the resulting layer name. """
        task = self.request("%s/imports/%s/tasks/%s" % (self.url, importId, taskId)).json()["task"] or {}
        err_msg = task.get("errorMessage", "")
        if err_msg:
            err_msg = "GeoServer Importer Extension error:\n%s" % err_msg
        return err_msg, task["layer"]["name"]

    def _publishVectorLayerFromFileToPostgis(self, layer, filename):
        self.logInfo("Publishing layer from file `%s`" % filename)
        datastore = self.createPostgisDatastore()
        title, ft_name = layerUtils.getLayerTitleAndName(layer)
        source_name = os.path.splitext(os.path.basename(filename))[0]

        # Create a new import
        body = {
            "import": {
                "targetStore": {
                    "dataStore": {
                        "name": datastore
                    }
                },
                "targetWorkspace": {
                    "workspace": {
                        "name": self._workspace
                    }
                }
            }
        }
        url = "%s/imports.json" % self.url
        ret = self.request(url, body, "post")

        # Create a new task and upload ZIP
        self.logInfo("Uploading layer data...")
        importId = ret.json()["import"]["id"]
        zipname = os.path.basename(filename)
        url = "%s/imports/%s/tasks/%s" % (self.url, importId, zipname)
        with open(filename, "rb") as f:
            ret = self.request(url, method="put", files={zipname: (zipname, f, 'application/octet-stream')})

        # Reassign PostGIS datastore as target (just to be sure)
        taskId = ret.json()["task"]["id"]
        body = {
            "dataStore": {
                "name": datastore
            }
        }
        url = "%s/imports/%s/tasks/%s/target.json" % (self.url, importId, taskId)
        self.request(url, body, "put")
        del ret

        # Start import execution
        self.logInfo("Starting Importer task for layer '%s'..." % ft_name)
        url = "%s/imports/%s" % (self.url, importId)
        self.request(url, method="post")

        # Get the import result (error message and target layer name)
        import_err, tmp_name = self._getImportResult(importId, taskId)
        if import_err:
            self.logError("Failed to publish QGIS layer '%s' as '%s'.\n\n%s" % (title, ft_name, import_err))
            return

        self._uploadedDatasets[filename] = (datastore, source_name)

        # Get the created feature type
        self.logInfo("Checking if feature type creation was successful...")
        url = "%s/workspaces/%s/datastores/%s/featuretypes/%s.json" % (self.url, self._workspace, datastore, tmp_name)
        try:
            ret = self.request(url + "?quietOnNotFound=true")
        except HTTPError as e:
            # Something unexpected happened: failure cannot be retrieved from import task,
            # so the user should check the GeoServer logs to find out what caused it.
            if e.response.status_code == 404:
                self.logError("Failed to publish QGIS layer '%s' as '%s' due to an unknown error.\n"
                              "Please check the GeoServer logs." % (title, ft_name))
                return
            raise

        # Modify the feature type descriptions, but leave the name in tact to avoid db schema mismatches
        self.logInfo("Fixing feature type properties...")
        ft = ret.json()
        ft["featureType"]["nativeName"] = tmp_name          # name given by Importer extension
        ft["featureType"]["originalName"] = source_name     # source file name
        ft["featureType"]["title"] = title                  # layer name as displayed in QGIS
        self.request(url, ft, "put")

        self.logInfo("Successfully created feature type from file '%s'" % filename)

        # Fix layer style reference and remove unwanted global style
        self.logInfo("Performing style cleanup...")
        try:
            self._fixLayerStyle(tmp_name, ft_name)
        except HTTPError as e:
            self.logWarning("Failed to clean up layer styles:\n%s" % e)
        else:
            self.logInfo("Successfully published layer '%s'" % title)

    def _publishRasterLayer(self, filename, layername):
        self._ensureWorkspaceExists()
        with open(filename, "rb") as f:
            url = "%s/workspaces/%s/coveragestores/%s/file.geotiff" % (self.url, self._workspace, layername)
            self.request(url, f.read(), "put")
        self.logInfo("Successfully created coverage from TIFF file '%s'" % filename)
        self._setLayerStyle(layername)

    def createGroups(self, groups, qgis_layers):
        for group in groups:
            self._publishGroup(group, qgis_layers)

    def _publishGroupMapBox(self, group, qgis_layers):
        name = group["name"]
        # compute actual style
        mbstylestring, warnings, obj, spriteSheet = mapboxgl.fromgeostyler.convertGroup(group, qgis_layers,

        # publish to geoserver
        self._ensureWorkspaceExists()
        styleExists = self.styleExists(name)
        if styleExists:
            self.deleteStyle(name)

        xml = "<style>" \
              + "<name>{0}</name>".format(name) \
              + "<workspace>{0}</workspace>".format(self._workspace) \
              + "<format>" \
              + "mbstyle" \
              + "</format>" \
              + "<filename>{0}.json</filename>".format(name) \
              + "</style>"

        url = self.url + "/workspaces/%s/styles" % (self._workspace)

        response = self.request(url, xml, "POST", {"Content-Type": "text/xml"})
        url = self.url + "/workspaces/%s/styles/%s?raw=true" % (self._workspace, name)

        headers = {"Content-Type": "application/vnd.geoserver.mbstyle+json"}
        response = self.request(url, mbstylestring, "PUT", headers)

        # save sprite sheet
        # get png -> bytes
        if spriteSheet:
            img_bytes = self.getImageBytes(spriteSheet["img"])
            img2x_bytes = self.getImageBytes(spriteSheet["img2x"])
            url = self.url + "/resource/workspaces/%s/styles/spriteSheet.png" % (self._workspace)
            r = self.request(url, img_bytes, "PUT")
            url = self.url + "/resource/workspaces/%s/styles/spriteSheet@2x.png" % (self._workspace)
            r = self.request(url, img2x_bytes, "PUT")
            url = self.url + "/resource/workspaces/%s/styles/spriteSheet.json" % (self._workspace)
            r = self.request(url, spriteSheet["json"], "PUT")
            url = self.url + "/resource/workspaces/%s/styles/spriteSheet@2x.json" % (self._workspace)
            r = self.request(url, spriteSheet["json2x"], "PUT")
            b = 1
        a = 1

    def getImageBytes(self, img):
        ba = QByteArray()
        buff = QBuffer(ba)
        buff.open(QIODevice.WriteOnly)
        img.save(buff, "PNG")
        img_bytes = ba.data()
        return img_bytes

    def _publishGroup(self, group, qgis_layers):
        self._publishGroupMapBox(group, qgis_layers)
        layers = []
        for layer in group["layers"]:
            if isinstance(layer, dict):
                layers.append({"@type": "layerGroup", "name": "%s:%s" % (self._workspace, layer["name"])})
                self._publishGroup(layer)
            else:
                layers.append({"@type": "layer", "name": "%s:%s" % (self._workspace, layer)})

        groupdef = {"layerGroup": {"name": group["name"],
                                   "title": group["title"],
                                   "abstractTxt": group["abstract"],
                                   "mode": "NAMED",
                                   "publishables": {"published": layers}}}

        url = "%s/workspaces/%s/layergroups" % (self.url, self._workspace)
        try:
            self.request(url+"/"+group["name"], method="delete")  # delete if it exists
        except HTTPError as e:
            # Swallow error if group does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise
        try:
            # Create new group
            self.request(url, groupdef, "post")
        except HTTPError:
            # Update group if it already exists
            self.request(url, groupdef, "put")

        # make sure there is VT format tiling
        url = "%s/gwc/rest/layers/%s:%s.xml" % (self.url.replace("/rest", ""), self._workspace, group["name"])
        r = self.request(url)
        xml = r.text
        if "application/vnd.mapbox-vector-tile" not in xml:
            xml = xml.replace("<mimeFormats>", "<mimeFormats><string>application/vnd.mapbox-vector-tile</string>")
            r = self.request(url, xml, "PUT", {"Content-Type": "text/xml"})

        self.logInfo("Group '%s' correctly created" % group["name"])

    def deleteStyle(self, name):
        url = "%s/workspaces/%s/styles/%s?purge=true&recurse=true" % (self.url, self._workspace, name)
        try:
            self.request(url, method="delete")
        except HTTPError as e:
            # Swallow error if style does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise

    def _clearCache(self):
        self._layersCache = None

    def _exists(self, url, category, name):
        try:
            if category != "layer" or self._layersCache is None:
                r = self.request(url)
                root = r.json()["%ss" % category]
                if category in root:
                    items = [s["name"] for s in root[category]]
                    if category == "layer":
                        self._layersCache = items
                else:
                    return False
            else:
                items = self._layersCache
            return name in items
        except:
            return False

    def layerExists(self, name):
        url = "%s/workspaces/%s/layers.json" % (self.url, self._workspace)
        return self._exists(url, "layer", name)

    def layers(self):
        url = "%s/workspaces/%s/layers.json" % (self.url, self._workspace)
        r = self.request(url)
        root = r.json()["layers"]
        if "layer" in root:
            return [s["name"] for s in root["layer"]]
        else:
            return []

    def styleExists(self, name):
        url = "%s/workspaces/%s/styles.json" % (self.url, self._workspace)
        return self._exists(url, "style", name)

    def workspaceExists(self):
        url = "%s/workspaces.json" % self.url
        return self._exists(url, "workspace", self._workspace)

    def willDeleteLayersOnPublication(self, toPublish):
        if self.workspaceExists():
            return bool(set(self.layers()) - set(toPublish))
        return False

    def datastoreExists(self, name):
        url = "%s/workspaces/%s/datastores.json" % (self.url, self._workspace)
        return self._exists(url, "dataStore", name)

    def _deleteDatastore(self, name):
        url = "%s/workspaces/%s/datastores/%s?recurse=true" % (self.url, self._workspace, name)
        try:
            self.request(url, method="delete")
        except HTTPError as e:
            # Swallow error if datastore does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise

    def deleteLayer(self, name, recurse=True):
        param = '?recurse=true' if recurse else ""
        url = "%s/workspaces/%s/layers/%s.json%s" % (self.url, self._workspace, name, param)
        try:
            self.request(url, method="delete")
        except HTTPError as e:
            # Swallow error if layer does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise

    def openPreview(self, names, bbox, srs):
        url = self.layerPreviewUrl(names, bbox, srs)
        webbrowser.open_new_tab(url)

    def layerPreviewUrl(self, names, bbox, srs):
        baseurl = self.baseUrl()
        names = ",".join(["%s:%s" % (self._workspace, name) for name in names])
        url = (
                "%s/%s/wms?service=WMS&version=1.1.0&request=GetMap&layers=%s&format=application/openlayers&bbox=%s&srs=%s&width=800&height=600"
                % (baseurl, self._workspace, names, bbox, srs))
        return url

    def fullLayerName(self, layerName):
        return "%s:%s" % (self._workspace, layerName)

    def layerWmsUrl(self):
        return "%s/wms?service=WMS&version=1.1.0&request=GetCapabilities" % (self.baseUrl())

    def layerWfsUrl(self):
        return "%s/wfs" % (self.baseUrl())

    def setLayerMetadataLink(self, name, url):
        layerUrl = "%s/workspaces/%s/layers/%s.json" % (self.url, self._workspace, name)
        r = self.request(layerUrl)
        resourceUrl = r.json()["layer"]["resource"]["href"]
        r = self.request(resourceUrl)
        layer = r.json()
        key = "featureType" if "featureType" in layer else "coverage"
        layer[key]["metadataLinks"] = {
            "metadataLink": [
                {
                    "type": "text/html",
                    "metadataType": "ISO19115:2003",
                    "content": url
                }
            ]
        }
        self.request(resourceUrl, data=layer, method="put")

    def clearWorkspace(self):
        """
        Clears all feature types and coverages (rasters) and their corresponding layers.
        Leaves styles and datastore definitions in tact.
        """
        if not self.workspaceExists():
            # Nothing to delete: workspace does not exist yet (so let's create it)
            self._createWorkspace()
            return

        # Get database datastores configuration
        db_stores = []
        url = "%s/workspaces/%s/datastores.json" % (self.url, self._workspace)
        stores = self.request(url).json()["dataStores"] or {}
        for store in stores.get("dataStore", []):
            url = "%s/workspaces/%s/datastores/%s.json" % (self.url, self._workspace, store["name"])
            ds = self.request(url).json()
            params = ds["dataStore"].get("connectionParameters", {})
            if any(entry["@key"] == "dbtype" for entry in params.get("entry", [])):
                # Fix namespace
                if self._fixNamespaceParam(params):
                    self.request(url, ds, "put")
                # Store copy of datastore configuration if it's a database
                db_stores.append(dict(ds))

        # Remove all styles with purge=true option to prevent SLD leftovers
        url = "%s/workspaces/%s/styles.json" % (self.url, self._workspace)
        styles = self.request(url).json()["styles"] or {}
        for style in styles.get("style", []):
            url = "%s/workspaces/%s/styles/%s.json?recurse=true&purge=true" % (self.url, self._workspace, style["name"])
            self.request(url, method="delete")

        # Delete workspace recursively
        url = "%s/workspaces/%s.json?recurse=true" % (self.url, self._workspace)
        self.request(url, method="delete")

        # Recreate the workspace
        self._createWorkspace()

        # Add all database datastores
        for body in db_stores:
            url = "%s/workspaces/%s/datastores.json" % (self.url, self._workspace)
            self.request(url, body, "post")

        self._clearCache()

    def _fixNamespaceParam(self, params):
        """
        Fixes the namespace connection parameter to match the namespace URI for the current workspace.
        If the fix was applied successfully, True is returned.
        """
        for entry in params.get("entry", []):
            if entry["@key"] != "namespace":
                continue
            # Get expected namespace endpoint
            url = "%s/namespaces/%s.json" % (self.url, self._workspace)
            try:
                ns = self.request(url).json()
            except HTTPError:
                self.logWarning("GeoServer namespace '%s' does not exist")
                return False
            entry["$"] = ns["namespace"]["uri"]
            return True
        return False

    def _publishStyle(self, name, style_filepath):
        # Make sure that the workspace is present
        self._ensureWorkspaceExists()

        # Figure out what style we're dealing with
        filetype = None
        headers = {}
        filemode = 'r'
        filename = os.path.basename(style_filepath)
        _, ext = os.path.splitext(filename.casefold())
        if ext == ".zip":
            filetype = 'ZIP'
            headers = {"Content-Type": "application/zip"}
            filemode = 'rb'
        elif ext == ".mapbox":
            filetype = 'MBStyle'
            headers = {"Content-Type": "application/vnd.geoserver.mbstyle+json"}

        # If style does not exist, create it using POST
        if not self.styleExists(name):
            try:
                if ext == ".zip":
                    # Create style but do not upload ZIP yet
                    url = self.url + "/workspaces/%s/styles" % self._workspace
                    body = {
                        "style": {
                            "name": name,
                            "filename": filename.replace('zip', 'sld')
                        }
                    }
                    self.request(url, body, "post")
                elif ext == ".mapbox":
                    # Upload MBStyle JSON
                    url = self.url + "/workspaces/%s/styles?name=%s" % (self._workspace, name)
                    with open(style_filepath, filemode) as f:
                        self.request(url, f.read(), "post", headers)
            except HTTPError as e:
                self.logError("Failed to create new style '%s' in workspace '%s':\n%s" % (name, self._workspace, e))
                return
            self.logInfo(QCoreApplication.translate("GeocatBridge",
                                                    "Successfully created style '%s' in workspace '%s'"
                                                    % (name, self._workspace)))
            if ext == ".mapbox":
                # If a Mapbox JSON was uploaded, we're done now
                return

        # Update existing style (perform upload)
        url = self.url + "/workspaces/%s/styles/%s" % (self._workspace, name)
        try:
            with open(style_filepath, filemode) as f:
                self.request(url, f.read(), "put", headers)
        except HTTPError as e:
            self.logError("Failed to update style '%s' in workspace '%s' "
                          "using ZIP file '%s':\n%s" % (name, self._workspace, style_filepath, e))
            return
        self.logInfo(QCoreApplication.translate("GeocatBridge",
                                                "Successfully updated style '%s' from %s in workspace '%s' using ZIP file '%s'"
                                                % (name, filetype, self._workspace, style_filepath)))

    def _setLayerStyle(self, name, style_name=None):
        """
        Update the layer style so that it matches the layer name and workspace.
        If the update was successful, the previous style object is returned.
        If the update failed or the new style does not exist, an empty object is returned.

        :param name:        Layer (and style name).
        :param style_name:  Style name (if different from layer name).
        :return:            A style object.
        """
        style_name = style_name or name

        # Get layer properties
        url = "%s/workspaces/%s/layers/%s.json" % (self.url, self._workspace, name)
        try:
            layer_def = self.request(url).json()
            if not self.styleExists(style_name):
                self.logWarning(QCoreApplication.translate("GeocatBridge",
                                                           "Style '%s' does not exist in workspace '%s'" %
                                                           (style_name, self._workspace)))

                raise KeyError()
        except (HTTPError, KeyError):
            return {}

        # Copy current default style and update for layer
        old_style = dict(layer_def["layer"]["defaultStyle"])
        style_url = "%s/workspaces/%s/styles/%s.json" % (self.url, self._workspace, style_name)
        layer_def["layer"]["defaultStyle"] = {
            "name": "%s:%s" % (self._workspace, style_name),
            "workspace": self._workspace,
            "href": style_url
        }
        try:
            self.request(url, data=layer_def, method="put")
        except HTTPError:
            return {}
        return old_style

    def _fixLayerStyle(self, actual_name, proper_name):
        """
        Fixes the layer style for feature types that have been imported using the GeoServer Importer extension.
        The Importer extension also creates an unwanted global style, which is removed by this function.

        :param actual_name: Layer name given by GeoServer (may contain numeric suffix).
        :param proper_name: The desired layer name, which should also be the style name.
        """

        old_style = self._setLayerStyle(actual_name, proper_name)
        if not old_style:
            # Something went wrong or the new style to assign does not exist:
            # The layer style will remain as-is and we will not delete the old style.
            return

        # Only remove style created by Importer extension if it is a global style.
        # However, built-in GeoServer styles should not be touched.
        if old_style.get("workspace"):
            # Style is not global: don't delete old style
            return
        style_name = old_style.get("name", "").casefold()
        if style_name and style_name not in ("raster", "point", "polygon", "line", "generic"):
            remove_url = "%s?purge=true" % old_style.get("href")
            try:
                # Delete old style
                self.request(remove_url, method="delete")
            except HTTPError:
                # Bad request or style is still in use by other layers: do nothing
                pass

    def _createWorkspace(self):
        """ Creates the workspace. """
        url = "%s/workspaces" % self.url
        ws = {"workspace": {"name": self._workspace}}
        self.request(url, data=ws, method="post")

    def _ensureWorkspaceExists(self):
        if not self.workspaceExists():
            self._createWorkspace()

    def postgisDatastores(self):
        pg_datastores = []
        url = "%s/workspaces.json" % self.url
        res = self.request(url).json().get("workspaces", {})
        if not res:
            # There aren't any workspaces (and thus no dataStores)
            return pg_datastores
        for ws_url in (s.get("href") for s in res.get("workspace", [])):
            props = self.request(ws_url).json().get("workspace", {})
            ws_name, ds_list_url = props.get("name"), props.get("dataStores")
            for ds_name in self._getPostgisDatastores(ds_list_url):
                pg_datastores.append("%s:%s" % (ws_name, ds_name))
        return pg_datastores

    def addPostgisDatastore(self, datastoreDef):
        url = "%s/workspaces/%s/datastores" % (self.url, self._workspace)
        self.request(url, data=datastoreDef, method="post")

    def addOGCServers(self):
        baseurl = "/".join(self.url.split("/")[:-1])
        addServicesForGeodataServer(self.name, baseurl, self.authid)

    # ensure that the geoserver we are dealing with is at least 2.13.2
    def checkMinGeoserverVersion(self, errors):
        try:
            url = "%s/about/version.json" % self.url
            result = self.request(url).json()['about']['resource']
        except HTTPError:
            errors.add("Could not connect to Geoserver.  Please check the server settings (including password).")
            return
        try:
            ver = next((x["Version"] for x in result if x["@name"] == 'GeoServer'), None)
            if ver is None:
                return  # couldn't find version -- dev GS, lets say its ok
            ver_major, ver_minor, ver_patch = ver.split('.')

            if int(ver_minor) <= 13:
                # GeoServer instance is too old
                errors.add(
                    "Geoserver 2.14.0 or later is required. Selected Geoserver is version '" + ver + "'. "
                    "Please see <a href='https://my.geocat.net/knowledgebase/100/Bridge-4-compatibility-with-"
                    "Geoserver-2134-and-before.html'>Bridge 4 Compatibility with Geoserver 2.13.4 and before</a>"
                )
        except Exception as e:
            # version format might not be the expected. This is usually a RC or dev version, so we consider it ok
            self.logWarning("Failed to retrieve GeoServer version info:\n%s" % e)

    def validateGeodataBeforePublication(self, errors, toPublish, onlySymbology):
        if not self._workspace:
            errors.add("QGIS Project is not saved. Project must be saved before publishing layers to GeoServer.")
        if "." in self._workspace:
            errors.add("QGIS project name contains unsupported characters ('.'). "
                       "Please save with a different name and try again.")
        if self.willDeleteLayersOnPublication(toPublish) and not onlySymbology:
            ret = QMessageBox.question(None, "Workspace",
                                       "A workspace named '%s' already exists and contains layers that will be deleted."
                                       "\nDo you want to proceed?" % self._workspace,
                                       QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                errors.add("Cannot overwrite existing workspace.")
        self.checkMinGeoserverVersion(errors)
