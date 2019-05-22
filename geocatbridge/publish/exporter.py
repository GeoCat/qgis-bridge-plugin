from qgis.core import QgsVectorLayerExporter, QgsRasterFileWriter
from qgiscommons2.files import tempFilenameInTempFolder

def exportLayer(layer, fields=None):
    filename = layer.source()
    destFilename = layer.name()
    if layer.type() == layer.VectorLayer:
        fields = fields or layer.fields()        
        if (not filename.lower().endswith("gpkg") or layer.fields() != fields):
            output = tempFilenameInTempFolder(destFilename + ".gpkg")
            exporter = QgsVectorLayerExporter(output, "GPKG", fields, layer.geometryType(), layer.crs(), True)
            for feature in layer.getFeatures():
                exporter.addFeature(feature)
            exporter.flushBuffer()
            return output
        else:
            return filename
    else:
        if (not filename.lower().endswith("tif")):        
            output = tempFilenameInTempFolder(destFilename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff");
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            return output
        else:
            return filename






