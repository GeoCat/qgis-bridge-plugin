import os
import webbrowser
from .catalog import GeodataCatalog
from geoserver.catalog import Catalog
from geoserver.catalog import ConflictingDataError
from . import log
from . import feedback
import json

class GSConfigCatalogUsingNetworkAccessManager(Catalog):

    #A class that patches the gsconfig Catalog class, to allow using a custom network access manager 
    def __init__(self, service_url, network_access_manager):
        self.service_url = service_url.strip("/")
        self._cache = dict()
        self._version = None
        self.nam = network_access_manager
        self.username = ''
        self.password = ''

    def http_request(self, url, data=None, method='get', headers = {}):
        log.logInfo("Making '%s' request to '%s'" % (method, url))
        resp, content = self.nam.request(url, method, data, headers)
        return resp

    def setup_connection(self):
        pass

class GeoServerCatalog(GeodataCatalog):

    def __init__(self, service_url, network_access_manager, workspace):
        super(GeoServerCatalog, self).__init__(service_url, network_access_manager)
        self.workspace = workspace
        self.gscatalog = GSConfigCatalogUsingNetworkAccessManager(service_url, network_access_manager)

    def publish_vector_layer_from_file(self, filename, layername, crsauthid, style, stylename):
        log.logInfo("Publishing layer from file: %s" % filename)
        self._ensureWorkspaceExists()
        self._deleteLayerIfItExists(layername)
        self.publish_style(stylename, zipfile = style)
        feedback.setText("Publishing data for layer %s" % layername)
        if filename.lower().endswith(".shp"):
            basename, extension = os.path.splitext(filename)
            path = {
                'shp': basename + '.shp',
                'shx': basename + '.shx',
                'dbf': basename + '.dbf',
                'prj': basename + '.prj'
            }
            self.gscatalog.create_featurestore(layername, path, self.workspace, True)
            self._set_layer_style(layername, stylename)
        elif filename.lower().endswith(".gpkg"):
            with open(filename, "rb") as f:
                url = "%s/workspaces/%s/datastores/%s/file.gpkg?update=overwrite" % (self.service_url, self.workspace, layername)
                self.http_request(url, f.read(), "put",)
            storeName = os.path.splitext(os.path.basename(filename))[0]
            url = "%s/workspaces/%s/layers/%s.json" % (self.service_url, self.workspace, storeName)
            self.http_request(url, json.dumps({"name": layername}), "put")
            '''
            storeName = os.path.splitext(os.path.basename(filename))[0]
            print(storeName)
            layer = self._get_layer(storeName)
            layer.title = layername
            self.gscatalog.save(layer) 
            '''     
            log.logInfo("Feature type correctly created from GPKG file '%s'" % filename)
            self._set_layer_style(layername, stylename)

    def publish_vector_layer_from_postgis(self, host, port, database, schema, table, 
                                        username, passwd, crsauthid, layername, style, stylename):
        self._ensureWorkspaceExists()
        self._deleteLayerIfItExists(layername)
        self.publish_style(stylename, zipfile = style)
        feedback.setText("Publishing data for layer %s" % layername)        
        store = self.gscatalog.create_datastore(layername, self.workspace)
        store.connection_parameters.update(host=host, port=str(port), database=database, user=username, 
                                            schema=schema, passwd=passwd, dbtype="postgis")
        self.gscatalog.save(store)        
        ftype = self.gscatalog.publish_featuretype(table, store, crsauthid, native_name=layername)        
        if ftype.name != layername:
            ftype.dirty["name"] = layername
        self.gscatalog.save(ftype)
        self._set_layer_style(layername, stylename)

    def publish_raster_layer(self, filename, style, layername, stylename):
        feedback.setText("Publishing data for layer %s" % layername)
        self._ensureWorkspaceExists()
        self.publish_style(stylename, sld = style)
        self.gscatalog.create_coveragestore(layername, filename, self.workspace, True)
        self._set_layer_style(layerame, stylename)

    def create_group(self, groupname, layernames, styles, bounds):
        try:
            layergroup = self.gscatalog.create_layergroup(groupname, layernames, layernames, bounds, workspace=self.workspace)
        except ConflictingDataError:
            layergroup = self.gscatalog.get_layergroups(groupname)[0]
            layergroup.dirty.update(layers = layernames, styles = names)

    def publish_style(self, name, sld=None, zipfile=None):
        feedback.setText("Publishing style for layer %s" % name)
        self._ensureWorkspaceExists()
        styleExists = bool(self.gscatalog.get_styles(names=name, workspaces=self.workspace))
        if sld:
            self.gscatalog.create_style(name, sld, True)
            log.logInfo("Style %s correctly created from SLD file '%s'" % (name, sld))
        elif zipfile:
            headers = {'Content-type': 'application/zip'}
            if styleExists:
                method = "put"
                url = self.service_url + "/workspaces/%s/styles/%s" % (self.workspace, name)
            else:
                url = self.service_url + "/workspaces/%s/styles" % self.workspace
                method = "post"
            with open(zipfile, "rb") as f:
                self.http_request(url, f.read(), method, headers)
            log.logInfo("Style %s correctly created from Zip file '%s'" % (name, zipfile))
        else:
            raise ValueError("A style definition must be provided, whether using a zipfile path or a SLD string")

    def style_exists(self, name):
        return len(self.gscatalog.get_styles(name, self.workspace)) > 0

    def delete_style(self, name):
        style = self.gscatalog.get_styles(name, self.workspace)[0]
        self.gscatalog.delete(style)

    def layer_exists(self, name):
        '''
        url = self.service_url + "/workspaces/%s/layers.json" % (self.workspace)
        layers = json.loads(self.nam.request(url, "get", f.read()))
        names = [lay["name"] for layer in layers["layers"]["layer"]]
        return name in names
        '''
        return self._get_layer(name) is not None

    def delete_layer(self, name):
        layer = self._get_layer(name)
        self.gscatalog.delete(layer, recurse = True, purge = True)
    
    def open_wms(self, names, bbox, srs):
        baseurl = "/".join(self.service_url.split("/")[:-1])
        names = ",".join(["%s:%s" % (self.workspace, name) for name in names])
        url = ("%s/%s/wms?service=WMS&version=1.1.0&request=GetMap&layers=%s&format=application/openlayers&bbox=%s&srs=%s&width=800&height=600" 
                    % (baseurl, self.workspace, names, bbox, srs))
        webbrowser.open_new_tab(url)

    ##########

    def _get_layer(self, name):
        fullname = self.workspace + ":" + name
        for layer in self.gscatalog.get_layers():
            if layer.name.lower() == fullname.lower():
                return layer

    def _set_layer_style(self, layername, stylename):
        self.gscatalog._cache.clear() #We are doing stuff on the geoserver rest api without using gsconfig, so cache might be outdated
        layer = self._get_layer(layername)
        default = self.gscatalog.get_styles(stylename, self.workspace)[0]
        layer.default_style = default
        self.gscatalog.save(layer)
        log.logInfo("Style %s correctly assigned to layer %s" % (stylename, layername))

    def _ensureWorkspaceExists(self):
        ws  = self.gscatalog.get_workspaces(self.workspace)
        if not ws:
            log.logInfo("Workspace %s does not exist. Creating it." % self.workspace)
            self.gscatalog.create_workspace(self.workspace, "http://%s.geocat.net" % self.workspace) #TODO change URL


    def _deleteLayerIfItExists(self, name):
        layer = self._get_layer(name)
        if layer:
            self.gscatalog.delete(layer)
        try:
            stores = self.gscatalog.get_stores(name, self.workspace)
            if stores:
                store = stores[0]
                for res in store.get_resources():
                    self.gscatalog.delete(res)
                self.gscatalog.delete(store)
        except:
            pass 
            '''We swallow possible errors while deleting the underlying datastore.
            That shouldn't be a problem, since later we are going to upload using overwrite mode'''

