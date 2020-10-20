import os
import uuid 
import zipfile
import lxml.etree as ET
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
from datetime import datetime
from qgis.PyQt.QtGui import QImage, QColor, QPainter
from qgis.PyQt.QtCore import QSize, QCoreApplication
from qgis.core import (
    QgsMapSettings, 
    QgsMapRendererCustomPainterJob,
    Qgis,
    QgsMessageLog
)
from ..utils.files import tempFilenameInTempFolder
from ..utils.layers import getLayerTitleAndName

QMD_TO_ISO19139_XSLT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "qgis-to-iso19139.xsl")
ISO19139_TO_QMD_XSLT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "iso19139-to-qgis.xsl")
ISO19115_TO_ISO19139_XSLT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "iso19115-to-iso19139.xsl")
WRAPPING_ISO19115_TO_ISO19139_XSLT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "ISO19115-wrapping-MD_Metadata-to-ISO19139.xslt")
FGDC_TO_ISO19115 = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "ArcCatalogFgdc_to_ISO19115.xsl")

def loadMetadataFromXml(layer, filename):
    root = ElementTree.parse(filename).getroot()
    def _hasTag(tag):
        return bool(len(list(root.iter(tag))))
 
    if _hasTag("esri"):
        if _hasTag("gmd:MD_Metadata"):
            loadMetadataFromWrappingEsriXml(layer, filename)
        else:
            loadMetadataFromEsriXml(layer, filename)
    elif _hasTag("MD_Metadata") or _hasTag("gmd:MD_Metadata"):
        loadMetadataFromIsoXml(layer, filename)      
    elif _hasTag("metadata/mdStanName"):
        schemaName = list(root.iter("metadata/mdStanName"))[0].text
        if "FGDC-STD" in schemaName:
            loadMetadataFromFgdcXml(layer, filename)
        elif "19115" in schemaName:
            loadMetadataFromIsoXml(layer, filename) 
    else:
        loadMetadataFromFgdcXml(layer, filename)
            
def loadMetadataFromIsoXml(layer, filename):
    qmdFilename = tempFilenameInTempFolder("fromiso.qmd")
    QgsMessageLog.logMessage("Exporting ISO19193 metadata to %s" % qmdFilename, 'GeoCat Bridge', level=Qgis.Info)
    dom = ET.parse(filename)
    xslt = ET.parse(ISO19139_TO_QMD_XSLT)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    if newdom is None:
        raise Exception("Cannot convert metadata")
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
    with open(qmdFilename, "w", encoding="utf8") as f:
        f.write(s)
    layer.loadNamedMetadata(qmdFilename)
    
def loadMetadataFromEsriXml(layer, filename):    
    isoFilename = tempFilenameInTempFolder("fromesri.xml")
    QgsMessageLog.logMessage("Exporting ISO19115 metadata to %s" % isoFilename, 'GeoCat Bridge', level=Qgis.Info)
    dom = ET.parse(filename)
    xslt = ET.parse(ISO19115_TO_ISO19139_XSLT)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    if newdom is None:
        raise Exception("Cannot convert metadata")
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
    with open(isoFilename, "w", encoding="utf8") as f:
        f.write(s)
    loadMetadataFromIsoXml(layer, isoFilename)

def loadMetadataFromWrappingEsriXml(layer, filename):
    isoFilename = tempFilenameInTempFolder("fromesri.xml")
    QgsMessageLog.logMessage("Exporting Wrapping-ISO19115 metadata to %s" % isoFilename, 'GeoCat Bridge', level=Qgis.Info) 
    dom = ET.parse(filename)
    xslt = ET.parse(WRAPPING_ISO19115_TO_ISO19139_XSLT)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    if newdom is None:
        raise Exception("Cannot convert metadata")
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
    with open(isoFilename, "w", encoding="utf8") as f:
        f.write(s)
    loadMetadataFromIsoXml(layer, isoFilename)

def loadMetadataFromFgdcXml(layer, filename):
    isoFilename = tempFilenameInTempFolder("fromfgdc.xml")
    QgsMessageLog.logMessage("Exporting FGDC metadata to %s" % isoFilename, 'GeoCat Bridge', level=Qgis.Info)
    dom = ET.parse(filename)
    xslt = ET.parse(FGDC_TO_ISO19115)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    if newdom is None:
        raise Exception("Cannot convert metadata")
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
    with open(isoFilename, "w", encoding="utf8") as f:
        f.write(s)
    loadMetadataFromEsriXml(layer, isoFilename)   

def saveMetadataToIsoXml(layer, filename):
    pass

def saveMetadata(layer, mefFilename=None, apiUrl=None, wms=None, wfs=None, layerName=None):
    uuid = uuidForLayer(layer)
    _, safe_name = getLayerTitleAndName(layer)
    filename = tempFilenameInTempFolder(safe_name + ".qmd")
    layer.saveNamedMetadata(filename)
    thumbnail = saveLayerThumbnail(layer)
    apiUrl = apiUrl or ""
    transformedFilename = transformMetadata(filename, uuid, apiUrl, wms, wfs, layerName or safe_name)
    mefFilename = mefFilename or tempFilenameInTempFolder(uuid + ".mef")
    createMef(uuid, transformedFilename, mefFilename, thumbnail)
    return mefFilename

