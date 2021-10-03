import json
import os
import shutil
import sqlite3
from zipfile import ZipFile

from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice, QSettings
from qgis.core import (
    QgsProject,
    QgsDataSourceUri,
    QgsProcessingParameterMapLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterAuthConfig
)
from requests.exceptions import HTTPError, RequestException

from geocatbridge.publish.style import (
    saveLayerStyleAsZippedSld, layerStyleAsMapboxFolder, convertMapboxGroup
)
from geocatbridge.process.algorithm import BridgeAlgorithm
from geocatbridge.publish.exporter import exportLayer
from geocatbridge.servers import manager
from geocatbridge.servers.bases import DataCatalogServerBase
from geocatbridge.servers.models.gs_storage import GeoserverStorage
from geocatbridge.servers.views.geoserver import GeoServerWidget
from geocatbridge.utils import layers as lyr_utils
from geocatbridge.utils.files import tempFileInSubFolder, tempSubFolder, Path
from geocatbridge.utils.meta import getAppName, semanticVersion
from geocatbridge.utils.network import TESTCON_TIMEOUT


class GeoserverServer(DataCatalogServerBase):

    def __init__(self, name, authid="", url="", storage=GeoserverStorage.FILE_BASED, postgisdb=None,
                 useOriginalDataSource=False, useVectorTiles=False):
        """
        Creates a new GeoServer model instance.

        :param name:                    Descriptive server name (given by the user)
        :param authid:                  QGIS Authentication ID (optional)
        :param url:                     GeoServer base or REST API URL
        :param storage:                 Data storage type (default = FILE_BASED)
        :param postgisdb:               PostGIS database (required if `storage` is *not* FILE_BASED)
        :param useOriginalDataSource:   Set to True if original data source should be used.
                                        This means that no data will be uploaded.
        :param useVectorTiles:          Set to True if vector tiles need to be published.
        """
        super().__init__(name, authid, url)
        self.postgisdb = None
        try:
            self.storage = GeoserverStorage[storage]
        except IndexError:
            raise ValueError(f"'{storage}' is not a valid GeoServer storage type")
        if self.storage != GeoserverStorage.FILE_BASED:
            self.postgisdb = postgisdb
        self.useOriginalDataSource = useOriginalDataSource
        self.useVectorTiles = useVectorTiles
        self._workspace = None
        self._uploaded_data = {}
        self._existing_layers = frozenset()  # unique list of layers in workspace on server (refreshed all the time)
        self._exported_layers = {}           # lookup of layer source path - exported file path
        self._published_layers = set()       #
        self._pg_datastore_exists = False
        self._apiurl = self.fixRestApiUrl()

    def getSettings(self) -> dict:
        return {
            'name': self.serverName,
            'authid': self.authId,
            'url': self.baseUrl,
            'storage': self.storage,
            'postgisdb': self.postgisdb,
            'useOriginalDataSource': self.useOriginalDataSource,
            'useVectorTiles': self.useVectorTiles
        }

    @classmethod
    def getWidgetClass(cls) -> type:
        return GeoServerWidget

    @classmethod
    def getLabel(cls) -> str:
        return 'GeoServer'

    @property
    def workspace(self):
        if self._workspace is None:
            self.refreshWorkspaceName()
        return self._workspace

    def refreshWorkspaceName(self):
        """ Resets the QGIS Project (file) name. Can be `None` if not found/saved. """
        self._workspace = None
        path = QgsProject().instance().absoluteFilePath()
        if path:
            self._workspace = Path(path).stem
        if not self._workspace:
            self.logWarning("Workspace name could not be derived from QGIS project: please save the project")

    def forceWorkspace(self, workspace):
        self._workspace = workspace

    def fixRestApiUrl(self):
        """ Appends 'rest' to the base URL if it is missing and returns the new URL.
        If the base URL already has 'rest', it is returned as-is, while 'rest' is stripped from the base URL.
        """
        url = self.baseUrl.rstrip("/")
        if not url.endswith("/rest"):
            # Remove potential trailing slash from base URL, append REST
            self._baseurl = url
            url += "/rest"
        else:
            # Strip REST from base URL
            self._baseurl = url[:-5]
        return url

    @property
    def apiUrl(self):
        return self._apiurl

    def prepareForPublishing(self, only_symbology):
        if not only_symbology:
            self.clearWorkspace()
        self._ensureWorkspaceExists()
        self._uploaded_data = {}
        self._exported_layers = {}
        self._pg_datastore_exists = False
        self._published_layers = set()

    def closePublishing(self):
        if not self.useVectorTiles:
            return
        folder = tempSubFolder()
        self.logInfo(f"Creating layer styles for Mapbox vector tiles in {folder}...")
        warnings = layerStyleAsMapboxFolder(self._published_layers, folder)
        for w in warnings:
            self.logWarning(w)
        self.logInfo(f"Editing Mapbox files...")
        self._editMapboxFiles(folder)
        self.logInfo(f"Publishing Mapbox styles...")
        self.publishMapboxGLStyle(folder)
        self.logInfo(f"Publishing OpenLayers vector tile preview...")
        self._publishOpenLayersPreview(folder)

    def _publishOpenLayersPreview(self, folder):
        style_filename = os.path.join(folder, "style.mapbox")
        with open(style_filename) as f:
            style = f.read()
        template = f"var style = {style};\nvar map = olms.apply('map', style);"

        js_filename = os.path.join(folder, "mapbox.js")
        with open(js_filename, "w") as f:
            f.write(template)
        src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "openlayers", "index.html")
        dst = os.path.join(folder, "index.html")
        shutil.copyfile(src, dst)
        self.uploadResource(f"{self.workspace}/index.html", src)
        self.uploadResource(f"{self.workspace}/mapbox.js", js_filename)

    def uploadResource(self, path, file):
        with open(file) as f:
            content = f.read()
        url = f"{self.apiUrl}/resource/{path}"
        self.request(url, "put", content)

    def _editMapboxFiles(self, folder):
        filename = os.path.join(folder, "style.mapbox")
        with open(filename) as f:
            mapbox = json.load(f)
        sources = mapbox["sources"]
        for name in sources.keys():
            url = (f"{self.baseUrl}/gwc/service/wmts?REQUEST=GetTile&SERVICE=WMTS"
                   f"&VERSION=1.0.0&LAYER={self.workspace}:{name}&STYLE=&TILEMATRIX=EPSG:900913:{{z}}"
                   "&TILEMATRIXSET=EPSG:900913&FORMAT=application/vnd.mapbox-vector-tile"
                   "&TILECOL={x}&TILEROW={y}")
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
        name = "mb_" + self.workspace
        filename = os.path.join(folder, "style.mapbox")
        self._publishStyle(name, filename)

    def publishStyle(self, layer):
        lyr_title, lyr_name = lyr_utils.getLayerTitleAndName(layer)
        export_layer = lyr_utils.getExportableLayer(layer, lyr_name)
        style_filename = tempFileInSubFolder(lyr_name + ".zip")
        warnings = saveLayerStyleAsZippedSld(export_layer, style_filename)
        for w in warnings:
            self.logWarning(w)
        self.logInfo(f"Style for layer '{layer.name()}' exported as ZIP file to '{style_filename}'")
        self._publishStyle(lyr_name, style_filename)
        self._published_layers.add(layer)
        return style_filename

    def publishLayer(self, layer, fields=None):
        lyr_title, safe_name = lyr_utils.getLayerTitleAndName(layer)
        if layer.type() == layer.VectorLayer:
            if layer.featureCount() == 0:
                self.logError(f"Layer '{lyr_title}' contains zero features and cannot be published")
                return

            if layer.dataProvider().name() == "postgres" and self.useOriginalDataSource:
                try:
                    from geocatbridge.servers.models.postgis import PostgisServer
                except (ImportError, ModuleNotFoundError):
                    raise Exception(self.translate(getAppName(), "Cannot find or import PostgisServer class"))
                else:
                    uri = QgsDataSourceUri(layer.source())
                    db = PostgisServer(
                        "temp", uri.authConfigId(), uri.host(), uri.port(), uri.schema(), uri.database())
                    self._publishVectorLayerFromPostgis(layer, db)
            elif self.storage != GeoserverStorage.POSTGIS_BRIDGE:
                src_path, src_name, src_ext = lyr_utils.getLayerSourceInfo(layer)
                filename = self._exported_layers.get(src_path)
                if not filename:
                    if self.storage == GeoserverStorage.POSTGIS_GEOSERVER:
                        shp_name = exportLayer(layer, fields, to_shapefile=True, force=True, logger=self)
                        basename = os.path.splitext(shp_name)[0]
                        filename = basename + ".zip"
                        with ZipFile(filename, 'w') as z:
                            for ext in (".shp", ".shx", ".prj", ".dbf"):
                                filetozip = basename + ext
                                z.write(filetozip, arcname=os.path.basename(filetozip))
                    else:
                        filename = exportLayer(layer, fields, logger=self)
                self._exported_layers[src_path] = filename
                if self.storage == GeoserverStorage.FILE_BASED:
                    self._publishVectorLayerFromFile(layer, filename)
                else:
                    self._publishVectorLayerFromFileToPostgis(layer, filename)
            elif self.storage == GeoserverStorage.POSTGIS_BRIDGE:
                db = manager.getServer(self.postgisdb)
                if not db:
                    raise Exception(self.translate(getAppName(), "Cannot find the selected PostGIS database"))
                db.importLayer(layer, fields)
                self._publishVectorLayerFromPostgis(layer, db)
        elif layer.type() == layer.RasterLayer:
            if layer.source() not in self._exported_layers:
                path = exportLayer(layer, fields, logger=self)
                self._exported_layers[layer.source()] = path
            filename = self._exported_layers[layer.source()]
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
            ds_list_url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores.json"

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
            if enabled and entries.get("dbtype", "").startswith("postgis"):
                yield ds_name

    def createPostgisDatastore(self):
        """
        Creates a new datastore based on the selected one in the Server widget
        if the workspace is created from scratch.

        :returns:   The existing or created PostGIS datastore name.
        """

        # Check if current workspaces has a PostGIS datastore (use first)
        for ds_name in self._getPostgisDatastores():
            return ds_name

        # Get workspace and datastore name from selected template in Server widget
        ws, ds_name = self.postgisdb.split(":")

        # Retrieve settings from datastore template
        url = f"{self.apiUrl}/workspaces/{ws}/datastores/{ds_name}.json"
        datastore = self.request(url).json()
        # Change datastore name to match workspace name
        datastore["dataStore"]["name"] = self.workspace
        # Change workspace settings to match the one for the current project
        datastore["dataStore"]["workspace"] = {
            "name": self.workspace,
            "href": f"{self.apiUrl}/workspaces/{self.workspace}.json"
        }
        # Fix featureTypes endpoint
        datastore["dataStore"]["featureTypes"] = \
            f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{self.workspace}/featuretypes.json"
        # Fix namespace connection parameter for current workspace
        self._fixNamespaceParam(datastore["dataStore"].get("connectionParameters", {}))
        # Post copy of datastore with modified workspace
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores.json"
        self.request(url, "post", datastore)
        return self.workspace

    def testConnection(self, errors: set):
        if not self.postgisdb:
            if self.storage == GeoserverStorage.POSTGIS_BRIDGE:
                errors.add(f'Server {self.serverName} configured with database storage, '
                           f'but without PostGIS server name')
                return False
            elif self.storage == GeoserverStorage.POSTGIS_GEOSERVER:
                errors.add(f'Server {self.serverName} configured with database storage, but without datastore name')
                return False
        try:
            url = f"{self.apiUrl}/about/version"
            self.request(url, timeout=TESTCON_TIMEOUT)
            return True
        except RequestException as e:
            msg = f'Could not connect to {self.serverName}'
            if isinstance(e, HTTPError) and e.response.status_code == 401:
                msg = f'{msg}: please check credentials'
            else:
                msg = f'{msg}: {e}'
        self.logError(msg)
        errors.add(msg)
        return False

    def _publishVectorLayerFromFile(self, layer, filename):
        self.logInfo(f"Publishing layer from file: {filename}")
        title, name = lyr_utils.getLayerTitleAndName(layer)
        is_data_uploaded = filename in self._uploaded_data
        if not is_data_uploaded:
            with open(filename, "rb") as f:
                self._deleteDatastore(name)
                url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{name}/file.gpkg?update=overwrite"
                self.request(url, "put", f.read())
            conn = sqlite3.connect(filename)
            cursor = conn.cursor()
            cursor.execute("""SELECT table_name FROM gpkg_geometry_columns""")  # noqa
            tablename = cursor.fetchall()[0][0]
            self._uploaded_data[filename] = (name, tablename)

        dataset_name, geoserver_layer_name = self._uploaded_data[filename]
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{dataset_name}/featuretypes/{geoserver_layer_name}.json"  # noqa
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
        if is_data_uploaded:
            url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{dataset_name}/featuretypes"
            self.request(url, "post", ft)
        else:
            self.request(url, "put", ft)
        self.logInfo(f"Successfully created feature type from GeoPackage file '{filename}'")
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
        ds_url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores"
        self.request(ds_url, data=ds, method="post")
        ft = {
            "featureType": {
                "name": name,
                "srs": layer.crs().authid()
            }
        }
        ft_url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{name}/featuretypes"
        self.request(ft_url, data=ft, method="post")
        self._setLayerStyle(name)

    def _getImportResult(self, import_id, task_id):
        """ Get the error message on the import task (if any) and the resulting layer name. """
        task = self.request(f"{self.apiUrl}/imports/{import_id}/tasks/{task_id}").json()["task"] or {}
        err_msg = task.get("errorMessage", "")
        if err_msg:
            err_msg = f"GeoServer Importer Extension error: {err_msg}"
        return err_msg, task["layer"]["name"]

    def _publishVectorLayerFromFileToPostgis(self, layer, filename):
        self.logInfo(f"Publishing layer '{layer.name()}' from file '{filename}'...")
        datastore = self.createPostgisDatastore()
        title, ft_name = lyr_utils.getLayerTitleAndName(layer)
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
                        "name": self.workspace
                    }
                }
            }
        }
        url = f"{self.apiUrl}/imports.json"
        ret = self.request(url, "post", body)

        # Create a new task and upload ZIP
        self.logInfo("Uploading layer data...")
        import_id = ret.json()["import"]["id"]
        zipname = os.path.basename(filename)
        url = f"{self.apiUrl}/imports/{import_id}/tasks/{zipname}"
        with open(filename, "rb") as f:
            ret = self.request(url, method="put", files={zipname: (zipname, f, 'application/octet-stream')})

        # Reassign PostGIS datastore as target (just to be sure)
        task_id = ret.json()["task"]["id"]
        body = {
            "dataStore": {
                "name": datastore
            }
        }
        url = f"{self.apiUrl}/imports/{import_id}/tasks/{task_id}/target.json"
        self.request(url, "put", body)
        del ret

        # Start import execution
        self.logInfo(f"Starting Importer task for layer '{ft_name}'...")
        url = f"{self.apiUrl}/imports/{import_id}"
        self.request(url, method="post")

        # Get the import result (error message and target layer name)
        import_err, tmp_name = self._getImportResult(import_id, task_id)
        if import_err:
            self.logError(f"Failed to publish QGIS layer '{title}' as '{ft_name}'.\n\n{import_err}")
            return

        self._uploaded_data[filename] = (datastore, source_name)

        # Get the created feature type
        self.logInfo("Checking if feature type creation was successful...")
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{datastore}/featuretypes/{tmp_name}.json"
        try:
            ret = self.request(url + "?quietOnNotFound=true")
        except RequestException as e:
            # Something unexpected happened: failure cannot be retrieved from import task,
            # so the user should check the GeoServer logs to find out what caused it.
            if isinstance(e, HTTPError) and e.response.status_code == 404:
                self.logError(f"Failed to publish QGIS layer '{title}' as '{ft_name}' due to an unknown error.\n"
                              "Please check the GeoServer logs.")
                return
            raise

        # Modify the feature type descriptions, but leave the name in tact to avoid db schema mismatches
        self.logInfo("Fixing feature type properties...")
        ft = ret.json()
        ft["featureType"]["nativeName"] = tmp_name  # name given by Importer extension
        ft["featureType"]["originalName"] = source_name  # source file name
        ft["featureType"]["title"] = title  # layer name as displayed in QGIS
        self.request(url, "put", ft)

        self.logInfo(f"Successfully created feature type from file '{filename}'")

        # Fix layer style reference and remove unwanted global style
        self.logInfo("Performing style cleanup...")
        try:
            self._fixLayerStyle(tmp_name, ft_name)
        except RequestException as e:
            self.logWarning(f"Failed to clean up layer styles: {e}")
        else:
            self.logInfo(f"Successfully published layer '{title}'")

    def _publishRasterLayer(self, filename, layername):
        self._ensureWorkspaceExists()
        with open(filename, "rb") as f:
            url = f"{self.apiUrl}/workspaces/{self.workspace}/coveragestores/{layername}/file.geotiff"
            self.request(url, "put", f.read())
        self.logInfo(f"Successfully created coverage from TIFF file '{filename}'")
        self._setLayerStyle(layername)

    def createGroups(self, groups, qgis_layers):
        for group in groups:
            self._publishGroup(group, qgis_layers)

    def _publishGroupMapBox(self, group, qgis_layers):
        name = group["name"]
        # compute actual style
        mbstylestring, warnings, obj, sprite_sheet = \
            convertMapboxGroup(
                group, qgis_layers, self.apiUrl, self.workspace, group["name"]
            )  # FIXME!

        # publish to geoserver
        self._ensureWorkspaceExists()
        if not self.deleteStyle(name):
            raise Exception('Failed to delete Mapbox style on GeoServer')

        xml = f"<style>" \
              f"<name>{name}</name>" \
              f"<workspace>{self.workspace}</workspace>" \
              f"<format>mbstyle</format>" \
              f"<filename>{name}.json</filename>" \
              f"</style>"

        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles"
        self.request(url, "post", xml, headers={"Content-Type": "text/xml"})

        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{name}?raw=true"
        headers = {"Content-Type": "application/vnd.geoserver.mbstyle+json"}
        self.request(url, "put", mbstylestring, headers=headers)

        # save sprite sheet
        # get png -> bytes
        if sprite_sheet:
            img_bytes = self.getImageBytes(sprite_sheet["img"])
            img2x_bytes = self.getImageBytes(sprite_sheet["img2x"])
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet.png"
            self.request(url, "put", img_bytes)
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet@2x.png"
            self.request(url, "put", img2x_bytes)
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet.json"
            self.request(url, "put", sprite_sheet["json"])
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet@2x.json"
            self.request(url, "put", sprite_sheet["json2x"])

    @staticmethod
    def getImageBytes(img):
        ba = QByteArray()
        buff = QBuffer(ba)
        buff.open(QIODevice.WriteOnly)
        img.save(buff, "png")
        img_bytes = ba.data()
        return img_bytes

    def _publishGroup(self, group, qgis_layers):
        if self.useVectorTiles:
            self._publishGroupMapBox(group, qgis_layers)

        layers = []
        for layer in group["layers"]:
            if isinstance(layer, dict):
                layers.append({"@type": "layerGroup", "name": f"{self.workspace}:{layer['name']}"})
                self._publishGroup(layer, qgis_layers)
            else:
                layers.append({"@type": "layer", "name": f"{self.workspace}:{layer}"})

        groupdef = {
            "layerGroup": {
                "name": group["name"],
                "title": group["title"],
                "abstractTxt": group["abstract"],
                "mode": "NAMED",
                "publishables": {
                    "published": layers
                }
            }
        }

        url = f"{self.apiUrl}/workspaces/{self.workspace}/layergroups"
        try:
            self.request(f'{url}/{group["name"]}', method="delete")  # delete if it exists
        except HTTPError as e:
            # Swallow error if group does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise
        try:
            # Create new group
            self.request(url, "post", groupdef)
        except HTTPError:
            # Update group if it already exists
            try:
                self.request(url, "put", groupdef)
            except HTTPError as err:
                self.logError(f"Failed to update layer group: {err}")
                return

        # make sure there is VT format tiling
        if self.useVectorTiles:
            url = f"{self.baseUrl}/gwc/rest/layers/{self.workspace}:{group['name']}.xml"
            r = self.request(url)
            xml = r.text
            if "application/vnd.mapbox-vector-tile" not in xml:
                xml = xml.replace("<mimeFormats>", "<mimeFormats><string>application/vnd.mapbox-vector-tile</string>")
                self.request(url, "put", xml, headers={"Content-Type": "text/xml"})

        self.logInfo(f"Group '{group['name']}' correctly created")

    def deleteStyle(self, name) -> bool:
        if not self.styleExists(name):
            return True
        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{name}?purge=true&recurse=true"
        try:
            self.request(url, method="delete")
        except RequestException as e:
            self.logError(f"Failed to delete style '{name}': {e}")
            return False
        return True

    def _clearCache(self):
        self._existing_layers = frozenset()

    def _exists(self, url, category, name):
        try:
            if category != "layer" or not self._existing_layers:
                r = self.request(url)
                root = r.json()[f"{category}s"]  # make plural -> TODO: improve robustness?
                if category in root:
                    items = frozenset(s["name"] for s in root[category])
                    if category == "layer":
                        self._existing_layers = items
                else:
                    return False
            else:
                items = self._existing_layers
            return name in items
        except Exception as err:
            self.logError(err)
            return False

    def layerExists(self, name):
        if not self.workspace:
            return False
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers.json"
        return self._exists(url, "layer", name)

    def layers(self):
        if not self.workspace:
            return []
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers.json"
        r = self.request(url)
        root = r.json()["layers"]
        if "layer" in root:
            return [s["name"] for s in root["layer"]]
        else:
            return []

    def styleExists(self, name):
        if not self.workspace:
            return False
        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles.json"
        return self._exists(url, "style", name)

    def workspaceExists(self):
        if not self.workspace:
            return False
        url = f"{self.apiUrl}/workspaces.json"
        return self._exists(url, "workspace", self.workspace)

    def willDeleteLayersOnPublication(self, to_publish):
        if self.workspaceExists():
            return bool(set(self.layers()) - set(to_publish))
        return False

    def datastoreExists(self, name):
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores.json"
        return self._exists(url, "dataStore", name)

    def _deleteDatastore(self, name):
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{name}?recurse=true"
        try:
            self.request(url, method="delete")
        except HTTPError as e:
            # Swallow error if datastore does not exist (404), re-raise otherwise
            if e.response.status_code != 404:
                raise

    def deleteLayer(self, name) -> bool:
        if not self.layerExists(name):
            return True
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers/{name}.json?recurse=true"
        try:
            self.request(url, method="delete")
        except RequestException as e:
            self.logError(f"Failed to delete layer '{name}': {e}")
            return False
        return True

    def getPreviewUrl(self, layer_names, bbox, srs):
        names = ",".join([f"{self.workspace}:{name}" for name in layer_names])
        url = f"{self.baseUrl}/{self.workspace}/wms?service=WMS&version=1.1.0&request=GetMap&layers={names}" \
              f"&format=application/openlayers&bbox={bbox}&srs={srs}&width=800&height=600"
        return url

    def fullLayerName(self, layer_name):
        return f"{self.workspace}:{layer_name}"

    def getWmsUrl(self):
        return f"{self.baseUrl}/wms?service=WMS&version=1.1.0&request=GetCapabilities"

    def getWfsUrl(self):
        return f"{self.baseUrl}/wfs"

    def setLayerMetadataLink(self, name, url):
        layer_url = f"{self.apiUrl}/workspaces/{self.workspace}/layers/{name}.json"
        r = self.request(layer_url)
        resource_url = r.json()["layer"]["resource"]["href"]
        r = self.request(resource_url)
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
        self.request(resource_url, "put", layer)

    def clearWorkspace(self, recreate=True) -> bool:
        """
        Clears all feature types and coverages (rasters) and their corresponding layers.
        Leaves styles and datastore definitions in tact.
        """
        if not self.workspaceExists() and recreate:
            # Nothing to delete: workspace does not exist yet (so let's create it)
            self._createWorkspace()
            return False

        # Get database datastores configuration
        db_stores = []
        if recreate:
            url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores.json"
            stores = self.request(url).json()["dataStores"] or {}
            for store in stores.get("dataStore", []):
                url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{store['name']}.json"
                ds = self.request(url).json()
                params = ds["dataStore"].get("connectionParameters", {})
                if any(entry["@key"] == "dbtype" for entry in params.get("entry", [])):
                    # Fix namespace
                    if self._fixNamespaceParam(params):
                        self.request(url, "put", ds)
                    # Store copy of datastore configuration if it's a database
                    db_stores.append(dict(ds))

            # Remove all styles with purge=true option to prevent SLD leftovers
            url = f"{self.apiUrl}/workspaces/{self.workspace}/styles.json"
            styles = self.request(url).json()["styles"] or {}
            for style in styles.get("style", []):
                url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{style['name']}.json?recurse=true&purge=true"
                self.request(url, method="delete")

        # Delete workspace recursively
        url = f"{self.apiUrl}/workspaces/{self.workspace}.json?recurse=true"
        self.request(url, method="delete")

        if recreate:
            # Recreate the workspace
            self._createWorkspace()

            # Add all database datastores
            for body in db_stores:
                url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores.json"
                self.request(url, "post", body)

        self._clearCache()
        return True

    def _fixNamespaceParam(self, params):
        """
        Fixes the namespace connection parameter to match the namespace URI for the current workspace.
        If the fix was applied successfully, True is returned.
        """
        for entry in params.get("entry", []):
            if entry["@key"] != "namespace":
                continue
            # Get expected namespace endpoint
            url = f"{self.apiUrl}/workspaces/{self.workspace}.json"
            try:
                ns = self.request(url).json()
            except HTTPError as err:
                if err.response.status_code == 404:
                    self.logWarning(f"GeoServer workspace '{self.workspace}' does not exist")
                return False
            except RequestException as err:
                self.logError(f"Failed to query GeoServer workspace {self.workspace}: {err}")
                return False
            uri = ns.get("namespace", {}).get("uri")
            if uri:
                entry["$"] = uri
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

        # Check if we're dealing with an existing style (update): set URL and method accordingly
        update = self.styleExists(name)
        endpoint = f"{self.apiUrl}/workspaces/{self.workspace}/styles"
        style_url = f"{endpoint}/{name}" if update else f"{endpoint}?name={name}"
        method = "put" if update else "post"

        # Perform POST (new style) or PUT (update style) request
        try:
            with open(style_filepath, filemode) as f:
                self.request(style_url, method, f.read(), headers=headers)
        except RequestException as e:
            self.logError(f"Failed to {'update' if update else 'create new'} style '{name}' in workspace "
                          f"'{self.workspace}' using {filetype} file '{style_filepath}': {e}")
            return

        self.logInfo(f"Successfully {'updated' if update else 'created new'} style '{name}' from "
                     f"{filetype} in workspace '{self.workspace}' using file '{style_filepath}'")

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
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers/{name}.json"
        try:
            layer_def = self.request(url).json()
            if not self.styleExists(style_name):
                self.logWarning(f"Style '{style_name}' does not exist in workspace '{self.workspace}'")
                raise KeyError()
        except (RequestException, KeyError):
            return {}

        # Copy current default style and update for layer
        old_style = dict(layer_def["layer"]["defaultStyle"])
        style_url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{style_name}.json"
        layer_def["layer"]["defaultStyle"] = {
            "name": f"{self.workspace}:{style_name}",
            "workspace": self.workspace,
            "href": style_url
        }
        try:
            self.request(url, data=layer_def, method="put")
        except RequestException:
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
            remove_url = f"{old_style.get('href')}?purge=true"
            try:
                # Delete old style
                self.request(remove_url, method="delete")
            except RequestException:
                # Bad request or style is still in use by other layers: do nothing
                pass

    def _createWorkspace(self):
        """ Creates the workspace. """
        url = f"{self.apiUrl}/workspaces"
        ws = {"workspace": {"name": self.workspace}}
        self.request(url, data=ws, method="post")

    def _ensureWorkspaceExists(self):
        if not self.workspaceExists():
            self._createWorkspace()

    def getWorkspaces(self) -> list:
        """ Returns a list of workspace names from GeoServer. """
        url = f"{self.apiUrl}/workspaces.json"
        try:
            res = self.request(url).json().get("workspaces", {})
        except RequestException as e:
            if isinstance(e, HTTPError) and e.response.status_code == 401:
                self.showErrorBar("Error", f"Failed to connect to {self.serverName}: bad or missing credentials")
            self.logError(f"Failed to retrieve workspaces from {self.apiUrl}: {e}")
            return []
        if not res:
            self.logWarning(f"GeoServer instance at {self.apiUrl} does not seem to have any workspaces")
            return []
        return [w.get("name") for w in res.get("workspace", [])]

    def getPostgisDatastores(self, workspace):
        """ Returns a list of all PostGIS datastores on GeoServer. """
        ds_list_url = f"{self.apiUrl}/workspaces/{workspace}/datastores.json"
        return [f"{workspace}:{ds_name}" for ds_name in self._getPostgisDatastores(ds_list_url)]

    def addPostgisDatastore(self, datastore_def):
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores"
        self.request(url, data=datastore_def, method="post")

    def addOGCServices(self):
        """ Adds OGC WMS and WFS services to the QGIS settings for this GeoServer instance. """
        s = QSettings()

        # Set WMS services
        s.setValue(f'qgis/WMS/{self.serverName}/password', '')
        s.setValue(f'qgis/WMS/{self.serverName}/username', '')
        s.setValue(f'qgis/WMS/{self.serverName}/authcfg', self.authId)
        s.setValue(f'qgis/connections-wms/{self.serverName}/dpiMode', 7)
        s.setValue(f'qgis/connections-wms/{self.serverName}/ignoreAxisOrientation', False)
        s.setValue(f'qgis/connections-wms/{self.serverName}/ignoreGetFeatureInfoURI', False)
        s.setValue(f'qgis/connections-wms/{self.serverName}/ignoreGetMapURI', False)
        s.setValue(f'qgis/connections-wms/{self.serverName}/invertAxisOrientation', False)
        s.setValue(f'qgis/connections-wms/{self.serverName}/referer', '')
        s.setValue(f'qgis/connections-wms/{self.serverName}/smoothPixmapTransform', False)
        s.setValue(f'qgis/connections-wms/{self.serverName}/url', f'{self.baseUrl}/wms')

        # Set WFS services
        s.setValue(f'qgis/WFS/{self.serverName}/username', '')
        s.setValue(f'qgis/WFS/{self.serverName}/password', '')
        s.setValue(f'qgis/connections-wfs/{self.serverName}/referer', '')
        s.setValue(f'qgis/connections-wfs/{self.serverName}/url', f'{self.baseUrl}/wfs')
        s.setValue(f'qgis/WFS/{self.serverName}/authcfg', self.authId)

    def checkMinGeoserverVersion(self, errors):
        """ Checks that the GeoServer instance we are dealing with is at least 2.13.2 """
        try:
            url = f"{self.apiUrl}/about/version.json"
            result = self.request(url).json()
        except RequestException:
            errors.add("Could not connect to Geoserver."
                       "Please check the server settings (including password).")
            return

        resources = result.get('about', {}).get('resource', {})

        try:
            ver = next((r["Version"] for r in resources if r["@name"] == 'GeoServer'), None)
            if ver is None:
                raise Exception('No GeoServer resource found or empty Version string')
            major, minor = semanticVersion(ver)
            if major < 2 or (major == 2 and minor <= 13):
                # GeoServer instance is too old (or bad)
                info_url = 'https://my.geocat.net/knowledgebase/100/Bridge-4-compatibility-with-Geoserver-2134-and-before.html'  # noqa
                errors.add(
                    f"Geoserver 2.14.0 or later is required, but the detected version is {ver}.\n"
                    f"Please refer to <a href='{info_url}'>this article</a> for more info."
                )
        except Exception as e:
            # Failed to retrieve Version. It could be a RC or dev version: warn but consider OK.
            self.logWarning(f"Failed to retrieve GeoServer version info: {e}")

    def validateBeforePublication(self, errors, to_publish, only_symbology):
        self.refreshWorkspaceName()
        if not self.workspace:
            errors.add("QGIS project must be saved before publishing layers to GeoServer.")
        elif self.workspace[0].isdigit() or self.workspace[0] in '.-_':
            errors.add("GeoServer workspace names may not start with a digit or .-_. "
                       "Please save QGIS project under a different name and retry.")
        if self.willDeleteLayersOnPublication(to_publish) and not only_symbology:
            ret = self.showQuestionBox("Workspace", f"A workspace named '{self.workspace}' "
                                                    f"already exists and contains layers that "
                                                    f"will be deleted.\nDo you wish to proceed?",
                                       buttons=self.BUTTONS.YES | self.BUTTONS.NO,
                                       defaultButton=self.BUTTONS.NO)
            if ret == self.BUTTONS.NO:
                errors.add("Cannot overwrite existing workspace.")
        self.checkMinGeoserverVersion(errors)

    @classmethod
    def getAlgorithmInstance(cls):
        return GeoserverAlgorithm()


