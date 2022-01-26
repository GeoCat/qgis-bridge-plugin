from typing import List, Union, NamedTuple, Iterable
from pathlib import Path

from qgis.core import (
    QgsVectorFileWriter,
    QgsRasterFileWriter,
    QgsDataSourceUri,
    QgsProject
)

from geocatbridge.utils import feedback
from geocatbridge.utils.layers import BridgeLayer, layerById
from geocatbridge.utils.files import tempFileInSubFolder
from geocatbridge.utils.fields import fieldIndexLookup, fieldsForLayer

EXT_SHAPEFILE = ".shp"
EXT_GEOPACKAGE = ".gpkg"
EXT_GEOTIFF = ".tif"

DRIVER_GEOPACKAGE = "GPKG"
DRIVER_SHAPEFILE = "ESRI Shapefile"
DRIVER_GEOTIFF = "GTiff"


def _writeVector(layer: BridgeLayer, fields: List[str],
                 target_path: Union[str, Path], encoding: str = "UTF-8") -> tuple:
    """ Writes vector output to the given target path and returns the result tuple. """
    if not layer.can_publish:
        raise ValueError(f"layer is not exportable")
    target_path = Path(target_path)
    if target_path.suffix == EXT_GEOPACKAGE:
        driver = DRIVER_GEOPACKAGE
    elif target_path.suffix == EXT_SHAPEFILE:
        driver = DRIVER_SHAPEFILE
    else:
        raise ValueError(f"target_path must have {EXT_SHAPEFILE} or {EXT_GEOPACKAGE} extension")
    output = str(target_path)
    options = None
    attrs = list(sorted(fieldIndexLookup(layer, fields).values()))
    transform_context = QgsProject.instance().transformContext()
    if hasattr(QgsVectorFileWriter, 'SaveVectorOptions'):
        # QGIS v3.x has the SaveVectorOptions object
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.fileEncoding = encoding
        options.attributes = attrs
        options.driverName = driver
        if driver == DRIVER_GEOPACKAGE:
            if isinstance(layer.uri, Path) and layer.uri.suffix == EXT_SHAPEFILE:
                # If the input layer comes from a Shapefile, explicitly set the GeoPackage layer name
                options.layerName = layer.dataset_name
            if target_path.exists():
                # Add a new layer to existing GeoPackages (instead of overwriting the GeoPackage)
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    # Make sure that we are using the latest (non-deprecated) write method
    if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
        # Use writeAsVectorFormatV3 for QGIS versions >= 3.20 to avoid DeprecationWarnings
        result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, output, transform_context, options)
    elif hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV2'):
        # Use writeAsVectorFormatV2 for QGIS versions >= 3.10.3 to avoid DeprecationWarnings
        result = QgsVectorFileWriter.writeAsVectorFormatV2(layer, output, transform_context, options)
    else:
        # Use writeAsVectorFormat for QGIS versions < 3.10.3 for backwards compatibility
        result = QgsVectorFileWriter.writeAsVectorFormat(layer, output,
                                                         fileEncoding=encoding, attributes=attrs, driverName=driver)
    # Return result tuple
    return result


@feedback.inject
def exportVector(layer: BridgeLayer, fields: List[str],
                 force_shp: bool = False, target_path: str = None, **kwargs) -> Path:
    """
    Exports the given vector layer (no checks performed!) to a Shapefile or GeoPackage.

    :param layer:       The BridgeLayer (QgsVectorLayer) instance to export.
    :param fields:      Field names in order of appearance which must be included in the export.
    :param force_shp:   Instructs the exporter to always write a Shapefile.
                        If False (default), the exporter writes a GeoPackage.
    :param target_path: If unspecified (default), the output will be written to a temporary folder:
                            - If 'force_shp' is True, a Shapefile will be exported to that folder.
                            - If 'force_shp' is False, a GeoPackage *with a single table* will be exported.
                        If specified, the output will be written to the given target path:
                            - If 'force_shp' is True, 'target_path' must be a .shp file location.
                            - If 'force_shp' is False, 'target_path' must be a .gpkg file, so it adds a table to it.
                              If the .gpkg file does not yet exist, it will be created.
    :return:            The output path where the vector data was written.
    """
    logger = kwargs.get('feedback', feedback)

    orig_ext = layer.uri.suffix.lower() if layer.is_file_based else None
    if orig_ext == EXT_SHAPEFILE and force_shp and not target_path:
        # No need to export if source format == target format == shapefile and no target path was set
        logger.logInfo(f"Layer {layer.name()} already is a {orig_ext} and can be published directly from {layer.uri}")
        return Path(layer.uri)

    # Determine output extension and check if valid
    ext = EXT_SHAPEFILE if force_shp else EXT_GEOPACKAGE
    if target_path and not target_path.endswith(ext):
        raise RuntimeError(f"target path {target_path} does not have extension {ext}")

    # Perform GeoPackage or Shapefile export
    output = target_path or tempFileInSubFolder(layer.file_slug + ext)
    result = _writeVector(layer, fields, output)

    # Check if first item in result tuple is an error code
    if result[0] == QgsVectorFileWriter.NoError:
        logger.logInfo(f"Layer {layer.name()} exported to {output}")
    else:
        # Dump the result tuple as-is when there are errors (the tuple size depends on the QGIS version)
        logger.logError(f"Layer {layer.name()} failed to export.\n\tResult object: {str(result)}")

    return Path(output)


