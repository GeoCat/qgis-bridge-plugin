from qgis.core import QgsVectorFileWriter, QgsRasterFileWriter
from qgiscommons2.files import tempFilenameInTempFolder
from geocatbridgecommons import log

def exportLayer(layer, fields=None):
    filename = layer.source()
    destFilename = layer.name()
    if layer.type() == layer.VectorLayer:            
        if os.path.splitext(filename.lower()) not in [".shp", ".gpkg"] or layer.fields().count() != len(fields):
            attrs = [i for i, f in enumerate(layer.fields()) if fields is None or f.name() in fields]
            output = tempFilenameInTempFolder(destFilename + ".gpkg")
            QgsVectorFileWriter.writeAsVectorFormat(layer, output, "UTF-8", attributes=attrs)
            log.logInfo("Layer %s exported to %s" % (destFilename, output))
            return output
        else:
            log.logInfo("No need to export layer %s stored at %s" % (destFilename, filename))
            return filename
    else:
        if (not filename.lower().endswith("tif")):        
            output = tempFilenameInTempFolder(destFilename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff");
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            log.logInfo("Layer %s exported to %s" % (destFilename, output))
            return output
        else:
            log.logInfo("No need to export layer %s stored at %s" % (destFilename, filename))
            return filename






