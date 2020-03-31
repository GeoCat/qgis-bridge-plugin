import os
import psycopg2
import json
import webbrowser
from zipfile import ZipFile 
import sqlite3
import secrets

from requests.exceptions import ConnectionError

from qgis.core import QgsProject, QgsVectorLayer, QgsDataSourceUri

from qgis.PyQt.QtCore import QCoreApplication

from qgis.PyQt.QtWidgets import QMessageBox

from bridgestyle.qgis import saveLayerStyleAsZippedSld

from .exporter import exportLayer
from .serverbase import ServerBase
from ..utils.files import tempFilenameInTempFolder
from ..utils.services import addServicesForGeodataServer

class GeoserverServer(ServerBase):

    FILE_BASED = 0
    POSTGIS_MANAGED_BY_BRIDGE = 1
    POSTGIS_MANAGED_BY_GEOSERVER = 2

    def __init__(self, name, url="", authid="", storage=0, postgisdb=None, useOriginalDataSource=False):
        super().__init__()
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
        self.postgisdb = postgisdb
        self.useOriginalDataSource = useOriginalDataSource
        self._isMetadataCatalog = False
        self._isDataCatalog = True
        self._layersCache = {}

    @property
    def _workspace(self):
        path = QgsProject.instance().absoluteFilePath()
        if path:
            return os.path.splitext(os.path.basename(path))[0]
        else:
            return ""

    def prepareForPublishing(self, onlySymbology):
        if not onlySymbology:
            self.deleteWorkspace()
        self._ensureWorkspaceExists()
        self._uploadedDatasets = {}
        self._exportedLayers = {}
        self._postgisDatastoreExists = False

    def closePublishing(self):
        pass

    def publishStyle(self, layer):
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            self.logWarning(w)
        self.logInfo(QCoreApplication.translate("GeocatBridge", "Style for layer %s exported as zip file to %s")
                     % (layer.name(), styleFilename))
        self._publishStyle(layer.name(), styleFilename)
        return styleFilename

    def publishLayer(self, layer, fields=None):        
        self.publishStyle(layer)
        if layer.type() == layer.VectorLayer:
            if layer.featureCount() == 0:
                self.logError("Layer contains zero features and cannot be published")
                return

            if layer.dataProvider().name() == "postgres" and self.useOriginalDataSource:
                from .postgis import PostgisServer
                uri = QgsDataSourceUri(layer.source())
                db = PostgisServer("temp", uri.authConfigId(), uri.host(), uri.port(), uri.schema(), uri.database())
                self._publishVectorLayerFromPostgis(layer, db)
            elif self.storage in [self.FILE_BASED, self.POSTGIS_MANAGED_BY_GEOSERVER]:
                if layer.source() not in self._exportedLayers:
                    if self.storage == self.POSTGIS_MANAGED_BY_GEOSERVER:                    
                        path = exportLayer(layer, fields, toShapefile=True, force=True, log=self)
                        basename = os.path.splitext(path)[0]
                        zipfilename = basename + ".zip"
                        with ZipFile(zipfilename,'w') as z:
                            for ext in [".shp", ".shx", ".prj", ".dbf"]:
                                filetozip = basename + ext
                                z.write(filetozip, arcname=os.path.basename(filetozip))
                        self._exportedLayers[layer.source()] = zipfilename
                    else:
                        path = exportLayer(layer, fields, log=self)
                        self._exportedLayers[layer.source()] = path
                filename = self._exportedLayers[layer.source()]
                if self.storage == self.FILE_BASED:
                    self._publishVectorLayerFromFile(layer, filename)
                else:
                    self._publishVectorLayerFromFileToPostgis(layer, filename)
            elif self.storage == self.POSTGIS_MANAGED_BY_BRIDGE:            
                try:
                    from .servers import allServers
                    db = allServers()[self.postgisdb]
                except KeyError:
                    raise Exception(QCoreApplication.translate("GeocatBridge", "Cannot find the selected PostGIS database"))
                db.importLayer(layer, fields)                
                self._publishVectorLayerFromPostgis(layer, db)            
        elif layer.type() == layer.RasterLayer:
            if layer.source() not in self._exportedLayers:
                path = exportLayer(layer, fields, log=self)
                self._exportedLayers[layer.source()] = path
            filename = self._exportedLayers[layer.source()]
            self._publishRasterLayer(filename, layer.name())
        self._clearCache()

    def createPostgisDatastore(self):
        ws, name = self.postgisdb.split(":")
        if not self.datastoreExists(name):
            url = "%s/workspaces/%s/datastores/%s.json" % (self.url, ws, name)
            r = self.request(url)
            datastore = r.json()["dataStore"]
            newDatastore = {"dataStore":{"name": datastore["name"],
                                        "type": datastore["type"],
                                        "connectionParameters": datastore["connectionParameters"],
                                        "enabled": True}}            
            url = "%s/workspaces/%s/datastores" % (self.url, self._workspace)
            r = self.request(url, newDatastore, "post")

    def testConnection(self):
        try:
            url = "%s/about/version" % self.url
            self.request(url)
            return True
        except:
            return False

    def unpublishData(self, layer):
        self.deleteLayer(layer.name())
        self.deleteStyle(layer.name()) 

    def baseUrl(self):
        return "/".join(self.url.split("/")[:-1])

    def _publishVectorLayerFromFile(self, layer, filename):
        self.logInfo("Publishing layer from file: %s" % filename)
        name = layer.name()
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
        url = "%s/workspaces/%s/datastores/%s/featuretypes/%s.json" % (self.url, self._workspace, datasetName, geoserverLayerName)
        r = self.request(url)
        ft = r.json()
        ft["featureType"]["name"] = name
        ft["featureType"]["title"] = name
        ext = layer.extent()
        ft["featureType"]["nativeBoundingBox"] = {
            "minx": round(ext.xMinimum(), 5),
            "maxx": round(ext.xMaximum(), 5),
            "miny": round(ext.yMinimum(),5),
            "maxy": round(ext.yMaximum(), 5),
            "srs": layer.crs().authid()
        }
        if isDataUploaded:
            url = "%s/workspaces/%s/datastores/%s/featuretypes" % (self.url, self._workspace, datasetName)
            r = self.request(url, ft, "post")
        else:
            r = self.request(url, ft, "put")
        self.logInfo("Feature type correctly created from GPKG file '%s'" % filename)
        self._setLayerStyle(name, name)

    def _publishVectorLayerFromPostgis(self, layer, db):
        name = layer.name()
        username, password = db.getCredentials()
        def _entry(k, v):
            return {"@key":k, "$":v}
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
        self._setLayerStyle(name, name)

    def _publishVectorLayerFromFileToPostgis(self, layer, filename):
        self.logInfo("Publishing layer from file: %s" % filename)
        self.createPostgisDatastore()
        ws, datastoreName = self.postgisdb.split(":")
        name = layer.name()
        isDataUploaded = filename in self._uploadedDatasets        
        if not isDataUploaded:
            _import = {
              "import": {
                "targetStore": {
                  "dataStore": {
                    "name": datastoreName
                  }
                },
                "targetWorkspace": {
                  "workspace": {
                    "name": self._workspace
                  }
                }
              }
            }
            url = "%s/imports" % (self.url)
            ret = self.request(url, _import, "post")
            importId = ret.json()["import"]["id"]
            url = "%s/imports/%s/tasks" % (self.url, importId)
            with open(filename, "rb") as f:
                files = {os.path.basename(filename): f}
                ret = self.request(url, method="post", files=files)
            taskId = ret.json()["task"]["id"]
            target = {"dataStore": {
                        "name": datastoreName
                        }
                    }
            url = "%s/imports/%s/tasks/%s/target" % (self.url, importId, taskId)
            self.request(url, target, "put")
            url = "%s/imports/%s" % (self.url, importId)
            self.request(url, method="post")
            layername = os.path.splitext(os.path.basename(filename))[0]
            self._uploadedDatasets[filename] = (datastoreName, layername)
        datasetName, geoserverLayerName = self._uploadedDatasets[filename]
        url = "%s/workspaces/%s/datastores/%s/featuretypes/%s.json" % (self.url, self._workspace, datasetName, geoserverLayerName)
        r = self.request(url)
        ft = r.json()
        ft["featureType"]["name"] = name
        ft["featureType"]["title"] = name                
        try:
            ftUrl = "%s/workspaces/%s/datastores/%s/featuretypes" % (self.url, self._workspace, datasetName)
            r = self.request(ftpUrl, ft, "post")
        except:            
            r = self.request(url, ft, "put")
        self.logInfo("Feature type correctly created from GPKG file '%s'" % filename)
        self._setLayerStyle(name, name)

    def _publishRasterLayer(self, filename, layername):
        #feedback.setText("Publishing data for layer %s" % layername)
        self._ensureWorkspaceExists()
        with open(filename, "rb") as f:
            url = "%s/workspaces/%s/coveragestores/%s/file.geotiff" % (self.url, self._workspace, layername)
            self.request(url, f.read(), "put")
        self.logInfo("Feature type correctly created from Tiff file '%s'" % filename)
        self._setLayerStyle(layername, layername)

    def createGroups(self, groups):      
        for group in groups:
            self._publishGroup(group)

    def _publishGroup(self, group):
        layers = []
        for layer in group["layers"]:
            if isinstance(layer, dict):
                layers.append({"@type": "layerGroup", "name": "%s:%s" % (self._workspace, layer["name"])})
                self._publishGroup(layer)
            else:
                layers.append({"@type": "layer", "name": "%s:%s" % (self._workspace, layer)})

        groupdef = {"layerGroup":{"name": group["name"],
                                "title": group["title"],
                                "abstractTxt": group["abstract"],
                                "mode":"NAMED",
                                "publishables": {"published":layers}}}
        
        url = "%s/workspaces/%s/layergroups" % (self.url, self._workspace)
        try:
            self.request(url, groupdef, "post")
        except:
            self.request(url, groupdef, "put")

        self.logInfo("Group %s correctly created" % group["name"])

    def deleteStyle(self, name):
        if self.styleExists(name):
            url = "%s/workspaces/%s/styles/%s?purge=true&recurse=true" % (self.url, self._workspace, name)        
            r = self.request(url, method="delete")

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
        url = "%s/workspaces.json" % (self.url)
        return self._exists(url, "workspace", self._workspace)

    def willDeleteLayersOnPublication(self, toPublish):

        if self.workspaceExists():
            print(3)
            layers = self.layers()
            toDelete = list(set(layers) - set(toPublish))
            print(layers)
            print(toPublish)
            print(toDelete)
            return bool(toDelete)
        else:
            return False



    def datastoreExists(self, name):
        url = "%s/workspaces%s/datastores.json" % (self.url, self._workspace)
        return self._exists(url, "dataStore", name)

    def _deleteDatastore(self, name):
        url = "%s/workspaces/%s/datastores/%s?recurse=true" % (self.url, self._workspace, name)
        try:
            r = self.request(url, method="delete")            
        except:
            pass

    def deleteLayer(self, name, recurse=True):
        if self.layerExists(name):
            recurseParam = 'recurse=true' if recurse else ""
            url = "%s/workspaces/%s/layers/%s.json?%s" % (self.url, self._workspace, name, recurseParam)
            r = self.request(url, method="delete")
        
    def openPreview(self, names, bbox, srs):
        url = self.layerPreviewUrl(names, bbox, srs)
        webbrowser.open_new_tab(url)

    def layerPreviewUrl(self, names, bbox, srs):
        baseurl = self.baseUrl()
        names = ",".join(["%s:%s" % (self._workspace, name) for name in names])
        url = ("%s/%s/wms?service=WMS&version=1.1.0&request=GetMap&layers=%s&format=application/openlayers&bbox=%s&srs=%s&width=800&height=600" 
                    % (baseurl, self._workspace, names, bbox, srs))
        return url

    def layerWmsUrl(self, name, forPreview = True):
        request = "GetMap" if forPreview else "GetCapabilities"
        return "%s/%s/wms?service=WMS&version=1.1.0&request=%s&layers=%s"% (self.baseUrl(), self._workspace, request, name)        
        
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
        r = self.request(resourceUrl, data=layer, method="put")

    def deleteWorkspace(self):
        if self.workspaceExists():
            url = "%s/workspaces/%s?recurse=true" % (self.url, self._workspace)
            r = self.request(url, method="delete")
            self._clearCache()

    def _publishStyle(self, name, styleFilename):
        #feedback.setText("Publishing style for layer %s" % name)
        self._ensureWorkspaceExists()
        styleExists = self.styleExists(name)
        headers = {'Content-type': 'application/zip'}
        if styleExists:
            method = "put"
            url = self.url + "/workspaces/%s/styles/%s" % (self._workspace, name)
        else:
            url = self.url + "/workspaces/%s/styles?name=%s" % (self._workspace, name)
            method = "post"
        with open(styleFilename, "rb") as f:
            self.request(url, f.read(), method, headers)
        self.logInfo(QCoreApplication.translate("GeocatBridge", "Style %s correctly created from Zip file '%s'"
                     % (name, styleFilename)))

    def _setLayerStyle(self, layername, stylename):
        url = "%s/workspaces/%s/layers/%s.json" % (self.url, self._workspace, layername)        
        r = self.request(url)
        layer = r.json()
        styleUrl = "%s/workspaces/%s/styles/%s.json" % (self.url, self._workspace, stylename)
        layer["layer"]["defaultStyle"] = {
                    "name": stylename,
                    "href": styleUrl
                }
        r = self.request(url, data=layer, method="put")

    def _ensureWorkspaceExists(self):        
        if not self.workspaceExists():
            url = "%s/workspaces" % self.url
            ws = {"workspace": {"name": self._workspace}}
            self.request(url, data=ws, method="post")
            
    def postgisDatastores(self):
        url = "%s/workspaces.json" % (self.url)
        r = self.request(url)
        root = r.json()["workspaces"]
        if "workspace" in root:
            wss = [s["name"] for s in root["workspace"]]
        else:
            wss = []
        datastores = []
        for ws in wss:
            url = "%s/workspaces/%s/datastores.json" % (self.url, ws)            
            r = self.request(url)
            root = r.json()["dataStores"]
            if "dataStore" in root:
                for datastore in root["dataStore"]:
                    url = "%s/workspaces/%s/datastores/%s.json" % (self.url, ws, datastore["name"])
                    r = self.request(url)
                    datastoreJson = r.json()                    
                    if datastoreJson["dataStore"].get("type", None) == "PostGIS":
                        datastores.append("%s:%s" % (ws, datastore["name"]))
        return datastores
        
    def addPostgisDatastore(self, datastoreDef):        
        url = "%s/workspaces/%s/datastores/" % (self.url, self._workspace)
        self.request(url, data=datastoreDef, method="post")

    def addOGCServers(self):
        baseurl = "/".join(self.url.split("/")[:-1])
        addServicesForGeodataServer(self.name, baseurl, self.authid)

    # ensure that the geoserver we are dealing with is at least 2.13.2
    def checkMinGeoserverVersion(self,errors):
        try:
            url = "%s/about/version.json" % self.url
            result = self.request(url).json()['about']['resource']
        except:            
            errors.add("Could not connect to Geoserver.  Please check the server settings (including password).")
            return
        try:
            ver = next((x["Version"] for x in result if x["@name"]=='GeoServer'), None)
            if ver is None:
                return # couldnt find version -- dev GS, lets say its ok      
            ver_major,ver_minor,ver_patch = ver.split('.')
            
            if int(ver_minor) <= 13: # old
                errors.add("Geoserver 2.14.0 or later is required.  Selected Geoserver is version '" + ver + "'.  Please see <a href='https://my.geocat.net/knowledgebase/100/Bridge-4-compatibility-with-Geoserver-2134-and-before.html'>Bridge 4 Compatibility with Geoserver 2.13.4 and before</a>")
        except:
            #version format might not be the expected. This is usually a RC or dev version, so we consider it ok
            pass

    def validateGeodataBeforePublication(self, errors, toPublish):
        path = QgsProject.instance().absoluteFilePath()
        if not path:
            errors.add("QGIS Project is not saved. Project must be saved before publishing layers to GeoServer")
        if "." in self._workspace:
            errors.add("QGIS project name contains unsupported characters ('.'). Save with a different name and try again")
        if self.willDeleteLayersOnPublication(toPublish):
            ret = QMessageBox.question(None, "Workspace",
                                "A workspace with that name exists and contains layers that are not going to be published.\nThose layers will be deleted.\nDo you want to proceed?",
                                QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                errors.add("Cannot overwrite existing workspace")
        self.checkMinGeoserverVersion(errors)

