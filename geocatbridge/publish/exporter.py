from qgis.core import QgsVectorFileWriter, QgsRasterFileWriter
from qgiscommons2.files import tempFilenameInTempFolder

def exportLayer(layer):
    filename = layer.source()
    destFilename = layer.name()
    if layer.type() == layer.VectorLayer:
        if (not filename.lower().endswith("gpkg")):
            output = tempFilenameInTempFolder(destFilename + ".gpkg")
            QgsVectorFileWriter.writeAsVectorFormat(layer, output, 'utf-8', layer.crs(), "GPKG")
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






