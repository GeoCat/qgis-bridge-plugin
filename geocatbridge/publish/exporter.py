import os
import gdal

from qgis.core import QgsVectorFileWriter, QgsRasterFileWriter
from qgis.PyQt.QtCore import QCoreApplication

from geocatbridge.utils.files import tempFilenameInTempFolder

def isSingleTableGpkg(layer):
    ds = gdal.OpenEx(layer)
    return ds.GetLayerCount() == 1

def exportLayer(layer, fields=None, toShapefile=False, path=None, force=False, log=None):
    filename = layer.source().split("|")[0]
    destFilename = layer.name()
    fields = fields or []
    if layer.type() == layer.VectorLayer:
        if toShapefile:
            if force or layer.fields().count() != len(fields) or (os.path.splitext(filename.lower())[1]  != ".shp"):
                attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
                output = path or tempFilenameInTempFolder(destFilename + ".shp")
                QgsVectorFileWriter.writeAsVectorFormat(layer, output, "UTF-8", attributes=attrs, driverName="ESRI Shapefile")
                if log is not None:
                    log.logInfo(QCoreApplication.translate("GeocatBridge", "Layer %s exported to %s") % (destFilename, output))
                return output
        elif (force or os.path.splitext(filename.lower())[1]  != ".gpkg"
                        or layer.fields().count() != len(fields) or not isSingleTableGpkg(filename)):
            attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
            output = path or tempFilenameInTempFolder(destFilename + ".gpkg")
            QgsVectorFileWriter.writeAsVectorFormat(layer, output, "UTF-8", attributes=attrs)
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge", "Layer %s exported to %s") % (destFilename, output))
            return output
        
        if log is not None:
            log.logInfo(QCoreApplication.translate("GeocatBridge", "No need to export layer %s stored at %s") % (destFilename, filename))
        return filename
    else:
        if (force or not filename.lower().endswith("tif")):        
            output = path or tempFilenameInTempFolder(destFilename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff");
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge", "Layer %s exported to %s") % (destFilename, output))
            return output
        else:
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge", "No need to export layer %s stored at %s") % (destFilename, filename))
            return filename





