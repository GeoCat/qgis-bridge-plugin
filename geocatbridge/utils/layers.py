from pathlib import Path
from typing import Union, Tuple, List

from qgis.core import (
    QgsProject,
    QgsMapLayer,
    QgsLayerTreeLayer,
    QgsLayerTreeGroup,
    QgsDataSourceUri
)

from geocatbridge.utils import strings


class BridgeLayer:
    def __new__(cls, qgis_layer):
        """ Wrapper for a QGIS layer (QgsMapLayer, QgsVectorLayer, QgsRasterLayer etc.) that
        sets some protected attributes and adds some properties to the layer that are often required by Bridge,
        and immediately returns the modified layer instance.

        Note that the type will be that of the 'qgis_layer'!
        This means that `isinstance(<val>, BridgeLayer)` will always return False.

        :param qgis_layer:  QgsMapLayer instance or one of its inheritors.
        """
        qgis_layer.__dataset_name, qgis_layer.__source_uri = cls._parse_source(qgis_layer)
        qgis_layer.__web_slug = strings.layer_slug(qgis_layer)
        qgis_layer.__file_slug = strings.layer_slug(qgis_layer, False)
        for pname, pval in cls.__dict__.items():
            if isinstance(pval, property):
                setattr(qgis_layer.__class__, pname, pval)
        return qgis_layer

    def __getattr__(self, attr):
        # Prevent IDE's from showing errors for missing methods or attributes on the QgsMapLayer
        return getattr(self, attr)

    @staticmethod
    def _parse_source(layer) -> Tuple[str, Union[Path, QgsDataSourceUri, None]]:
        """ Analyzes the layer source and returns either a Path or a QgsDataSourceUri instance (or None). """
        source = layer.source()

        # Source may be a PostgreSQL database
        if layer.dataProvider().name() == "postgres":
            try:
                db_source = QgsDataSourceUri(source)
                return db_source.table, db_source
            except Exception:  # noqa
                return '', None

        # Source *may be* file-based
        try:
            parts = source.split("|")
            src_path = Path(parts[0])
            if not src_path.exists():
                return '', None
            ds_name = {k: v for k, v in (p.split('=') for p in parts[1:])}.get('layername', src_path.stem)
            return ds_name, src_path
        except Exception:  # noqa
            return '', None

    @property
    def web_slug(self) -> str:
        """ Returns a version of the layer name that is safe to use in URL paths.

        The output string conforms to RFC-3986 (limited set of ASCII-only chars).
        Any character that does not comply is replaced by an underscore.
        If the output string would otherwise start with a non-alpha character, it will be prepended by an 'L'.
        """
        return self.__web_slug

    @property
    def file_slug(self) -> str:
        """ Returns a version of the layer name that is safe to use in local file paths.

        The output string will only contain digits, ASCII letters, underscores and hyphens.
        Any character that does not comply is replaced by an underscore.
        If the output string would otherwise start with a non-alpha character, it will be prepended by an 'L'.

        Note that although spaces and dots technically are allowed in file names,
        they are replaced by underscores here. This is done to avoid potential problems
        with double file extensions or unquoted paths in shell commands, for example.
        """
        return self.__file_slug

    @property
    def is_vector(self) -> bool:
        """ Returns True if it's a vector layer. """
        return self.type() == QgsMapLayer.VectorLayer  # noqa

    @property
    def is_raster(self) -> bool:
        """ Returns True if it's a raster layer. """
        return self.type() == QgsMapLayer.RasterLayer  # noqa

    @property
    def is_postgis_based(self) -> bool:
        """ Returns True if the layer source is stored in a PostGIS database. """
        return isinstance(self.__source_uri, QgsDataSourceUri)

    @property
    def is_file_based(self) -> bool:
        """ Returns True if the layer source is file-based (e.g. GeoPackage, Shapefile, GeoTIFF, etc.). """
        return isinstance(self.__source_uri, Path)

    @property
    def uri(self) -> Union[Path, QgsDataSourceUri, None]:
        """ Returns the layer source path or database connection details.
        May return None if the layer data provider is not supported. """
        return self.__source_uri

    @property
    def dataset_name(self):
        """ Returns the layer source dataset name.
        For a PostGIS data provider, this will be the table name.
        For a file-based source, this will be the name of the file without the extension (i.e. stem).
        For a GeoPackage, this will be the name of the layer inside the .gpkg file.
        """
        return self.__dataset_name

    @property
    def can_publish(self) -> bool:
        """ Returns True if the layer can be published with Bridge,
        assuming that the layer is also supported (see isSupportedLayer()).
        This is the case if the __dataset_name and __source_uri have been set.
        """
        return self.__dataset_name and self.__source_uri and (self.is_vector or self.is_raster)


def isSupportedLayer(layer):
    """ Returns True if the given layer is supported by Bridge.

    Supported layers are valid, non-temporary spatial vector or raster layers with a spatial reference.
    Their source can be taken from disk or a database, but not from a web service (e.g. WM(T)S).
    """
    if not layer:
        return False
    return layer.isValid() and layer.isSpatial() and layer.crs().isValid() and not layer.isTemporary() and \
        layer.type() in (QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer) and layer.dataProvider().name() != "wms"


def listBridgeLayers() -> List[BridgeLayer]:
    """ Returns a flattened list of supported publishable layers in the current QGIS project.

    See `isSupportedLayer()` to find out which layers are supported.
    """
    def _layersFromTree(layer_tree):
        _layers = []
        for child in layer_tree.children():
            if isinstance(child, QgsLayerTreeLayer):
                bridge_layer = BridgeLayer(child.layer())
                if isSupportedLayer(bridge_layer) and bridge_layer.can_publish:
                    _layers.append(bridge_layer)
            elif isinstance(child, QgsLayerTreeGroup):
                _layers.extend(_layersFromTree(child))
        return _layers

    root = QgsProject().instance().layerTreeRoot()
    return _layersFromTree(root)


def layerById(layer_id: str, publishable_only: bool = True) -> Union[None, BridgeLayer, QgsMapLayer]:
    """ Finds a layer object in the TOC by QGIS ID and returns it.

    :param layer_id:            The unique ID for the layer to search within the current QGIS project.
    :param publishable_only:    If True, only search within publishable layers (default).
    :returns:                   A BridgeLayer (if 'publishable_only' is True), QgsMapLayer or None if not found.
    """
    for lyr in (listBridgeLayers() if publishable_only else QgsProject().instance().mapLayers().values()):
        if lyr.id() == layer_id:
            return lyr
    return None
