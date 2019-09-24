from bridgecommon.catalog import GeodataCatalog
import os

#A dummy catalog
class MapServerCatalog(GeodataCatalog):

    def __init__(self):
        super().__init__("", None)

    def style_exists(self, name):
        return False        

    def delete_style(self, name):
        return False

    def layer_exists(self, name):
        return False

    def delete_layer(self, name):
        return False
    
    def open_wms(self, names, bbox, srs):
        pass

    def layer_wms(self, names, bbox, srs):
        return ""
        
    def set_layer_metadata_link(self, name, url):
        pass

    def create_group(self, name, layers):
        pass