def saveLayerThumbnail(layer):
    filename = tempFilenameInTempFolder("thumbnail.png")
    img = QImage(QSize(800,800), QImage.Format_A2BGR30_Premultiplied)
    color = QColor(255,255,255,255)
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

def transformMetadata(filename, uuid, apiUrl, wms, wfs, layerName):
    def _ns(n):
        return '{http://www.isotc211.org/2005/gmd}' + n
    isoFilename = tempFilenameInTempFolder("metadata.xml")
    dom = ET.parse(filename)
    xslt = ET.parse(QMD_TO_ISO19139_XSLT)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)    
    for ident in newdom.iter(_ns('fileIdentifier')):
        ident[0].text = uuid
    if wms is not None:
        for root in newdom.iter(_ns('MD_Distribution')):
            trans = ET.SubElement(root, _ns('transferOptions'))
            dtrans = ET.SubElement(trans, _ns('MD_DigitalTransferOptions'))
            online = ET.SubElement(dtrans, _ns('onLine'))
            cionline = ET.SubElement(online, _ns('CI_OnlineResource'))
            linkage = ET.SubElement(cionline, _ns('linkage'))
            url = ET.SubElement(linkage, _ns('URL'))
            url.text = wms
            protocol = ET.SubElement(cionline, _ns('protocol'))
            cs = ET.SubElement(protocol, '{http://www.isotc211.org/2005/gco}CharacterString')
            cs.text = "OGC:WMS"
            name = ET.SubElement(cionline, _ns('name'))
            csname = ET.SubElement(name, '{http://www.isotc211.org/2005/gco}CharacterString')            
            csname.text = layerName
    if wfs is not None:
        for root in newdom.iter(_ns('MD_Distribution')):
            trans = ET.SubElement(root, _ns('transferOptions'))
            dtrans = ET.SubElement(trans, _ns('MD_DigitalTransferOptions'))
            online = ET.SubElement(dtrans, _ns('onLine'))
            cionline = ET.SubElement(online, _ns('CI_OnlineResource'))
            linkage = ET.SubElement(cionline, _ns('linkage'))
            url = ET.SubElement(linkage, _ns('URL'))
            url.text = wfs
            protocol = ET.SubElement(cionline, _ns('protocol'))
            cs = ET.SubElement(protocol, '{http://www.isotc211.org/2005/gco}CharacterString')
            cs.text = "OGC:WFS"
            name = ET.SubElement(cionline, _ns('name'))
            csname = ET.SubElement(name, '{http://www.isotc211.org/2005/gco}CharacterString')            
            csname.text = layerName            
    for root in newdom.iter(_ns('MD_DataIdentification')):
        overview = ET.SubElement(root, _ns('graphicOverview'))
        browseGraphic = ET.SubElement(overview, _ns('MD_BrowseGraphic'))
        file = ET.SubElement(browseGraphic, _ns('fileName'))
        cs = ET.SubElement(file, '{http://www.isotc211.org/2005/gco}CharacterString')
        thumbnailUrl = "%s/records/%s/attachments/thumbnail.png" % (apiUrl , uuid)
        cs.text = thumbnailUrl
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
    with open(isoFilename, "w", encoding="utf8") as f:
        f.write(s)
    
    return isoFilename

def createMef(uuid, metadataFilename, mefFilename, thumbnailFilename):
    z = zipfile.ZipFile(mefFilename, "w")    
    z.write(metadataFilename, os.path.join(uuid, "metadata", os.path.basename(metadataFilename)))
    z.write(thumbnailFilename, os.path.join(uuid, "public", os.path.basename(thumbnailFilename)))
    info = getInfoXmlContent(uuid, thumbnailFilename)
    z.writestr(os.path.join(uuid, "info.xml"), info)
    z.close()

def _addSubElement(parent, tag, value=None, attrib=None):
    sub = SubElement(parent, tag, attrib=attrib or {})
    if value is not None:
        sub.text = value
    return sub

def getInfoXmlContent(uuid, thumbnailFilename):
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
    _addSubElement(general, "siteId", "GeoCatBridge")
    _addSubElement(general, "siteName", "GeoCatBridge")
    _addSubElement(root, "categories")
    privs = _addSubElement(root, "privileges")
    grp = _addSubElement(privs, "group", attrib={"name":"all"})
    _addSubElement(grp, "operation", attrib={"name":"dynamic"})
    _addSubElement(grp, "operation", attrib={"name":"featured"})
    _addSubElement(grp, "operation", attrib={"name":"view"})
    _addSubElement(grp, "operation", attrib={"name":"download"})
    public = _addSubElement(root, "public")
    _addSubElement(public, "file", attrib = {"name": os.path.basename(thumbnailFilename), "changeDate": d})
    _addSubElement(root, "private")    
    xmlstring = ElementTree.tostring(root, encoding='UTF-8', method='xml').decode()
    dom = minidom.parseString(xmlstring)    
    return dom.toprettyxml(indent="  ")    

def uuidForLayer(layer):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, layer.source()))

