from qgis.core import QgsVectorLayerExporter, QgsRasterFileWriter
from qgiscommons2.files import tempFilenameInTempFolder
from geocatbridgecommons import logInfo, logWarning, logError

def exportLayer(layer, fields=None):
    filename = layer.source()
    destFilename = layer.name()
    if layer.type() == layer.VectorLayer:
        fields = fields or layer.fields()        
        if not filename.lower().endswith("gpkg") or layer.fields().count() != len(fields):
            attrs = [i for i, f in enumerate(layer.fields()) if f.name() in fields]
            output = tempFilenameInTempFolder(destFilename + ".gpkg")
            QgsVectorFileWriter.writeAsVectorFormat(layer, output, "UTF-8", attributes=attrs)
            return output
            logInfo("Layer %s exported to %s" % (destFilename, output))
        else:
            logInfo("No need to export layer %s stored at %s" % (destFilename, filename))
            return filename
    else:
        if (not filename.lower().endswith("tif")):        
            output = tempFilenameInTempFolder(destFilename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff");
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            logInfo("Layer %s exported to %s" % (destFilename, output))
            return output
        else:
            logInfo("No need to export layer %s stored at %s" % (destFilename, filename))
            return filename






