from qgis.core import QgsVectorLayerExporter
from qgiscommons2.files import tempFilenameInTempFolder
from .exporter import exportLayer
from .sldadapter import getCompatibleSldAsZip, getStyleAsSld

def publishLayerToCatalogUsingPostgis(connection, catalog, layer):
    pk = "id"
    geom = "geom"
    providerName = "postgres"

    uri = QgsDataSourceURI()
    uri.setConnection(connection.host, str(connection.port), connection.dbname, connection.user, connection.passwd)
    uri.setDataSource(connection.schema, layer.name(), geom, "", pk)

    options = {}
    options['overwrite'] = True
    if singleGeom:
        options['forceSinglePartGeometryType'] = True
    ret, errMsg = QgsVectorLayerExporter.exporterLayer(layer, uri.uri(), providerName, layer.crs(), False, options)
    if ret != 0:
        raise Exception(errMsg)
    zipfile = getCompatibleSldAsZip(layer)
    catalog.publish_vector_layer_from_postgis(connection.host, str(connection.port), connection.dbname, 
    											connection.schema, layer.name(), connection.user, 
    											connection.passwd, layer.crs().authid(), layer.name(), 
    											zipfile, layer.name())

def publishLayerToCatalogWithDirectUpload(catalog, layer):
    filename = exportLayer(layer)    
    if layer.type() == layer.VectorLayer:
    	zipfile = getCompatibleSldAsZip(layer)
        catalog.publish_vector_layer_from_file(filename, zipfile, layer.name(), layer.name())
    elif layer.type() == layer.RasterLayer:
    	sld = getStyleAsSld(layer)
		catalog.publish_raster_layer(filename, sld, layer.name(), layer.name())







