from .catalog import GeodataCatalog

class MapServerCatalog(GeodataCatalog):

    def __init__(service_url, network_access_manager):
        pass
        
    def publish_vector_layer_from_file(self, filename, layername, style, stylename):
        pass

    def publish_vector_layer_from_postgis(self, host, port, database, schema, table, 
                                        username, passwd, layername, style, stylename):
        pass

    def publish_raster_layer(self, filename, style, name):
        pass

    def create_group(self, layers):
        pass

    def publish_style(self, sld, name):
        pass

    def raster_layer_exists(self, name):
        pass

    def vector_layer_exists(self, name):
        pass

    def delete_raster_layer(self, name):
        pass
    
    def delete_vector_layer(self, name):
        pass    
