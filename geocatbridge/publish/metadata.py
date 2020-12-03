import os
import uuid
import zipfile
from datetime import datetime
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import lxml.etree as ET
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QImage, QColor, QPainter
from qgis.core import (
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    Qgis,
    QgsMessageLog
)

from ..utils.files import tempFilenameInTempFolder, getResourcePath

QMD_TO_ISO19139_XSLT = getResourcePath("qgis-to-iso19139.xsl")
ISO19139_TO_QMD_XSLT = getResourcePath("iso19139-to-qgis.xsl")
ISO19115_TO_ISO19139_XSLT = getResourcePath("iso19115-to-iso19139.xsl")
WRAPPING_ISO19115_TO_ISO19139_XSLT = getResourcePath("ISO19115-wrapping-MD_Metadata-to-ISO19139.xslt")
FGDC_TO_ISO19115 = getResourcePath("ArcCatalogFgdc_to_ISO19115.xsl")


def uuidForLayer(layer):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, layer.source()))


def loadMetadataFromXml(layer, filename):
    root = ElementTree.parse(filename).getroot()

    def _hasTag(tag):
        for _ in root.iter(tag):
            return True
        return False

    if _hasTag("esri"):
        if _hasTag("gmd:MD_Metadata"):
            _loadMetadataFromWrappingEsriXml(layer, filename)
        else:
            _loadMetadataFromEsriXml(layer, filename)
    elif _hasTag("MD_Metadata") or _hasTag("gmd:MD_Metadata"):
        _loadMetadataFromIsoXml(layer, filename)
    elif _hasTag("metadata/mdStanName"):
        schema_name = list(root.iter("metadata/mdStanName"))[0].text
        if "FGDC-STD" in schema_name:
            _loadMetadataFromFgdcXml(layer, filename)
        elif "19115" in schema_name:
            _loadMetadataFromIsoXml(layer, filename)
    else:
        _loadMetadataFromFgdcXml(layer, filename)


def saveMetadata(layer, mef_filename=None, api_url=None, wms=None, wfs=None, layer_name=None):
    uuid = uuidForLayer(layer)
    filename = tempFilenameInTempFolder(layer.name() + ".qmd")
    layer.saveNamedMetadata(filename)
    thumbnail = _saveLayerThumbnail(layer)
    api_url = api_url or ""
    transformed_filename = _transformMetadata(filename, uuid, api_url, wms, wfs, layer_name or layer.name())
    mef_filename = mef_filename or tempFilenameInTempFolder(uuid + ".mef")
    _createMef(uuid, transformed_filename, mef_filename, thumbnail)
    return mef_filename


def _transformDom(input_file, xslt_file):
    in_dom = ET.parse(input_file)
    xslt = ET.parse(xslt_file)
    transform = ET.XSLT(xslt)
    out_dom = transform(in_dom)
    if not out_dom:
        raise Exception("Failed to convert metadata")
    return out_dom


def _writeDom(dom, output_file):
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(dom, pretty_print=True).decode()
    with open(output_file, "w", encoding="utf8") as f:
        f.write(s)


def _convertMetadata(input_file, output_file, xslt_file):
    out_dom = _transformDom(input_file, xslt_file)
    _writeDom(out_dom, output_file)


def _loadMetadataFromIsoXml(layer, filename):
    qmd_filename = tempFilenameInTempFolder("fromiso.qmd")
    QgsMessageLog.logMessage("Exporting ISO19193 metadata to %s" % qmd_filename, 'GeoCat Bridge', level=Qgis.Info)
    _convertMetadata(filename, qmd_filename, ISO19139_TO_QMD_XSLT)
    layer.loadNamedMetadata(qmd_filename)


def _loadMetadataFromEsriXml(layer, filename):
    iso_filename = tempFilenameInTempFolder("fromesri.xml")
    QgsMessageLog.logMessage("Exporting ISO19115 metadata to %s" % iso_filename, 'GeoCat Bridge', level=Qgis.Info)
    _convertMetadata(filename, iso_filename, ISO19115_TO_ISO19139_XSLT)
    _loadMetadataFromIsoXml(layer, iso_filename)


def _loadMetadataFromWrappingEsriXml(layer, filename):
    iso_filename = tempFilenameInTempFolder("fromesri.xml")
    QgsMessageLog.logMessage("Exporting Wrapping-ISO19115 metadata to %s" % iso_filename, 'GeoCat Bridge',
                             level=Qgis.Info)
    _convertMetadata(filename, iso_filename, WRAPPING_ISO19115_TO_ISO19139_XSLT)
    _loadMetadataFromIsoXml(layer, iso_filename)


def _loadMetadataFromFgdcXml(layer, filename):
    iso_filename = tempFilenameInTempFolder("fromfgdc.xml")
    QgsMessageLog.logMessage("Exporting FGDC metadata to %s" % iso_filename, 'GeoCat Bridge', level=Qgis.Info)
    _convertMetadata(filename, iso_filename, FGDC_TO_ISO19115)
    _loadMetadataFromEsriXml(layer, iso_filename)


