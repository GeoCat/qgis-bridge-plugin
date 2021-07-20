from osgeo import gdal
from qgis.core import (
    QgsVectorFileWriter,
    QgsRasterFileWriter,
    QgsCoordinateTransformContext
)

from geocatbridge.utils import feedback
from geocatbridge.utils import layers as lyr_utils
from geocatbridge.utils.files import tempFileInSubFolder

EXT_SHAPEFILE = ".shp"
EXT_GEOPACKAGE = ".gpkg"


def isSingleTableGpkg(layer):
    ds = gdal.OpenEx(layer)
    return ds.GetLayerCount() == 1


def exportLayer(layer, fields=None, to_shapefile=False, path=None, force=False, logger=None):
    logger = logger or feedback
    filepath, _, orig_ext = lyr_utils.getLayerSourceInfo(layer)
    lyr_name, safe_name = lyr_utils.getLayerTitleAndName(layer)
    fields = fields or []
    if layer.type() == layer.VectorLayer:
        if to_shapefile and (force or layer.fields().count() != len(fields) or orig_ext != EXT_SHAPEFILE):
            # Export with Shapefile extension
            ext = EXT_SHAPEFILE
        elif force or orig_ext != EXT_GEOPACKAGE or layer.fields().count() != len(fields) \
                or not isSingleTableGpkg(filepath):
            # Export with GeoPackage extension
            ext = EXT_GEOPACKAGE
        else:
            # No need to export
            logger.logInfo(f"No need to export layer {lyr_name} stored at {filepath}")
            return filepath

        # Perform GeoPackage or Shapefile export
        if orig_ext == EXT_SHAPEFILE and ext == EXT_GEOPACKAGE:
            # Shapefiles: FID fields should not be exported to GeoPackage (causes conflicts)
            attrs = [i for i, f in enumerate(layer.fields()) if
                     (len(fields) == 0 or f.name() in fields) and f.name().lower() != 'fid']
        else:
            attrs = [i for i, f in enumerate(layer.fields()) if len(fields) == 0 or f.name() in fields]
        driver = "ESRI Shapefile" if ext == EXT_SHAPEFILE else "GPKG"
        output = path or tempFileInSubFolder(safe_name + ext)
        encoding = "UTF-8"
        options = None
        if hasattr(QgsVectorFileWriter, 'SaveVectorOptions'):
            # QGIS v3.x has the SaveVectorOptions object
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.fileEncoding = encoding
            options.attributes = attrs
            options.driverName = driver
        # Make sure that we are using the latest (non-deprecated) write method
        if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
            # Use writeAsVectorFormatV3 for QGIS versions >= 3.20 to avoid DeprecationWarnings
            result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, output, QgsCoordinateTransformContext(), options)  # noqa
        elif hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV2'):
            # Use writeAsVectorFormatV2 for QGIS versions >= 3.10.3 to avoid DeprecationWarnings
            result = QgsVectorFileWriter.writeAsVectorFormatV2(layer, output, QgsCoordinateTransformContext(), options)  # noqa
        else:
            # Use writeAsVectorFormat for QGIS versions < 3.10.3 for backwards compatibility
            result = QgsVectorFileWriter.writeAsVectorFormat(layer, output,
                                                             fileEncoding=encoding, attributes=attrs, driverName=driver)  # noqa
        # Check if first item in result tuple is an error code
        if result[0] == QgsVectorFileWriter.NoError:
            logger.logInfo(f"Layer {lyr_name} exported to {output}")
        else:
            # Dump the result tuple as-is when there are errors (the tuple size depends on the QGIS version)
            logger.logError(f"Layer {lyr_name} failed to export.\n\tResult object: {str(result)}")
        return output
    else:
        # Export raster
        if force or not filepath.lower().endswith("tif"):
            output = path or tempFileInSubFolder(safe_name + ".tif")
            writer = QgsRasterFileWriter(output)
            writer.setOutputFormat("GTiff")
            writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())
            del writer
            logger.logInfo(f"Layer {lyr_name} exported to {output}")
            return output
        else:
            logger.logInfo(f"No need to export layer {lyr_name} stored at {filepath}")
            return filepath
