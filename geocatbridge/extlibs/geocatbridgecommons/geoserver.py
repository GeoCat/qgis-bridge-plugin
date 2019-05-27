from .server import GeodataCatalog
from geoserver.catalog import Catalog
from geoserver.catalog import ConflictingDataError

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
        return self.nam.request(url, method, data, headers)

    def setup_connection(self):
        pass

class GeoServerCatalog(GeodataCatalog):

    def __init__(self, service_url, network_access_manager, workspace):
        self.workspace = workspace
        self.gscatalog = GSConfigCatalogUsingNetworkAccessManager(service_url, network_access_manager)

    def publish_vector_layer_from_file(self, filename, layername, style, stylename):
        self._ensureWorkspaceExists()
        self.publish_style(stylename, zipfile = style)
        if filename.lower().endswith(".shp"):
            basename, extension = os.path.splitext(filename)
            path = {
                'shp': basename + '.shp',
                'shx': basename + '.shx',
                'dbf': basename + '.dbf',
                'prj': basename + '.prj'
            }
            self.gscatalog.create_featurestore(name, path, self.workspace, True)
            self._set_layer_style(layername, stylename)
        elif filename.lower().endswith(".gpkg"):
            json = { "dataStore": {
                        "name": layername,
                        "connectionParameters": {
                            "entry": [
                                {"@key":"database","$":"file://" + filename},
                                {"@key":"dbtype","$":"geopkg"}
                                ]
                            }
                        }
                    }
            headers = {'Content-type': 'application/json'}
            url = self.service_url + "/workspaces/%s/datastores" % self.workspace
            self.gscatalog.nam.http_request(url, data=json, method="put", headers=headers)
            store = self.gscatalog.get_store(layername, self.workspace)
            ftype = self.catalog.publish_featuretype(layername, store, crsauthid)        
            if ftype.name != name:
                ftype.dirty["name"] = name
            self.gscatalog.save(ftype)
            self._set_layer_style(layername, stylename)

    def publish_vector_layer_from_postgis(self, host, port, database, schema, table, 
                                        username, passwd, crsauthid, layername, style, stylename):
        self._ensureWorkspaceExists()
        self.publish_style(stylename, zipfile = style)
        store = self.gscatalog.create_datastore(name, self.workspace)
        store.connection_parameters.update(host=host, port=str(port), database=database, user=user, 
                                            schema=schema, passwd=passwd, dbtype="postgis")
        self.gscatalog.save(store)        
        ftype = self.catalog.publish_featuretype(table, store, crsauthid)        
        if ftype.name != name:
            ftype.dirty["name"] = name
        self.gscatalog.save(ftype)
        self._set_layer_style(layername, stylename)

    def publish_raster_layer(self, filename, style, layername, stylename):
        self._ensureWorkspaceExists()
        self.publish_style(stylename, sld = style)
        self.gscatalog.create_coveragestore(layername, filename, self.workspace, True)
        self._set_layer_style(layerame, stylename)

    def create_group(self, groupname, layernames, styles, bounds):
        try:
            layergroup = catalog.create_layergroup(groupname, layernames, layernames, bounds, workspace=self.workspace)
        except ConflictingDataError:
            layergroup = catalog.get_layergroups(groupname)[0]
            layergroup.dirty.update(layers = layernames, styles = names)

    def publish_style(self, name, sld=None, zipfile=None):
        self._ensureWorkspaceExists()
        if sld:
            self.gscatalog.create_style(name, sld, True)
        elif zipfile:
            headers = {'Content-type': 'application/zip'}
            url = self.service_url + "/workspaces/%s/styles" % self.workspace
            with open(zipfile, "rb") as f:
                data = f.read()
                self.gscatalog.nam.http_request(url, data=data, method="put", headers=headers)
        else:
            raise ValueError("A style definition must be provided, whether using a zipfile path or a SLD string")

    def style_exists(self, name):
        return len(sself.gscatalog.get_styles(stylename, self.workspace)) > 0

    def delete_style(self, name):
        style = self.gscatalog.get_styles(stylename, self.workspace)[0]
        self.gscatalog.delete(style)

    def layer_exists(self, name):
        return self._get_layer(name) is not None

    def delete_layer(self, name):
        layer = self._get_layer(name)
        self.gscatalog.delete(layer, recurse = True, purge = True)
    

    ##########

    def _get_layer(self, name):
        layers = [layer for layer in self.gscatalog.get_layers() if layer.name == name]
        for layer in layers:
            if layer.resource.workspace.name == self.workspace:
                return layer        

    def _set_layer_style(self, layername, stylename):
        layer = self._get_layer(name)
        layer.default_style = self.gscatalog.get_styles(stylename, self.workspace)[0]
        self.gscatalog.save(layer)

    def _ensureWorkspaceExists(self):
        pass








