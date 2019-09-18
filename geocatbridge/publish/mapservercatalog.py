from bridgecommon.catalog import GeodataCatalog
import os

#A dummy catalog, since for now Bridge only creates the mapserver folder and does not publish it to the server itself
class MapServerCatalog(GeodataCatalog):

    def __init__(self, folder="", host="", port="", username="", password=""):
        super().__init__(folder or host, None)
        self.folder = folder
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def style_exists(self, name):
        if folder:
            return os.path.exists(os.path.join(self.folder, "style.map"))        

    def delete_style(self, name):
        if folder:
            os.remove(os.path.join(self.folder, "style.map"))

    def layer_exists(self, name):
        if folder:
            return os.path.exists(os.path.join(self.folder, name + ".shp"))

    def delete_layer(self, name):
        if folder:
            os.remove(os.path.join(self.folder, name + ".shp"))
    
    def open_wms(self, names, bbox, srs):
        pass

    def layer_wms(self, names, bbox, srs):
        return self.url
        
    def set_layer_metadata_link(name, url):
        pass
