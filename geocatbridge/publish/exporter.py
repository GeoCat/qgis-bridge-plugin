import os

from osgeo import gdal
from qgis.core import (
    QgsVectorFileWriter,
    QgsRasterFileWriter,
    QgsProject,
    Qgis
)

from geocatbridge.utils.files import tempFilenameInTempFolder

EXT_SHAPEFILE = ".shp"
EXT_GEOPACKAGE = ".gpkg"


def isSingleTableGpkg(layer):
    ds = gdal.OpenEx(layer)
    return ds.GetLayerCount() == 1


def exportLayer(layer, fields=None, to_shapefile=False, path=None, force=False, logger=None):

    def safeLog(message):
        if not logger or not hasattr(logger, 'logInfo'):
            return
        logger.logInfo(message)

    filename = layer.source().split("|")[0]
    dest_filename = layer.name()
    fields = fields or []
    if layer.type() == layer.VectorLayer:
        if to_shapefile and (force or layer.fields().count() != len(fields) or
                             (os.path.splitext(filename.lower())[1] != EXT_SHAPEFILE)):
            # Export with Shapefile extension
            ext = EXT_SHAPEFILE
        elif force or os.path.splitext(filename.lower())[1] != EXT_GEOPACKAGE or \
                layer.fields().count() != len(fields) or not isSingleTableGpkg(filename):
            # Export with GeoPackage extension
            ext = EXT_GEOPACKAGE
        else:
            # No need to export
            safeLog(f"No need to export layer {dest_filename} stored at {filename}")
            return filename

        # Perform GeoPackage or Shapefile export
        attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
        output = path or tempFilenameInTempFolder(dest_filename + ext)
        if Qgis.QGIS_VERSION_INT < 31003:
            # Use writeAsVectorFormat for QGIS versions < 3.10.3 for backwards compatibility
            # noinspection PyArgumentList
            QgsVectorFileWriter().writeAsVectorFormat(
                layer, output, fileEncoding="UTF-8", attributes=attrs,
                driverName="ESRI Shapefile" if ext == EXT_SHAPEFILE else ""
            )
        else:
            # Use writeAsVectorFormatV2 for QGIS versions >= 3.10.3 to avoid DeprecationWarnings
            transform_ctx = QgsProject().instance().transformContext()
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.fileEncoding = "UTF-8"
            options.attributes = attrs
            options.driverName = "ESRI Shapefile" if ext == EXT_SHAPEFILE else ""
            QgsVectorFileWriter().writeAsVectorFormatV2(layer, output, transform_ctx, options)
        safeLog(f"Layer {dest_filename} exported to {output}")
        return output
    else:
        # Export raster
        if force or not filename.lower().endswith("tif"):
            output = path or tempFilenameInTempFolder(dest_filename + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff")
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            safeLog(f"Layer {dest_filename} exported to {output}")
            return output
        else:
            safeLog(f"No need to export layer {dest_filename} stored at {filename}")
            return filename
