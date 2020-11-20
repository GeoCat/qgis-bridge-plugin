import os

try:
    from osgeo import gdal
except (ModuleNotFoundError, ImportError):
    import gdal

from qgis.core import QgsVectorFileWriter, QgsRasterFileWriter, QgsProject, Qgis
from qgis.PyQt.QtCore import QCoreApplication

from geocatbridge.utils.files import tempFilenameInTempFolder

EXT_SHAPEFILE = ".shp"
EXT_GEOPACKAGE = ".gpkg"


def isSingleTableGpkg(layer):
    ds = gdal.OpenEx(layer)
    return ds.GetLayerCount() == 1


def exportLayer(layer, fields=None, toShapefile=False, path=None, force=False, log=None):
    filename = layer.source().split("|")[0]
    destFilename = layer.name()
    fields = fields or []
    if layer.type() == layer.VectorLayer:
        if toShapefile and (force or layer.fields().count() != len(fields) or
                            (os.path.splitext(filename.lower())[1] != EXT_SHAPEFILE)):
            # Export with Shapefile extension
            ext = EXT_SHAPEFILE
        elif force or os.path.splitext(filename.lower())[1] != EXT_GEOPACKAGE or \
                layer.fields().count() != len(fields) or not isSingleTableGpkg(filename):
            # Export with GeoPackage extension
            ext = EXT_GEOPACKAGE
        else:
            # No need to export
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge",
                                                       f"No need to export layer {destFilename} stored at {filename}"))
            return filename

        # Perform GeoPackage or Shapefile export
        attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
        output = path or tempFilenameInTempFolder(destFilename + ext)
        if Qgis.QGIS_VERSION_INT < 31003:
            # Use writeAsVectorFormat for QGIS versions < 3.10.3 for backwards compatibility
            QgsVectorFileWriter.writeAsVectorFormat(
                layer, output, fileEncoding="UTF-8", attributes=attrs,
                driverName="ESRI Shapefile" if ext == EXT_SHAPEFILE else ""
            )
        else:
            # Use writeAsVectorFormatV2 for QGIS versions >= 3.10.3 to avoid DeprecationWarnings
            transform_ctx = QgsProject.instance().transformContext()
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.fileEncoding = "UTF-8"
            options.attributes = attrs
            options.driverName = "ESRI Shapefile" if ext == EXT_SHAPEFILE else ""
            QgsVectorFileWriter.writeAsVectorFormatV2(layer, output, transform_ctx, options)
        if log is not None:
            log.logInfo(QCoreApplication.translate("GeocatBridge",
                                                   f"Layer {destFilename} exported to {output}"))
        return output
    else:
        # Export raster
        if force or not filename.lower().endswith("tif"):
            output = path or tempFilenameInTempFolder(destFilename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff")
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge",
                                                       f"Layer {destFilename} exported to {output}"))
            return output
        else:
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge",
                                                       f"No need to export layer {destFilename} stored at {filename}"))
            return filename
