import os
import string


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
