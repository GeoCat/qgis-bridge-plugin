import os
import psycopg2
import json
import webbrowser

from qgis.core import QgsProject

from qgis.PyQt.QtCore import QCoreApplication

from geoserver.catalog import Catalog
from geoserver.catalog import ConflictingDataError

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
        self._gscatalog = Catalog(self.url, user, password)
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

    def _publishStyle(self, name, styleFilename):
        #feedback.setText("Publishing style for layer %s" % name)
        self._ensureWorkspaceExists()
        styleExists = bool(self._gscatalog.get_styles(names=name, workspaces=self._workspace))
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
                self._publishVectorLayerFromPostgis(db.host, db.port, 
                                        db.database, db.schema, layer.name(), 
                                        db._username, db._password, layer.crs().authid(), 
                                        layer.name(), styleFilename, layer.name())
        elif layer.type() == layer.RasterLayer:
            filename = exportLayer(layer, fields, log = self)            
            self._publishRasterLayer(filename, styleFilename, layer.name(), layer.name())

    def testConnection(self):
        try:
            self._gscatalog.gsversion()
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
        self._deleteLayerIfItExists(layername)
        self._publishStyle(stylename, style)
        #feedback.setText("Publishing data for layer %s" % layername)
        if filename.lower().endswith(".shp"):
            basename, extension = os.path.splitext(filename)
            path = {
                'shp': basename + '.shp',
                'shx': basename + '.shx',
                'dbf': basename + '.dbf',
                'prj': basename + '.prj'
            }
            self._gscatalog.create_featurestore(layername, path, self._workspace, True)
            self._setLayerStyle(layername, stylename)
        elif filename.lower().endswith(".gpkg"):
            with open(filename, "rb") as f:
                url = "%s/workspaces/%s/datastores/%s/file.gpkg?update=overwrite" % (self.url, self._workspace, layername)
                self.request(url, f.read(), "put")
            storeName = os.path.splitext(os.path.basename(filename))[0]
            url = "%s/workspaces/%s/layers/%s.json" % (self.url, self._workspace, storeName)
            #TODO ensure layer name 
            self.logInfo("Feature type correctly created from GPKG file '%s'" % filename)
            self._setLayerStyle(layername, stylename)

    def _publishVectorLayerFromPostgis(self, host, port, database, schema, table, 
                                        username, passwd, crsauthid, layername, style, stylename):
        self._ensureWorkspaceExists()
        self._deleteLayerIfItExists(layername)
        self._publishStyle(stylename, style)
        #feedback.setText("Publishing data for layer %s" % layername)        
        store = self._gscatalog.create_datastore(layername, self._workspace)
        store.connection_parameters.update(host=host, port=str(port), database=database, user=username, 
                                            schema=schema, passwd=passwd, dbtype="postgis")
        self._gscatalog.save(store)        
        ftype = self._gscatalog.publish_featuretype(table, store, crsauthid, native_name=layername)        
        if ftype.name != layername:
            ftype.dirty["name"] = layername
        self._gscatalog.save(ftype)
        self._setLayerStyle(layername, stylename)

    def _publishRasterLayer(self, filename, style, layername, stylename):
        #feedback.setText("Publishing data for layer %s" % layername)
        self._ensureWorkspaceExists()
        self._publishStyle(stylename, style)
        self._gscatalog.create_coveragestore(layername, self._workspace, filename)
        self._setLayerStyle(layername, stylename)

    def createGroups(self, groups): 
        print(groups)       
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
        
        headers = {"Content-Type": "application/json"}
        url = "%s/workspaces/%s/layergroups" % (self.url, self._workspace)           
        try:
            self.request(url, json.dumps(groupdef), "post", headers)
        except:
            self.request(url, json.dumps(groupdef), "put", headers)

        self.logInfo("Group %s correctly created" % group["name"])

    def styleExists(self, name):
        if not self._workspaceExists():
            return False
        return len(self._gscatalog.get_styles(name, self._workspace)) > 0

    def deleteStyle(self, name):
        styles = self._gscatalog.get_styles(name, self._workspace)
        if styles:
            self._gscatalog.delete(styles[0])

    def layerExists(self, name):
        return self._getLayer(name) is not None

    def deleteLayer(self, name):
        layer = self._getLayer(name)
        self._gscatalog.delete(layer, recurse = True, purge = True)
    
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
        layer = self._getLayer(name)
        resource = layer.resource
        resource.metadata_links= [('text/html', 'other', url),]
        self._gscatalog.save(resource)

    def deleteWorkspace(self):
        ws  = self._gscatalog.get_workspaces(self._workspace)
        if ws:
            self._gscatalog.delete(ws[0], recurse = True)

    ##########

    def _getLayer(self, name):
        fullname = self._workspace + ":" + name
        for layer in self._gscatalog.get_layers():
            if layer.name.lower() == fullname.lower():
                return layer

    def _setLayerStyle(self, layername, stylename):
        self._gscatalog._cache.clear() #We are doing stuff on the geoserver rest api without using gsconfig, so cache might be outdated
        layer = self._getLayer(layername)
        default = self._gscatalog.get_styles(stylename, self._workspace)[0]
        layer.default_style = default
        self._gscatalog.save(layer)
        self.logInfo("Style %s correctly assigned to layer %s" % (stylename, layername))


    def _workspaceExists(self):
        ws  = self._gscatalog.get_workspaces(self._workspace)
        return bool(ws)

    def _ensureWorkspaceExists(self):
        ws  = self._gscatalog.get_workspaces(self._workspace)
        if not ws:
            self.logInfo("Workspace %s does not exist. Creating it." % self._workspace)
            self._gscatalog.create_workspace(self._workspace, "http://%s.geocat.net" % self._workspace) #TODO change URL


    def _deleteLayerIfItExists(self, name):
        layer = self._getLayer(name)
        if layer:
            self._gscatalog.delete(layer)
        try:
            stores = self._gscatalog.get_stores(name, self._workspace)
            if stores:
                store = stores[0]
                for res in store.get_resources():
                    self._gscatalog.delete(res)
                self._gscatalog.delete(store)
        except:
            pass 
            '''We swallow possible errors while deleting the underlying datastore.
            That shouldn't be a problem, since later we are going to upload using overwrite mode'''


