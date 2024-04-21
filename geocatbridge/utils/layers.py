from re import compile
from pathlib import Path
from itertools import chain
from functools import partial
from typing import Union, Tuple, List, Iterable, FrozenSet
from collections import namedtuple

from qgis.core import (
    QgsProject,
    QgsMapLayer,
    QgsLayerTreeLayer,
    QgsLayerTreeGroup,
    QgsDataSourceUri
)

from geocatbridge.utils import strings

LAYERNAME_REGEX = compile(r'^layername=(.*)$')


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
        # Override title, abstract and keyword methods, so they look in metadata instead
        qgis_layer.title = qgis_layer.metadata().title
        qgis_layer.abstract = qgis_layer.metadata().abstract
        qgis_layer.keywords = partial(cls.keywords, qgis_layer)
        return qgis_layer

    def __getattr__(self, attr):
        # Prevent IDE's from showing errors for missing methods or attributes on the QgsMapLayer
        return getattr(self, attr)

    def keywords(self) -> List[str]:
        """ Returns a list of all keywords in the metadata. """
        return sorted([v.strip() for v in chain.from_iterable(self.metadata().keywords().values())])

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
            ds_name = next((m.group(1) for m in (LAYERNAME_REGEX.match(p) for p in parts[1:]) if m and m.groups()), src_path.stem)  # noqa
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


LayerGroup = namedtuple('LayerGroup', 'name title abstract layers')


class LayerGroups(list):
    def __init__(self, lyrid_filter: Iterable[str] = None, slug_map: dict = None):
        """
        Creates a list of LayerGroup objects for the current QGIS project.

        On init, the QGIS TOC will be searched for layer groups. If a list of QGIS layer IDs is provided,
        only the layers that are in the list will be added to a group object. All other layers will be ignored.
        If no IDs are specified, all groups and layers will be included.

        :param lyrid_filter:    Iterable of QGIS layer IDs that will participate in the output object.
        :param slug_map:        Optional lookup dictionary to map the original layer slugs (names) to
                                the feature type names that were given on the server.
        """
        super().__init__()
        self._lyrnames: set[str] = set()
        lyrid_filter = frozenset(lyrid_filter or [])
        root = QgsProject().instance().layerTreeRoot()
        for element in self._reversed_iter(root):
            self._group(element, lyrid_filter, slug_map or {})

    @staticmethod
    def _reversed_iter(element):
        """ Returns a generator of child elements for the given element in a reversed order.
        GeoServer requires a reversed layer stacking order compared to QGIS.
        """
        children = element.children()
        children.reverse()
        for child in children:
            yield child

    def _group(self, layer_tree: QgsLayerTreeGroup, lyrid_filter: FrozenSet[str], slug_map: dict, parent: list = None):
        if not isinstance(layer_tree, QgsLayerTreeGroup):
            return
        parent = self if parent is None else parent

        # Walk child elements
        layers = []
        for child in self._reversed_iter(layer_tree):
            if isinstance(child, QgsLayerTreeLayer):
                child_layer = BridgeLayer(child.layer())
                if not lyrid_filter or (child_layer.id() in lyrid_filter):
                    name = slug_map.get(child_layer.web_slug, child_layer.web_slug)
                    layers.append(name)
                    self._lyrnames.add(name)
            elif isinstance(child, QgsLayerTreeGroup):
                self._group(child, lyrid_filter, slug_map, layers)

        if not layers or (len(layers) == 1 and isinstance(layers[0], str) and layers[0] in self._lyrnames):
            return  # Less than 2 layers or no subgroups encountered in child elements

        # Append a (sub)group object
        parent.append(
            LayerGroup(
                name=strings.layer_slug(layer_tree),
                title=layer_tree.customProperty("wmsTitle", layer_tree.name()),
                abstract=layer_tree.customProperty("wmsAbstract", layer_tree.name()),
                layers=layers
            )
        )


def isSupportedLayer(layer):
    """ Returns True if the given layer is supported by Bridge.

    Supported layers are valid, non-temporary spatial vector or raster layers with a spatial reference.
    Their source can be taken from disk or a database, but not from a web service (e.g. WM(T)S).
    """
    if not layer:
        return False
    if layer.isTemporary():
        uri = layer.source()
        try:
            if not (uri and Path(uri).exists()):
                # Temporary layers are only supported if the source is an actual path (on disk)
                return False
        except OSError:
            # If the path is invalid (e.g. too long), the layer is not supported either way [#004035]
            return False
    return (layer.isValid() and layer.isSpatial() and layer.crs().isValid() and
            layer.type() in (QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer) and
            layer.dataProvider().name() != "wms")


def listLayerNames(layer_ids: Iterable[str] = None, actual: bool = False) -> List[str]:
    """
    Returns a list of layer names for the given QGIS layer IDs.
    If no list of IDs was specified, all publishable layer names will be returned.

    :param layer_ids:   Optional list of QGIS layer IDs that must be included in the result.
    :param actual:      If True, the QGIS layer name will be returned (as shown in the TOC).
                        If False, the web-safe name will be returned (default).
    :return:            A list of layer names.
    """
    return [(lyr.name() if actual else lyr.web_slug) for lyr in listBridgeLayers(layer_ids)]


def listGroupNames(layer_ids: Iterable[str] = None, actual: bool = False) -> List[str]:
    """
    Returns a list of layer group names for the given QGIS layer IDs, if any have been grouped.
    If no list of IDs was specified, all layer group names in the TOC will be returned.

    :param layer_ids:   Optional list of QGIS layer IDs whose parent groups must be included.
    :param actual:      If True, the QGIS group name will be returned (as shown in the TOC).
                        If False, the web-safe name will be returned.
    :return:            A list of group names.
    """
    return [(g.title if actual else g.name) for g in LayerGroups(layer_ids)]


def listBridgeLayers(filter_ids: Iterable[str] = None) -> List[BridgeLayer]:
    """ Returns a flattened list of supported publishable layers in the current QGIS project.

    See `isSupportedLayer()` to find out which layers are supported.

    :param filter_ids:  Optional list of QGIS layer IDs for layer that should be included in the output.
                        If omitted, all publishable layers will be returned.
    """
    def _layersFromTree(layer_tree):
        _layers = []
        for child in layer_tree.children():
            if isinstance(child, QgsLayerTreeLayer):
                bridge_layer = BridgeLayer(child.layer())
                if not (isSupportedLayer(bridge_layer) and bridge_layer.can_publish) or \
                        (filter_ids and bridge_layer.id() not in filter_ids):
                    continue
                _layers.append(bridge_layer)
            elif isinstance(child, QgsLayerTreeGroup):
                _layers.extend(_layersFromTree(child))
        return _layers

    filter_ids = frozenset(filter_ids or [])
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
