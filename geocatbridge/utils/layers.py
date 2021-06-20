import os
import string
from typing import Union

from qgis.core import QgsProject, QgsMapLayer, QgsLayerTreeLayer, QgsLayerTreeGroup


def getLayerTitleAndName(layer):
    """ Gets the layer title and a lowercase name in which spaces have been replaced by underscores. """
    title = layer.name()
    return title, title.lower().replace(' ', '_')


def getLayerSourceInfo(layer):
    """ Returns a tuple of (path, name, extension) for the layer source file. """
    filepath = layer.source().split("|")[0]
    stem, ext = os.path.splitext(filepath.lower())
    _, name = os.path.split(stem)
    return filepath, name, ext


def hasValidLayerName(layer):
    """
    Checks if there are some problematic characters in the layer name. Returns True when layer name is OK.
    Non-ASCII chars could for instance break API URLs or cause other issues.
    """
    name = layer.name()
    correct = {c for c in string.ascii_letters + string.digits + "-_. "}
    return set(name).issubset(correct)


def getExportableLayer(layer, target_name):
    """
    Returns a modified layer clone with the given target name.
    The layer clone can be safely used for export purposes, also when the original name included spaces.
    """
    export_layer = layer.clone()
    export_layer.setName(target_name)
    return export_layer


def getPublishableLayers() -> list:
    """ Returns a flat list of supported publishable layers in the current QGIS project.

    Supported layers are valid, non-temporary spatial vector or raster layers with a spatial reference.
    Their source can be taken from disk or a database, but not from a web service (e.g. WM(T)S).
    """
    def _layersFromTree(layer_tree):
        _layers = []
        for child in layer_tree.children():
            if isinstance(child, QgsLayerTreeLayer):
                _layers.append(child.layer())
            elif isinstance(child, QgsLayerTreeGroup):
                _layers.extend(_layersFromTree(child))
        return _layers

    root = QgsProject().instance().layerTreeRoot()
    return [layer for layer in _layersFromTree(root)
            if layer and layer.isValid() and layer.isSpatial() and layer.crs().isValid() and not layer.isTemporary()
            and layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]
            and layer.dataProvider().name() != "wms"]


def getLayerById(layer_id: str, publishable_only: bool = True) -> Union[None, QgsMapLayer]:
    """ Finds a layer object by QGIS ID and returns it.

    :param layer_id:            The unique ID for the layer to search within the current QGIS project.
    :param publishable_only:    If True, only search within publishable layers (default).
    :returns:                   A QGIS layer object or None if not found.
    """
    layers = getPublishableLayers() if publishable_only else QgsProject().instance().mapLayers().values()
    for lyr in (lyr for lyr in layers if lyr.id() == layer_id):
        return lyr
    return None
