from ..utils import layers

try:
    from osgeo import gdal
except (ModuleNotFoundError, ImportError):
    import gdal

from qgis.core import QgsVectorFileWriter, QgsRasterFileWriter, QgsProject, Qgis
from qgis.PyQt.QtCore import QCoreApplication

from geocatbridge.utils import layers as layerUtils
from geocatbridge.utils.files import tempFilenameInTempFolder

EXT_SHAPEFILE = ".shp"
EXT_GEOPACKAGE = ".gpkg"


def isSingleTableGpkg(layer):
    ds = gdal.OpenEx(layer)
    return ds.GetLayerCount() == 1


def exportLayer(layer, fields=None, toShapefile=False, path=None, force=False, log=None):
    filepath, _, ext = layers.getLayerSourceInfo(layer)
    lyr_name, safe_name = layerUtils.getLayerTitleAndName(layer)
    fields = fields or []
    if layer.type() == layer.VectorLayer:
        if toShapefile and (force or layer.fields().count() != len(fields) or ext != EXT_SHAPEFILE):
            # Export with Shapefile extension
            ext = EXT_SHAPEFILE
        elif force or ext != EXT_GEOPACKAGE or layer.fields().count() != len(fields) or not isSingleTableGpkg(filepath):
            # Export with GeoPackage extension
            ext = EXT_GEOPACKAGE
        else:
            # No need to export
            if log is not None:
                log.logInfo(
                    QCoreApplication.translate("GeocatBridge",
                                               "No need to export layer %s stored at %s" % (lyr_name, filepath)))
            return filepath

        # Perform GeoPackage or Shapefile export
        attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
        output = path or tempFilenameInTempFolder(safe_name + ext)
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
            log.logInfo(QCoreApplication.translate("GeocatBridge", "Layer %s exported to %s" % (lyr_name, output)))
        return output
    else:
        # Export raster
        if force or not filepath.lower().endswith("tif"):
            output = path or tempFilenameInTempFolder(safe_name + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff")
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge", "Layer %s exported to %s" % (lyr_name, output)))
            return output
        else:
            if log is not None:
                log.logInfo(QCoreApplication.translate("GeocatBridge",
                            "No need to export layer %s stored at %s" % (lyr_name, filepath)))
            return filepath
