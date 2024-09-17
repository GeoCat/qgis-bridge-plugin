import json as _json
from typing import Dict as _Dict, List, Tuple
from xml.dom import minidom
from xml.etree import ElementTree as ETree

# Maps required bridgestyle functionality to a more convenient geocatbridge.publish.style namespace.
# This also makes sure that we are importing the bridgestyle lib matching this version of GeoCat Bridge.
from geocatbridge.libs.bridgestyle.bridgestyle.qgis import *  # noqa
from geocatbridge.utils import layers as _lyr
from geocatbridge.utils import meta as _meta

# Shortcuts to other functions that were imported by doing import * above
convertDictToMapfile = mapserver.fromgeostyler.convertDictToMapfile
convertStyle = togeostyler.convert


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


# noinspection HttpUrlsUsage
def layerStyleAsSld(layer: _lyr.BridgeLayer, lowercase_props: bool = False) -> Tuple[str, dict, list]:
    """ Function override of bridgestyle.qgis.layerStyleAsSld() to convert a QGIS layer style to an SLD string.
    Circumvents bridgestyle.sld.fromgeostyler.convert(), so we can properly set the layer name, title, and abstract.

    :param layer:           The Bridge layer for which to export an SLD.
    :param lowercase_props: For some styles, it may be necessary to use lowercase property names for attributes.
                            If that is the case, set this to True (defaults to False).
    """
    geostyler, icons, sprites, warnings = convertStyle(layer)

    # Code below overrides bridgestyle.sld.fromgeostyler.convert()
    attribs = {
        "version": "1.0.0",
        "xsi:schemaLocation": "http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd",
        "xmlns": "http://www.opengis.net/sld",
        "xmlns:ogc": "http://www.opengis.net/ogc",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    root = ETree.Element("StyledLayerDescriptor", attrib=attribs)
    named_layer = ETree.SubElement(root, "NamedLayer")
    layer_name = ETree.SubElement(named_layer, "Name")
    layer_name.text = layer.web_slug if hasattr(layer, 'web_slug') else layer.name()
    user_style = ETree.SubElement(named_layer, "UserStyle")
    props = {
        "Title": layer.title().strip() or layer.name(),
        "Abstract": layer.abstract()
    }
    for pname, pvalue in props.items():
        if not pvalue:
            continue
        element = ETree.SubElement(user_style, pname)
        element.text = pvalue

    feature_type_style = ETree.SubElement(user_style, "FeatureTypeStyle")
    transformation = geostyler.get("transformation", {})
    if transformation:
        feature_type_style.append(sld.fromgeostyler.processTransformation(transformation))
    for rule in geostyler.get("rules", []):
        feature_type_style.append(sld.fromgeostyler.processRule(rule))
    if lowercase_props:
        # Convert property names to lowercase in order to match the feature type attributes if needed
        for p in feature_type_style.iter("ogc:PropertyName"):
            p.text = p.text.lower()
    sld.fromgeostyler._addVendorOption(feature_type_style, "composite", geostyler.get("blendMode"))  # noqa

    # Convert ElementTree to XML string (use minidom for proper formatting)
    root.insert(0, ETree.Comment(f"Generated by {_meta.getLongAppNameWithCurrentVersion()} "
                                 f"with bridgestyle {sld.fromgeostyler.__version__}"))
    sld_string = ETree.tostring(root, encoding="utf-8", method="xml").decode()
    dom = minidom.parseString(sld_string)
    return dom.toprettyxml(indent="  ", encoding="utf-8").decode(), icons, warnings


def saveLayerStyleAsZippedSld(layer: _lyr.BridgeLayer, target_file: str, lowercase_props: bool = False) -> List[str]:
    """ Function override of bridgestyle.qgis.saveLayerStyleAsZippedSld().

    :param layer:           The Bridge layer for which to export an SLD.
    :param target_file:     Path to the output zip file.
    :param lowercase_props: For some styles, it may be necessary to use lowercase property names for attributes.
                            If that is the case, set this to True (defaults to False).
    """
    sld_string, icons, warnings = layerStyleAsSld(layer, lowercase_props)
    with zipfile.ZipFile(target_file, "w") as z:
        for icon in icons.keys():
            if icon:
                z.write(icon, os.path.basename(icon))
        z.writestr(layer.file_slug + ".sld", sld_string)
    return warnings
