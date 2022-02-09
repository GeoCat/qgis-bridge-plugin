from typing import Dict as _Dict
import json as _json

# Maps required bridgestyle functionality to a more convenient geocatbridge.publish.style namespace.
# This also makes sure that we are importing the bridgestyle lib matching this version of GeoCat Bridge.
from geocatbridge.libs.bridgestyle.bridgestyle.qgis import *  # noqa

from geocatbridge.utils import layers as _lyr

# Shortcuts to other functions that were imported by doing import * above
convertDictToMapfile = mapserver.fromgeostyler.convertDictToMapfile
convertStyle = togeostyler.convert


# def layerStyleAsMapboxFolder(layer, folder):
#     """
#
#
#     :param layer:
#     :param folder:
#     :return:
#     """
#     geostyler, icons, sprites, warnings = togeostyler.convert(layer)
#     mbox, mbWarnings = mapboxgl.fromgeostyler.convert(geostyler)
#     filename = os.path.join(folder, "style.mapbox")
#     with open(filename, "w", encoding='utf-8') as f:
#         f.write(mbox)
#     return warnings


def convertMapboxGroup(group: _lyr.LayerGroup, layers: _Dict[str, _lyr.BridgeLayer], base_url: str, workspace: str):
    """ Reimplementation of the mapbox.convertGroup bridgestyle function,
    that is more robust and less sensitive to changes in Bridge.

    :param group:       LayerGroup object to publish as a Mapbox style.
    :param layers:      Lookup of layer name (in group) and BridgeLayer objects.
    :param base_url:    The GeoServer base URL to append to the URIs.
    :param workspace:   The GeoServer workspace name to publish to.
    """
    obj = {
        "version": 8,
        "glyphs": "mapbox://fonts/mapbox/{fontstack}/{range}.pbf",
        "name": group.name,
        "sources": {
            mapboxgl.fromgeostyler.SOURCE_NAME: {
                "type": "vector",
                "tiles": [
                    mapboxgl.fromgeostyler.tileURLFull(base_url, workspace, group.name)
                ],
                "minZoom": 0,
                "maxZoom": 20  # TODO: Determine from style?
            },
        },
        "sprite": mapboxgl.fromgeostyler.spriteURLFull(base_url, workspace, group.name),
        "layers": []
    }

    geostylers = {}
    all_sprites = {}
    all_warnings = set()

    # Build GeoStyler and Mapbox styles
    for layer_name in (name for name in group.layers if isinstance(name, str)):
        layer = layers.get(layer_name)
        if not layer:
            all_warnings.add(f"Mapbox group layer '{layer_name}' not found")
            continue
        # Clone the layer and make sure that the QGIS name matches the published name
        layer_clone = layer.clone()
        layer_clone.setName(layer_name)
        # Convert layer style using bridgestyle
        try:
            geostyler, icons, sprites, warnings = convertStyle(layer_clone)
            all_sprites.update(sprites)  # combine/accumulate sprites
            geostylers[layer_clone.name()] = geostyler
            mbox, mb_warnings = mapboxgl.fromgeostyler.convert(geostyler)
            all_warnings.update(mb_warnings)
            mbox_obj = _json.loads(mbox)
            obj["layers"].extend(mbox_obj.get("layers", []))
        except Exception as err:
            all_warnings.add(f"Could not create Mapbox style for layer '{layer_name}': {err}")

    return _json.dumps(obj, indent=4), all_warnings, mapboxgl.fromgeostyler.toSpriteSheet(all_sprites)
