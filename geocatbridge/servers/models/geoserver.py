import json
import os
from typing import List, Iterable, Dict
from zipfile import ZipFile

from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice, QSettings
from qgis.core import (
    QgsProject,
    QgsProcessingParameterMapLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterAuthConfig
)
from requests.exceptions import HTTPError, RequestException

from geocatbridge.publish.style import (
    saveLayerStyleAsZippedSld, layerStyleAsMapboxFolder, convertMapboxGroup
)
from geocatbridge.process.algorithm import BridgeAlgorithm
from geocatbridge.publish.export import exportVector, exportRaster
from geocatbridge.servers import manager
from geocatbridge.servers.bases import DataCatalogServerBase
from geocatbridge.servers.models.gs_storage import GeoserverStorage
from geocatbridge.servers.views.geoserver import GeoServerWidget
from geocatbridge.utils import strings
from geocatbridge.utils.files import tempFileInSubFolder, tempSubFolder, Path, getResourcePath
from geocatbridge.utils.meta import getAppName, semanticVersion
from geocatbridge.utils.network import TESTCON_TIMEOUT
from geocatbridge.utils.layers import (
    BridgeLayer, LayerGroups, LayerGroup, listBridgeLayers, layerById, listLayerNames
)


class GeoserverServer(DataCatalogServerBase):
    storage: GeoserverStorage = GeoserverStorage.FILE_BASED
    postgisdb: str = None
    useOriginalDataSource: bool = False
    useVectorTiles: bool = False

    def __init__(self, name, authid="", url="", **options):
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
        super().__init__(name, authid, url, **options)
        self._workspace = None
        self._slug_map = {}     # maps requested layer name (slug) to the resulting server name
        self._apiurl = self.fixRestApiUrl()

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

    def workspaceFromProject(self):
        """ Returns the workspace name derived from the QGIS Project path. """
        path = QgsProject().instance().absoluteFilePath()
        if path:
            return Path(path).stem
        self.logWarning("Workspace name could not be derived from QGIS project path: please save the project")

    def refreshWorkspaceName(self) -> bool:
        """ Resets the QGIS Project (file) name. Can be `None` if not found/saved. """
        self._workspace = None
        name = self.workspaceFromProject()
        if name and strings.validate(name, first_alpha=True, allowed_chars=strings.WORKSPACE_CHARS):
            self._workspace = name
            return True
        return False

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

    def prepareForPublishing(self, only_symbology: bool):
        if not only_symbology:
            self.clearWorkspace()
        self._ensureWorkspaceExists()

    def closePublishing(self, layer_ids: Iterable[str]):
        """ Called after all layers and layer groups were published successfully.
        For GeoServer, this step finalizes the Mapbox VT export process, if this was enabled.
        """
        if not self.useVectorTiles:
            return

        warnings = set()
        tmp_dir = tempSubFolder()
        self.logInfo(f"Creating layer styles for Mapbox vector tiles in {tmp_dir}...")

        # Export layers to temp folder
        for lyr_id in layer_ids:
            layer = layerById(lyr_id)
            if not layer:
                continue
            # Make temporary layer clone and set web slug as name (for bridgestyle export)
            layer_clone = layer.clone()
            layer_clone.setName(layer.web_slug)
            warnings.update(layerStyleAsMapboxFolder(layer_clone, tmp_dir))

        # Log warnings, if any
        for w in warnings:
            self.logWarning(w)

        self.logInfo(f"Editing temporary Mapbox files...")
        self._editMapboxFiles(tmp_dir)

        self.logInfo(f"Publishing Mapbox styles...")
        self.publishMapboxGLStyle(tmp_dir)

        self.logInfo(f"Publishing OpenLayers vector tile preview...")
        self._publishOpenLayersPreview(tmp_dir)
        self.logInfo(f"Finished MapBox VT publish process")

    @staticmethod
    def featureTypeProps(layer: BridgeLayer, bounding_box: bool = False, **kwargs) -> dict:
        """ Extracts name, title, abstract and keywords from the given layer and creates
        a JSON dictionary that can be used for GeoServer featuretype/coverage `PUT` requests.

        :param layer:           The layer for which to collect properties.
        :param bounding_box:    If True, a `nativeBoundingBox` property will also be added.
        """
        props = {
            "name": layer.web_slug,
            "title": layer.title() or layer.name(),
            "abstract": layer.abstract(),
            "keywords": {
                "string": layer.keywords()
            }
        }
        if bounding_box:
            ext = layer.extent()
            props["nativeBoundingBox"] = {
                "minx": round(ext.xMinimum(), 5),
                "maxx": round(ext.xMaximum(), 5),
                "miny": round(ext.yMinimum(), 5),
                "maxy": round(ext.yMaximum(), 5),
                "crs": layer.crs().authid()
            }
        props.update(**kwargs)
        return {
            "featureType": props
        }

    def _publishOpenLayersPreview(self, folder):
        style_filename = os.path.join(folder, "style.mapbox")
        with open(style_filename) as f:
            style = f.read()
        template = f"var style = {style};\nvar map = olms.apply('map', style);"

        js_filename = os.path.join(folder, "mapbox.js")
        with open(js_filename, "w") as f:
            f.write(template)

        html = getResourcePath("openlayers/index.html")
        self.uploadResource(f"{self.workspace}/index.html", html)
        self.uploadResource(f"{self.workspace}/mapbox.js", js_filename)

    def uploadResource(self, path, file):
        url = f"{self.apiUrl}/resource/{path}"
        with open(file) as f:
            self.request(url, "put", f.read())

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

    def vectorLayersAsShp(self) -> bool:
        # When GeoServer imports to PostGIS using the Importer extension, we require a Shapefile
        return self.storage == GeoserverStorage.POSTGIS_GEOSERVER

    def publishStyle(self, layer: BridgeLayer):
        style_file = tempFileInSubFolder(layer.file_slug + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, style_file)
        for w in warnings:
            self.logWarning(w)
        self.logInfo(f"Style for layer '{layer.name()}' exported as ZIP file to '{style_file}'")
        self._publishStyle(layer.web_slug, style_file)
        return style_file

    def publishLayer(self, layer: BridgeLayer, fields: List[str] = None):
        if layer.is_vector:
            # Export vector layer
            if layer.featureCount() == 0:
                self.logWarning(f"Layer '{layer.name()}' contains no features and will not be published")
                return

            if layer.is_postgis_based and self.useOriginalDataSource:
                # Reference existing PostGIS table (must have direct access)
                try:
                    from geocatbridge.servers.models.postgis import PostgisServer
                except (ImportError, ModuleNotFoundError, NameError):
                    raise Exception(self.translate(getAppName(), "Cannot find or import PostgisServer class"))
                else:
                    db = PostgisServer(
                        "temp",
                        layer.uri.authConfigId(),
                        host=layer.uri.host(),
                        port=layer.uri.port(),
                        schema=layer.uri.schema(),
                        database=layer.uri.database()
                    )
                    self._publishVectorLayerFromPostgis(layer, db)

            elif self.storage == GeoserverStorage.POSTGIS_BRIDGE:
                # Export to PostGIS table (must have direct access)
                db = manager.getServer(self.postgisdb)
                if not db:
                    raise Exception(self.translate(getAppName(), "Cannot find the selected PostGIS database"))
                db.importLayer(layer, fields)
                self._publishVectorLayerFromPostgis(layer, db)

            elif self.storage == GeoserverStorage.POSTGIS_GEOSERVER:
                # Export layer to Shapefile and publish to PostGIS using GeoServer Importer extension
                self._publishVectorLayerFromShpToPostgis(layer, fields)

            elif self.storage == GeoserverStorage.FILE_BASED:
                # Export layer to GeoPackage datastore
                self._publishVectorLayerFromGeoPackage(layer, fields)

        elif layer.is_raster:
            # Publish GeoTIFF
            self._publishRasterLayer(layer)

        self._clearCache()

    def _getPostgisDatastores(self, ds_list_url: str = None):
        """
        Finds all PostGIS datastores for a certain workspace (typically only 1).
        If `ds_list_url` is not specified, the first PostGIS datastore for the current workspace is returned.
        Otherwise, `ds_list_url` should be the datastores REST endpoint to a specific workspace.

        :param ds_list_url:         REST URL that returns a list of datastores for a specific workspace.
        :returns:                   A generator with PostGIS datastore names.
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

    def createPostgisDatastore(self) -> str:
        """
        Creates a new datastore based on the selected one in the Server widget
        if the workspace is created from scratch.

        :returns:   The existing or created PostGIS datastore name (which equals the workspace name).
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

    def _publishVectorLayerFromGeoPackage(self, layer: BridgeLayer, fields: List[str]):
        """
        Publishes the given layer to a GeoPackage (file-based) GeoServer datastore.

        :param layer:   Vector layer to publish.
        :param fields:  Field names to export.
        """
        gpkg_path = exportVector(layer, fields)
        if not gpkg_path:
            return

        # Upload GeoPackage and create (overwrite) datastore
        ds_name = layer.web_slug
        self._deleteDatastore(ds_name)
        with open(gpkg_path, "rb") as f:
            url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{ds_name}/file.gpkg?update=overwrite"
            try:
                self.request(url, "put", f.read())
            except Exception as err:
                return self.logError(f"Failed to create datastore {ds_name} from {gpkg_path}: {err}")

        # Make GeoPackage datastore readonly (huge performance boost!)
        try:
            url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{ds_name}.json"
            body = self.request(url).json()
            entries = body.get("dataStore", {}).get("connectionParameters", {}).get("entry", [])
            entry_dict = {e["@key"]: e["$"] for e in entries}
            if "read_only" not in entry_dict:
                entries.append(self._connectionParamEntry("read_only", "true"))
                body = {
                    "dataStore": {
                        "connectionParameters": {
                            "entry": entries
                        }
                    }
                }
                self.request(url, "put", body)
        except Exception as err:
            self.logWarning(f"Failed to set read_only property of datastore {ds_name}: {err}")

        # Get the created feature type for the current layer
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{ds_name}/featuretypes/{ds_name}.json"
        try:
            self.request(url).json()
        except Exception as err:
            return self.logError(f"Feature type {ds_name} was not found: {err}")

        # Modify the feature type
        ft = self.featureTypeProps(layer, bounding_box=True)
        try:
            self.request(url, "put", ft)
        except Exception as err:
            return self.logError(f"Failed to update feature type {layer.web_slug} in datastore {ds_name}: {err}")
        else:
            self.logInfo(f"Successfully created feature type from GeoPackage file '{gpkg_path}'")

        # Link style to layer
        self._setLayerStyle(layer.web_slug)

    def _publishVectorLayerFromShpToPostgis(self, layer: BridgeLayer, fields: List[str]):
        """
        Publishes the given vector layer to PostGIS using the GeoServer Importer extension.
        The Importer extension expects a zipped Shapefile as input.
        """
        # First export layer data to a zipped Shapefile
        shp_file = exportVector(layer, fields, force_shp=True)
        zip_file = shp_file.with_suffix('.zip')
        with ZipFile(zip_file, 'w') as z:
            for ext in (".shp", ".shx", ".prj", ".dbf"):
                z.write(shp_file.with_suffix(ext))

        # Get/create datastore
        datastore = self.createPostgisDatastore()

        # Create a new import and retrieve its ID
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
        try:
            import_id = self.request(url, "post", body).json()["import"]["id"]
        except Exception as err:
            return self.logError(f"Failed to create GeoServer Importer job: {err}")

        # Create a new task, upload ZIP, and return task ID
        self.logInfo(f"Uploading data from layer '{layer.name()}' as zipped Shapefile '{zip_file}'...")
        url = f"{self.apiUrl}/imports/{import_id}/tasks"
        try:
            with open(zip_file, "rb") as f:
                task_id = self.request(url, method="post", files={
                    zip_file.name: (zip_file.name, f, 'application/octet-stream')
                }).json()["task"]["id"]
        except Exception as err:
            return self.logError(f"Failed to initiate GeoServer Importer task: {err}")

        # Reassign PostGIS datastore as target (was reset to Shapefile by upload)
        body = {
            "dataStore": {
                "name": datastore
            }
        }
        url = f"{self.apiUrl}/imports/{import_id}/tasks/{task_id}/target.json"
        self.request(url, "put", body)

        # Start import execution
        self.logInfo(f"Starting Importer task for layer '{layer.name()}'...")
        url = f"{self.apiUrl}/imports/{import_id}"
        self.request(url, method="post")

        # Get the import result (error message and target layer name)
        import_err, given_name = self._getImportResult(import_id, task_id)
        if import_err:
            return self.logError(f"Failed to publish QGIS layer '{layer.name()}'.\n\n{import_err}")

        # Get the created feature type
        self.logInfo("Checking if feature type creation was successful...")
        url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{datastore}/featuretypes/{given_name}.json"
        try:
            self.request(url + "?quietOnNotFound=true")
        except RequestException as e:
            # Something unexpected happened: failure cannot be retrieved from import task,
            # so the user should check the GeoServer logs to find out what caused it.
            if isinstance(e, HTTPError) and e.response.status_code == 404:
                return self.logError(f"Failed to publish QGIS layer '{layer.name()}' as '{given_name}' "
                                     f"due to an unknown error.\nPlease check the GeoServer logs.")
            raise

        # Modify the feature type descriptions, but leave the name intact to avoid DB schema mismatches
        self.logInfo("Fixing feature type properties...")
        ft = self.featureTypeProps(layer, nativeName=layer.web_slug)  # reset original name used for the upload
        self.request(url, "put", ft)

        self.logInfo(f"Successfully created feature type from file '{shp_file}'")
        self._slug_map[layer.web_slug] = given_name

        # Fix layer style reference and remove unwanted global style
        self.logInfo("Performing style cleanup...")
        try:
            self._fixLayerStyle(given_name, layer.web_slug)
        except RequestException as e:
            self.logWarning(f"Failed to clean up layer styles: {e}")
        else:
            self.logInfo(f"Successfully published layer '{layer.name()}'")

    def _publishVectorLayerFromPostgis(self, layer: BridgeLayer, db):
        """ Creates a datastore and feature type for the given PostGIS layer and DB connection on GeoServer. """
        username, password = db.getCredentials()

        ds = {
            "dataStore": {
                "name": layer.web_slug,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "entry": [
                        self._connectionParamEntry("schema", db.schema),
                        self._connectionParamEntry("port", str(db.port)),
                        self._connectionParamEntry("database", db.database),
                        self._connectionParamEntry("passwd", password),
                        self._connectionParamEntry("user", username),
                        self._connectionParamEntry("host", db.host),
                        self._connectionParamEntry("dbtype", "postgis")
                    ]
                }
            }
        }
        ds_url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores"
        self.request(ds_url, data=ds, method="post")

        ft = self.featureTypeProps(layer, srs=layer.crs().authid())
        ft_url = f"{self.apiUrl}/workspaces/{self.workspace}/datastores/{layer.web_slug}/featuretypes"
        self.request(ft_url, data=ft, method="post")

        self._setLayerStyle(layer.web_slug)

    def _publishRasterLayer(self, layer: BridgeLayer):
        self._ensureWorkspaceExists()

        # Export to GeoTIFF
        filename = exportRaster(layer)

        # Upload the TIFF
        try:
            with open(filename, "rb") as f:
                url = f"{self.apiUrl}/workspaces/{self.workspace}/coveragestores/" \
                      f"{layer.web_slug}/file.geotiff?coverageName={layer.web_slug}"
                self.request(url, "put", f.read())
        except Exception as e:
            return self.logError(f"Failed to create coverage from TIFF file '{filename}': {e}")

        self.logInfo(f"Successfully created coverage from TIFF file '{filename}'")
        self._setLayerStyle(layer.web_slug)

    def _getImportResult(self, import_id, task_id):
        """ Get the error message on the import task (if any) and the resulting layer name. """
        task = self.request(f"{self.apiUrl}/imports/{import_id}/tasks/{task_id}").json()["task"] or {}
        err_msg = task.get("errorMessage", "")
        if err_msg:
            err_msg = f"GeoServer Importer Extension error: {err_msg}"
        return err_msg, task["layer"]["name"]

    @staticmethod
    def _connectionParamEntry(key, value):
        """ Creates a connection parameter JSON entry for datastore configurations. """
        return {"@key": key, "$": value}

    def createGroups(self, layer_ids: Iterable[str]):
        """ Publishes layer groups for all published layers that participate in one.

        :param layer_ids:   List of ID's of all QGIS layers that were published.
        """
        lookup = {self._slug_map.get(lyr.web_slug, lyr.web_slug): lyr for lyr in listBridgeLayers(layer_ids)}
        for group in LayerGroups(layer_ids, self._slug_map):
            self._publishGroup(group, lookup)

    def _publishGroupMapBox(self, group: LayerGroup, lookup: Dict[str, BridgeLayer]):
        """ Publishes layer group as a MapBox VT style. """

        def getImageBytes(img) -> bytes:
            """ Reads bytes from PNG sprite sheets. """
            ba = QByteArray()
            buff = QBuffer(ba)
            buff.open(QIODevice.WriteOnly)
            img.save(buff, "png")
            return ba.data()

        # Get suitable layer lookup for bridgestyle (filter out nested group layers!)
        published_layers = {name: lyr for name, lyr in lookup.items() if name in group.layers}

        # Compute actual style
        mb_style, warnings, sprite_sheet = convertMapboxGroup(group, published_layers, self.apiUrl, self.workspace)
        for warning in warnings:
            self.logWarning(warning)

        # Delete Mapbox style (if it exists)
        self._ensureWorkspaceExists()
        if not self.deleteStyle(group.name):
            raise Exception(f"failed to (re)publish Mapbox style '{group.name}'")

        # Publish Mapbox style to GeoServer
        xml = f"""<style>
                     <name>{group.name}</name>
                     <workspace>{self.workspace}</workspace>
                     <format>mbstyle</format>
                     <filename>{group.name}.json</filename>
                   </style>"""
        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles"
        self.request(url, "post", xml, headers={"Content-Type": "text/xml"})

        # Write style JSON
        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{group.name}?raw=true"
        headers = {"Content-Type": "application/vnd.geoserver.mbstyle+json"}
        self.request(url, "put", mb_style, headers=headers)

        if not sprite_sheet:
            return

        # Publish sprite sheet data, if present
        try:
            img_bytes = getImageBytes(sprite_sheet["img"])
            img2x_bytes = getImageBytes(sprite_sheet["img2x"])
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet.png"
            self.request(url, "put", img_bytes)
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet@2x.png"
            self.request(url, "put", img2x_bytes)
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet.json"
            self.request(url, "put", sprite_sheet["json"])
            url = f"{self.apiUrl}/resource/workspaces/{self.workspace}/styles/spriteSheet@2x.json"
            self.request(url, "put", sprite_sheet["json2x"])
        except Exception as err:
            self.logError(f"Failed to upload sprite sheet(s) for Mapbox style '{group.name}': {err}")

    def _publishGroup(self, group: LayerGroup, lookup: Dict[str, BridgeLayer]):
        """ Publishes the given layer group to GeoServer. Also sets up Mapbox VT groups if needed.

        :param group:   The LayerGroup definition to publish.
        :param lookup:  Lookup dictionary of layer name (slug) and BridgeLayer object.
        """

        mb_continue = True
        if self.useVectorTiles:
            try:
                self._publishGroupMapBox(group, lookup)
            except Exception as err:
                self.logError(err)
                mb_continue = False

        layer_objs = []
        for child in group.layers:
            if isinstance(child, LayerGroup):
                layer_objs.append({
                    "@type": "layerGroup",
                    "name": f"{self.workspace}:{child.name}"
                })
                # Create a separate layer group for each nested layer group
                self._publishGroup(child, lookup)
            else:
                layer_objs.append({
                    "@type": "layer",
                    "name": f"{self.workspace}:{child}"}
                )

        groupdef = {
            "layerGroup": {
                "name": group.name,
                "title": group.title,
                "abstractTxt": group.abstract,
                "mode": "NAMED",
                "publishables": {
                    "published": layer_objs
                }
            }
        }

        url = f"{self.apiUrl}/workspaces/{self.workspace}/layergroups.json"
        try:
            self.request(f'{url}/{group.name}', method="delete")  # delete if it exists
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

        # Make sure there is VT format tiling for this group
        if self.useVectorTiles and mb_continue:
            url = f"{self.baseUrl}/gwc/rest/layers/{self.workspace}:{group.name}.xml"
            r = self.request(url)
            xml = r.text
            if "application/vnd.mapbox-vector-tile" not in xml:
                xml = xml.replace("<mimeFormats>", "<mimeFormats><string>application/vnd.mapbox-vector-tile</string>")
                self.request(url, "put", xml, headers={"Content-Type": "text/xml"})

        self.logInfo(f"Successfully created GeoServer layergroup '{group.name}'")

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
        self._slug_map = {}

    def _exists(self, url: str, category: str, name: str) -> bool:
        """
        Checks if the given object of 'category' with 'name' exists on the remote server.

        :param url:         The REST API endpoint to use for the check.
        :param category:    The GeoServer object category to check (e.g. datastore, layer, workspace, etc.).
        :param name:        The object name to verify.
        :return:
        """
        try:
            r = self.request(url)
            root = r.json().get(f"{category}s", {}) or {}  # make plural
            return name in frozenset(s["name"] for s in root.get(category, []))
        except Exception as err:
            # Non-200 response, bad JSON or no "name" property in object
            self.logError(err)
            return False

    def layerExists(self, name: str) -> bool:
        """ Checks if a layer with the given name exists on the server.
        The name is used 'as-is': no smart lookups are performed! """
        if not self.workspace:
            return False
        return self._exists(f"{self.apiUrl}/workspaces/{self.workspace}/layers.json", 'layer', name)

    def layerNames(self) -> Dict[str, str]:
        """ Returns a lookup dictionary of the local layer name (slug) and the remote layer name.

        For GeoServer-managed PostGIS datastores, the remote name may have a numeric suffix and will be matched to
        the local name. In all other cases, the local and the remote name will be the same.

        Remote names on the server that cannot be mapped to a local name will not be included in the result.
        """
        if not self.workspace:
            return {}

        # Retrieve all layers in the workspace
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers.json"
        try:
            layers = self.request(url).json()["layers"] or {}
        except Exception as err:
            self.logError(f"Failed to retrieve layers from workspace {self.workspace}: {err}")
            return {}

        # Get reversed lookup for published layer slugs
        reversed_map = {rem: loc for loc, rem in self._slug_map.items()}

        # Try and match remote names to local names
        local_slugs = frozenset(listLayerNames())
        output = {}
        for lyr in layers.get("layer", []):
            remote_slug = lyr["name"]

            if remote_slug in local_slugs:
                # Remote and local slug are identical
                output[remote_slug] = remote_slug
                continue

            local_slug = reversed_map.get(remote_slug)
            if local_slug:
                # Layer was published before and name was changed during publication (GeoServer-managed PostGIS)
                output[remote_slug] = local_slug
                continue

            # Check if remote slug exists locally, but has a numeric suffix: map local name to remote
            for slug in local_slugs:
                if remote_slug.replace(slug, '').isdigit():
                    output[slug] = remote_slug
                    break

            # No match found, do not include layer in result

        return output

    def styleExists(self, name: str):
        if not self.workspace:
            return False
        url = f"{self.apiUrl}/workspaces/{self.workspace}/styles.json"
        return self._exists(url, "style", name)

    def workspaceExists(self):
        if not self.workspace:
            return False
        url = f"{self.apiUrl}/workspaces.json"
        return self._exists(url, "workspace", self.workspace)

    def willDeleteLayersOnPublication(self, to_publish: List[str]):
        """ Checks if any of the layer names of the given QGIS layer IDs already exist on the server workspace. """
        if self.workspaceExists():
            # If the set of selected QGIS layers is NOT disjoint with the layers on the server, layers will be deleted!
            return not frozenset(listLayerNames(to_publish)).isdisjoint(self.layerNames().keys())
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
        verified_name = self.layerNames().get(name)
        if not verified_name:
            return True
        url = f"{self.apiUrl}/workspaces/{self.workspace}/layers/{verified_name}.json?recurse=true"
        try:
            self.request(url, method="delete")
        except RequestException as e:
            self.logError(f"Failed to delete layer '{name}': {e}")
            return False
        return True

    def getPreviewUrl(self, layer_names, bbox, srs):
        lookup = self.layerNames()
        names = ",".join([f"{self.workspace}:{lookup.get(name)}" for name in layer_names if name in lookup])
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
                    "metadataType": "ISO19115:2003",  # TODO: metadata type may be different
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
                params_json = json.dumps(params)
                # if any(entry["@key"] == "dbtype" for entry in params.get("entry", [])):
                if 'dbtype' in params_json and 'postgis' in params_json:
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
            url = f"{self.apiUrl}/namespaces/{self.workspace}.json"
            try:
                ns = self.request(url).json()
            except HTTPError as err:
                if err.response.status_code == 404:
                    self.logWarning(f"GeoServer namespace '{self.workspace}' does not exist")
                return False
            except RequestException as err:
                self.logError(f"Failed to query GeoServer namespace {self.workspace}: {err}")
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

    def _setLayerStyle(self, name: str, style_name: str = None) -> dict:
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
        old_style = dict(layer_def["layer"].get("defaultStyle", {}))
        style_url = f"{self.apiUrl}/workspaces/{self.workspace}/styles/{style_name}.json"
        layer_def["layer"]["defaultStyle"] = {
            "name": f"{self.workspace}:{style_name}",
            "workspace": self.workspace,
            "href": style_url
        }
        try:
            self.request(url, "put", layer_def)
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
        except json.JSONDecodeError:
            self.logWarning(f"GeoServer instance at {self.apiUrl} did not return a valid JSON response")
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

    def validateBeforePublication(self, errors: set, layer_ids: List[str], only_symbology: bool):
        if not self.refreshWorkspaceName():
            errors.add("QGIS project must be saved before publishing layers to GeoServer.\n"
                       "Project name preferably is ASCII only, starts with a letter, and consists of letters, numbers, or .-_")  # noqa
        elif self.willDeleteLayersOnPublication(layer_ids) and not only_symbology:
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

    def name(self):  # noqa
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
