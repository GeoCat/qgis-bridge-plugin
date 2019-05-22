from qgis.core import QgsVectorLayerExporter
from qgiscommons2.files import tempFilenameInTempFolder
from .exporter import exportLayer
from .sldadapter import getCompatibleSldAsZip, getStyleAsSld

def publishLayerToCatalogUsingPostgis(connection, catalog, layer, fields):
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
    exporter = QgsVectorLayerExporter(uri.uri(), providerName, fields, layer.geometryType(), layer.crs(), True, options)
    for feature in layer.getFeatures():
    	exporter.addFeature(feature)
    exporter.flushBuffer()
    if exporter.errorCount():
    	raise Exception(exporter.errorMessage())
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


def publishMetadata(catalog, layer, metadata):
    if isinstance(catalog, GeoNetworkCatalog):
        metadatamef = createMetadataMefFile(layer, metadata)
        catalog.publish_metadata(metadatamef)
    elif isinstance(catalog, CSWCatalog):
        metadataxml = createMetadataXmlFile(layer, metadata)
        catalog.publish_metadata(metadataxml)


