import os
import zipfile
from xml.dom import minidom
from multistyler.qgis.geostyler import layerAsGeostyler
from multistyler.sld.sld import processLayer
from xml.etree import ElementTree

def layerStyleAsSld(layer):
    geostyler, icons, warnings = layerAsGeostyler(layer)
    xml = processLayer(geostyler)
    sld = ElementTree.tostring(xml, encoding='utf8', method='xml').decode()
    dom = minidom.parseString(sld)
    return dom.toprettyxml(), icons, warnings    

def saveLayerStyleAsSld(layer, filename):
    sld, icons, warnings = layerStyleAsSld(layer)       
    with open(filename, "w") as f:
        f.write(sld)
    return warnings

def saveLayerStyleAsZippedSld(layer, filename):
    sld, icons, warnings = layerStyleAsSld(layer)
    z = zipfile.ZipFile(filename, "w")
    for icon in icons:
        z.write(icon, os.path.basename(icon))
    z.writestr(layer.name() + ".sld", sld)
    z.close()
    return warnings