def _saveLayerThumbnail(layer):
    filename = tempFilenameInTempFolder("thumbnail.png")
    img = QImage(QSize(800, 800), QImage.Format_A2BGR30_Premultiplied)
    color = QColor(255, 255, 255, 255)
    img.fill(color.rgba())
    p = QPainter()
    p.begin(img)
    p.setRenderHint(QPainter.Antialiasing)
    ms = QgsMapSettings()
    ms.setBackgroundColor(color)
    ms.setLayers([layer])
    ms.setExtent(layer.extent())
    ms.setOutputSize(img.size())
    render = QgsMapRendererCustomPainterJob(ms, p)
    render.start()
    render.waitForFinished()
    p.end()
    img.save(filename)
    return filename


def _transformMetadata(filename, uuid, api_url, wms, wfs, layer_name):

    def _ns(n):
        return '{http://www.isotc211.org/2005/gmd}' + n

    def _addServiceElement(root_element, md_layer, service_url, service_type):
        trans = ET.SubElement(root_element, _ns('transferOptions'))
        dtrans = ET.SubElement(trans, _ns('MD_DigitalTransferOptions'))
        online = ET.SubElement(dtrans, _ns('onLine'))
        cionline = ET.SubElement(online, _ns('CI_OnlineResource'))
        linkage = ET.SubElement(cionline, _ns('linkage'))
        url = ET.SubElement(linkage, _ns('URL'))
        url.text = service_url
        protocol = ET.SubElement(cionline, _ns('protocol'))
        cs = ET.SubElement(protocol, '{http://www.isotc211.org/2005/gco}CharacterString')
        cs.text = f"OGC:{service_type.upper()}"
        name = ET.SubElement(cionline, _ns('name'))
        csname = ET.SubElement(name, '{http://www.isotc211.org/2005/gco}CharacterString')
        csname.text = md_layer

    iso_filename = tempFilenameInTempFolder("metadata.xml")
    out_dom = _transformDom(filename, iso_filename)

    for ident in out_dom.iter(_ns('fileIdentifier')):
        ident[0].text = uuid
    if wms is not None:
        for root in out_dom.iter(_ns('MD_Distribution')):
            _addServiceElement(root, layer_name, wms, 'wms')
    if wfs is not None:
        for root in out_dom.iter(_ns('MD_Distribution')):
            _addServiceElement(root, layer_name, wfs, 'wfs')
    for root in out_dom.iter(_ns('MD_DataIdentification')):
        overview = ET.SubElement(root, _ns('graphicOverview'))
        browse_graphic = ET.SubElement(overview, _ns('MD_BrowseGraphic'))
        file = ET.SubElement(browse_graphic, _ns('fileName'))
        cs = ET.SubElement(file, '{http://www.isotc211.org/2005/gco}CharacterString')
        thumbnail_url = "%s/records/%s/attachments/thumbnail.png" % (api_url, uuid)
        cs.text = thumbnail_url

    _writeDom(out_dom, iso_filename)
    return iso_filename


def _createMef(uuid, md_filename, mef_filename, thumb_filename):
    z = zipfile.ZipFile(mef_filename, "w")
    z.write(md_filename, os.path.join(uuid, "metadata", os.path.basename(md_filename)))
    z.write(thumb_filename, os.path.join(uuid, "public", os.path.basename(thumb_filename)))
    info = _getInfoXmlContent(uuid, thumb_filename)
    z.writestr(os.path.join(uuid, "info.xml"), info)
    z.close()


def _addSubElement(parent, tag, value=None, attrib=None):
    sub = SubElement(parent, tag, attrib=attrib or {})
    if value is not None:
        sub.text = value
    return sub


def _getInfoXmlContent(uuid, thumb_filename):
    root = Element("info", {"version": "1.1"})
    general = _addSubElement(root, "general")
    d = datetime.now().isoformat()
    _addSubElement(general, "changeDate", d)
    _addSubElement(general, "createDate", d)
    _addSubElement(general, "schema", "iso19139")
    _addSubElement(general, "isTemplate", "n")
    _addSubElement(general, "format", "full")
    _addSubElement(general, "localId")
    _addSubElement(general, "uuid", uuid)
    _addSubElement(general, "siteId", "GeoCat Bridge")
    _addSubElement(general, "siteName", "GeoCat Bridge")
    _addSubElement(root, "categories")
    privs = _addSubElement(root, "privileges")
    grp = _addSubElement(privs, "group", attrib={"name": "all"})
    _addSubElement(grp, "operation", attrib={"name": "dynamic"})
    _addSubElement(grp, "operation", attrib={"name": "featured"})
    _addSubElement(grp, "operation", attrib={"name": "view"})
    _addSubElement(grp, "operation", attrib={"name": "download"})
    public = _addSubElement(root, "public")
    _addSubElement(public, "file", attrib={"name": os.path.basename(thumb_filename), "changeDate": d})
    _addSubElement(root, "private")
    xmlstring = ElementTree.tostring(root, encoding='UTF-8', method='xml').decode()
    dom = minidom.parseString(xmlstring)
    return dom.toprettyxml(indent="  ")
