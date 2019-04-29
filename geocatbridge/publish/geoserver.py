from .server import GeodataCatalog
from .sldadapter import getGsCompatibleSld

class GeoServerCatalog(GeodataCatalog):

    def publishLayer(self, layer, name=None):
        self.publishStyle(layer, name) 
        self.createDatastore(layer, name)

        #TODO:link style and layer

    def createGroup(self, layers):
        pass

    def publishLayerStyle(self, layer, name):        
        sld, icons = getGsCompatibleSld(layer)
        if sld is not None:
            name = name if name is not None else layer.name()
            name = name.replace(" ", "_")
            self.uploadIcons(icons)
            self.catalog.create_style(name, sld, overwrite)


    def uploadIcons(self, icons):
        for icon in icons:
            url = self.service_url + "/resource/styles/" + icon[1]
            r = self.http_request(url, data=icon[2], method="put")

    def createDatastore(self, layer, name):
        filename = exporter.exportLayer(layer)
        if layer.type() == layer.VectorLayer:
            json = { "dataStore": {
                        "name": name,
                        "connectionParameters": {
                            "entry": [
                                {"@key":"database","$":"file://" + filename},
                                {"@key":"dbtype","$":"geopkg"}
                                ]
                            }
                        }
                    }
            ws = self.getDefaultWorkspace()
            url = self.service_url + "/workspaces/%s/datastores" % ws
            r = self.http_request(url, data=json, method="put")
        else:
            pass #TODO

    def getDefaultWorkspace(self):
        return "default"