@feedback.inject
def exportRaster(layer: BridgeLayer, target_path: str = None, **kwargs) -> Path:
    """
    Exports the given raster layer (no checks performed!) to a GeoTIFF.
    If the input layer already *is* a GeoTIFF, this function does nothing an returns the original source path.

    :param layer:       The QgsRasterLayer instance to export.
    :param target_path: An optional output path where the GeoTIFF should be written (must include .tif).
                        If not specified (default), a temporary path is created.
    :return:            The output path where the TIF was written (or the original source path).
    """
    logger = kwargs.get('feedback', feedback)

    orig_ext = layer.uri.suffix.lower() if layer.is_file_based else None
    if orig_ext == EXT_GEOTIFF and not target_path:
        logger.logInfo(f"Layer {layer.name()} already is a GeoTIFF and can be published directly from {layer.uri}")
        return Path(layer.uri)

    output = target_path or tempFileInSubFolder(layer.file_slug + EXT_GEOTIFF)
    writer = QgsRasterFileWriter(output)
    writer.setOutputFormat(DRIVER_GEOTIFF)
    try:
        # For QGIS versions >= 3.8, pass transform context argument
        result = writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs(),
                                    transformContext=QgsProject.instance().transformContext())
    except AttributeError:
        # For QGIS versions < 3.8, do not use transform context
        result = writer.writeRaster(layer.pipe(), layer.width(), layer.height(), layer.extent(), layer.crs())

    # Return type is WriterError (int)
    if result == QgsRasterFileWriter.NoError:
        logger.logInfo(f"Layer {layer.name()} exported to {output}")
    else:
        # Dump the result tuple as-is when there are errors (the tuple size depends on the QGIS version)
        logger.logError(f"Layer {layer.name()} failed to export.\n\tGDAL return code: {result}")
    del writer

    return Path(output)


class ExportResult(NamedTuple):
    """ GeoPackager export result object.

    :param first_export:    True if it was the first time that a layer was exported to the GeoPackage output path.
    :param gpkg_path:       The temporary GeoPackage output path or `None` if the export failed.
    """
    first_export: bool = True
    gpkg_path: Union[str, None] = None


class GeoPackager:
    def __init__(self, items: Iterable[Union[str, BridgeLayer]], item_fields: dict):
        self._gpk_id_map = {}
        self._id_gpk_out = {}
        self._field_map = item_fields
        for item in items:
            if isinstance(item, str):
                # If GeoPackager is instantiated with a list of UUID's, fetch the layer objects
                item = layerById(item)
            if not item or item.is_raster or not item.uri:
                # Only support vector layers with a valid source
                continue
            layer_id = item.id()
            self._id_gpk_out[layer_id] = None
            uri_key = self._fix_uri(item)
            self._gpk_id_map.setdefault(uri_key, set()).add(layer_id)

    @staticmethod
    def _fix_uri(layer: BridgeLayer) -> Union[QgsDataSourceUri, Path]:
        """ Returns the parent Path of layer.uri if layer.uri is not a GeoPackage path, or layer.uri otherwise. """
        return layer.uri.parent if isinstance(layer.uri, Path) and layer.uri.suffix != EXT_GEOPACKAGE else layer.uri

    @staticmethod
    def _gpkg_out(uri: Union[QgsDataSourceUri, Path]):
        """ Returns a temporary GeoPackage output path for the given layer source URI. """
        if isinstance(uri, QgsDataSourceUri):
            # Layer source is a PostGIS database
            schema = f"_{uri.schema}" if uri.schema else ""
            gpkg = f"{uri.database}{schema}{EXT_GEOPACKAGE}"
        else:
            # Layer source is a GeoPackage or a directory (assumes _fix_uri() has been called already!)
            gpkg = uri.name
        return tempFileInSubFolder(gpkg)

    def export(self, layer: BridgeLayer) -> ExportResult:
        """ Exports the given (vector) layer to a temporary GeoPackage file and returns the .gpkg path.

        If it detects that more layers can be combined into the same GeoPackage, it will also immediately export these.
        Upon calling 'export()' on the other layers, no export will take place and the target GeoPackage
        path will be returned immediately.
        Layer sources from the same originating GeoPackage, file directory or PostGIS database+schema are
        combined into the same output GeoPackage.

        If `None` is returned, it means that the layer could not be exported to a GeoPackage.
        This can happen when the layer is not present in the GeoPackager, because it was unsupported.
        In that case, the layer should be exported in another way (e.g. Shapefile).

        :param layer:       The layer to export to a GeoPackage.
        :return:            An ExportResult object.
        """
        cur_id = layer.id()
        lyr_src = self._fix_uri(layer)
        try:
            gpk_out = self._id_gpk_out[cur_id]
        except KeyError:
            # Layer is not supported or does not participate in the publish process
            return ExportResult()
        if gpk_out:
            # Layer has been exported to GeoPackage already: return the output path
            return ExportResult(False, gpk_out)

        # Determine an output path based on the source URI
        gpk_out = self._gpkg_out(lyr_src)

        # Combine all layers from the same source (db schema, folder, GeoPackage) into the same GeoPackage export
        for lyr_id in self._gpk_id_map[lyr_src]:
            lyr = layerById(lyr_id)
            fields = fieldsForLayer(lyr, self._field_map)
            result = _writeVector(lyr, fields, gpk_out)
            if result[0] == QgsVectorFileWriter.NoError:
                self._id_gpk_out[lyr.id()] = gpk_out

        return ExportResult(gpkg_path=self._id_gpk_out.get(cur_id))
