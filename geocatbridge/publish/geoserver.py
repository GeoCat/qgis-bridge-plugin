import os
import psycopg2
import json
import webbrowser

import sqlite3

from requests.exceptions import ConnectionError

from qgis.core import QgsProject, QgsVectorLayer

from qgis.PyQt.QtCore import QCoreApplication

from bridgestyle.qgis import saveLayerStyleAsZippedSld

from .exporter import exportLayer
from .serverbase import ServerBase
from ..utils.files import tempFilenameInTempFolder


class GeoserverServer(ServerBase):

    UPLOAD_DATA = 0
    STORE_IN_POSTGIS = 1

    def __init__(self, name, url="", authid="", storage=0, workspace="", postgisdb=None):
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
        self.workspace = workspace
        self.postgisdb = postgisdb
        self._isMetadataCatalog = False
        self._isDataCatalog = True
        user, password = self.getCredentials()
        self.setupForProject()

    def setupForProject(self):
        if self.workspace is None:
            self._workspace = os.path.splitext(os.path.basename(
                                QgsProject.instance().absoluteFilePath()))[0]
        else:
            self._workspace = self.workspace
    
    def prepareForPublishing(self, onlySymbology):
        self.setupForProject()
        if self.workspace is None and not onlySymbology:
            self.deleteWorkspace()

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

    def publishLayer(self, layer, fields=None):
        self.publishStyle(layer)
        styleFilename = tempFilenameInTempFolder(layer.name() + ".zip")
        warnings = saveLayerStyleAsZippedSld(layer, styleFilename)
        for w in warnings:
            self.logWarning(w, 'GeoCat Bridge')
        self.logInfo(QCoreApplication.translate("GeocatBridge", "Style for layer %s exported as zip file to %s")
                     % (layer.name(), styleFilename))        
        if layer.type() == layer.VectorLayer:
            if self.storage == self.UPLOAD_DATA:
                filename = exportLayer(layer, fields, log = self)
                self._publishVectorLayerFromFile(filename, layer.name(), layer.crs().authid(), styleFilename, layer.name())
            else:
                try:
                    from .servers import allServers
                    db = allServers()[self.postgisdb]
                except KeyError:
                    raise Exception(QCoreApplication.translate("GeocatBridge", "Cannot find the selected PostGIS database"))
                db.importLayer(layer, fields)                
                self._publishVectorLayerFromPostgis(db, layer.crs().authid(), 
                                        layer.name(), styleFilename, layer.name())
        elif layer.type() == layer.RasterLayer:
            filename = exportLayer(layer, fields, log = self)            
            self._publishRasterLayer(filename, styleFilename, layer.name(), layer.name())

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

    def _publishVectorLayerFromFile(self, filename, layername, crsauthid, style, stylename):
        self.logInfo("Publishing layer from file: %s" % filename)
        self._ensureWorkspaceExists()
        self.deleteLayer(layername)
        self._publishStyle(stylename, style)
        #feedback.setText("Publishing data for layer %s" % layername)
        with open(filename, "rb") as f:
            url = "%s/workspaces/%s/datastores/%s/file.gpkg?update=overwrite" % (self.url, self._workspace, layername)
            self.request(url, f.read(), "put")
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM gpkg_geometry_columns")
        tablename = cursor.fetchall()[0][0]
        url = "%s/workspaces/%s/datastores/%s/featuretypes/%s.json" % (self.url, self._workspace, layername, tablename)
        r = self.request(url)
        ft = r.json()
        ft["featureType"]["name"] = layername
        r = self.request(url, ft, "put")
        self.logInfo("Feature type correctly created from GPKG file '%s'" % filename)
        self._setLayerStyle(layername, stylename)

    def _publishVectorLayerFromPostgis(self, db, crsauthid, layername, style, stylename):
        self._ensureWorkspaceExists()
        self.deleteLayer(layername)
        self._publishStyle(stylename, style)
        username, password = db.getCredentials()
        def _entry(k, v):
            return {"@key":k, "$":v}
        ds = {   
            "dataStore": {
                "name": layername,
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
                "name": layername,
                "srs": crsauthid
            }
        }    
        ftUrl = "%s/workspaces/%s/datastores/%s/featuretypes" % (self.url, self._workspace, layername)        
        self.request(ftUrl, data=ft, method="post")             
        self._setLayerStyle(layername, stylename)

    def _publishRasterLayer(self, filename, style, layername, stylename):
        #feedback.setText("Publishing data for layer %s" % layername)
        self._ensureWorkspaceExists()
        self._publishStyle(stylename, style)
        with open(filename, "rb") as f:
            url = "%s/workspaces/%s/coveragestores/%s/file.geotiff" % (self.url, self._workspace, layername)
            self.request(url, f.read(), "put")
        self.logInfo("Feature type correctly created from Tiff file '%s'" % filename)
        self._setLayerStyle(layername, stylename)

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

        groupdef = {"layerGroup":{"name": group["name"],"mode":"NAMED","publishables": {"published":layers}}}
        
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

    def _exists(self, url, category, name):
        r = self.request(url)
        root = r.json()["%ss" % category]
        if category in root:            
            layers = [s["name"] for s in root[category]]
            return name in layers
        else:
            return False

    def layerExists(self, name):
        if not self.workspaceExists():
            return False
        url = "%s/workspaces/%s/layers.json" % (self.url, self._workspace)
        return self._exists(url, "layer", name)

    def styleExists(self, name):
        if not self.workspaceExists():
            return False
        url = "%s/workspaces/%s/styles.json" % (self.url, self._workspace)
        return self._exists(url, "style", name)

    def workspaceExists(self):        
        try:
            url = "%s/workspaces.json" % (self.url)
            return self._exists(url, "workspace", self._workspace)
        except ConnectionError:
            return False

    def deleteLayer(self, name):
        if self.layerExists(name):
            url = "%s/workspaces/%s/layers/%s.json?recurse=true" % (self.url, self._workspace, name)        
            r = self.request(url, method="delete")        
        
    def openWms(self, names, bbox, srs):
        url = self.layerWms(names, bbox, srs)
        webbrowser.open_new_tab(url)

    def layerWms(self, names, bbox, srs):
        baseurl = self.baseUrl()
        names = ",".join(["%s:%s" % (self._workspace, name) for name in names])
        url = ("%s/%s/wms?service=WMS&version=1.1.0&request=GetMap&layers=%s&format=application/openlayers&bbox=%s&srs=%s&width=800&height=600" 
                    % (baseurl, self._workspace, names, bbox, srs))
        return url
        
    def setLayerMetadataLink(self, name, url):
        url = "%s/workspaces/%s/layers/%s.json" % (self.url, self._workspace, name)
        r = self.request(url)
        resourceUrl = r.json()["layer"]["resource"]["href"]
        r = self.request(resourceUrl)
        layer = r.json()
        layer["featureType"]["metadataLinks"] = {
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

        