class GeoserverAlgorithm(BridgeAlgorithm):

    INPUT = 'INPUT'
    URL = 'URL'
    WORKSPACE = 'WORKSPACE'
    AUTHID = 'AUTHID'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer(self.INPUT,
                                                         self.tr('Layer')))
        self.addParameter(QgsProcessingParameterString(self.URL,
                                                       self.tr('Server URL'), ''))
        self.addParameter(QgsProcessingParameterString(self.WORKSPACE,
                                                       self.tr('Workspace'), ''))
        self.addParameter(QgsProcessingParameterAuthConfig(self.AUTHID,
                                                           self.tr('Auth credentials')))

    def name(self):
        return 'publishtogeoserver'

    def displayName(self):
        return self.tr('Layer to GeoServer')

    def shortDescription(self):
        return self.tr('Publishes a layer (data and style) to a GeoServer instance')

    def processAlgorithm(self, parameters, context, feedback):
        url = self.parameterAsString(parameters, self.URL, context)
        authid = self.parameterAsString(parameters, self.AUTHID, context)
        workspace = self.parameterAsString(parameters, self.WORKSPACE, context)
        layer = self.parameterAsLayer(parameters, self.INPUT, context)

        feedback.pushInfo(f'Publishing {layer} and its style to GeoServer...')
        try:
            server = GeoserverServer(GeoserverServer.__name__, authid, url)
            server.forceWorkspace(workspace)
            server.publishStyle(layer)
            server.publishLayer(layer)
        except Exception as err:
            feedback.reportError(err, True)

        return {self.OUTPUT: True}
