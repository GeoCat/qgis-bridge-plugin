import os
import zipfile
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
from datetime import datetime
import webbrowser

import lxml.etree as ET
import requests
from requests.auth import HTTPBasicAuth

from qgis.PyQt.QtCore import QSize, QCoreApplication
from qgis.PyQt.QtGui import QImage, QColor, QPainter
from qgis.core import (
    QgsMessageLog, 
    Qgis, 
    QgsFeatureSink, 
    QgsMapSettings, 
    QgsMapRendererCustomPainterJob
)

from .metadata import uuidForLayer
from ..utils.files import tempFilenameInTempFolder
from .serverbase import ServerBase


class TokenNetworkAccessManager():
    def __init__(self, url, username, password):        
        self.url = url.strip("/")
        self.token = None
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
    
    def setTokenInHeader(self):
        if self.token is None:
            self.getToken()
        self.session.headers.update({"X-XSRF-TOKEN" : self.token}) 

    def request(self, url, data=None, method="get", headers={}):
        QgsMessageLog.logMessage(QCoreApplication.translate("GeocatBridge", "Making '%s' request to '%s'") % (method, url), 'GeoCat Bridge', level=Qgis.Info)
        self.setTokenInHeader()
        method = getattr(self.session, method.lower())
        resp = method(url, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    def getToken(self):                
        xmlInfoUrl = self.url + '/info.xml'
        self.session.post(xmlInfoUrl)
        self.token = self.session.cookies.get('XSRF-TOKEN')
        self.session.headers.update({"X-XSRF-TOKEN" : self.token})

class GeonetworkServer(ServerBase):

    PROFILE_DEFAULT = 0
    PROFILE_INSPIRE = 1
    PROFILE_DUTCH = 2

    XSLTFILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "qgis-to-iso19139.xsl")

    def __init__(self, name, url="", authid="", profile=0, node="srv"):
        super().__init__()
        self.name = name
        self.url = url
        self.authid = authid
        self.profile = profile
        self._isMetadataCatalog = True
        self._isDataCatalog = False 
        self.node = node
        user, password = self.getCredentials()
        self._nam = TokenNetworkAccessManager(self.url, user, password)


    def request(self, url, data=None, method="put", headers={}):
        return self._nam.request(url, data, method, headers)

    def publishLayerMetadata(self, layer, wms):
        uuid = uuidForLayer(layer)
        filename = tempFilenameInTempFolder(layer.name() + ".qmd")
        layer.saveNamedMetadata(filename)
        thumbnail = self.saveLayerThumbnail(layer)
        transformedFilename = self.transformMetadata(filename, uuid, wms)
        mefFilename = tempFilenameInTempFolder(uuid + ".mef")
        self.createMef(uuid, transformedFilename, mefFilename, thumbnail)        
        self.publishMetadata(mefFilename)

    def testConnection(self):
        try:
            self.me()
            return True
        except Exception as e:
            return False

    def saveLayerThumbnail(self, layer):
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

    def transformMetadata(self, filename, uuid, wms):
        def _ns(n):
            return '{http://www.isotc211.org/2005/gmd}' + n
        isoFilename = tempFilenameInTempFolder("metadata.xml")
        dom = ET.parse(filename)
        xslt = ET.parse(self.XSLTFILENAME)
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
        for root in newdom.iter(_ns('MD_DataIdentification')):
            overview = ET.SubElement(root, _ns('graphicOverview'))
            browseGraphic = ET.SubElement(overview, _ns('MD_BrowseGraphic'))
            file = ET.SubElement(browseGraphic, _ns('fileName'))
            cs = ET.SubElement(file, '{http://www.isotc211.org/2005/gco}CharacterString')
            thumbnailUrl = "%s/records/%s/attachments/thumbnail.png" % (self.apiUrl() , uuid)
            cs.text = thumbnailUrl
        s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(newdom, pretty_print=True).decode()
        with open(isoFilename, "w", encoding="utf8") as f:
            f.write(s)
        
        return isoFilename

    def apiUrl(self):
        return self.url + "/%s/api" % self.node

    def xmlServicesUrl(self):
        return self.url + "/%s/eng"  % self.node

    def metadataExists(self, uuid):
        try:
            self.getMetadata(uuid)
            return True
        except:
            return False

    def getMetadata(self, uuid):
        url = self.apiUrl() + "/records/" + uuid
        return self.request(url)

    def publishMetadata(self, metadata):
        self._nam.setTokenInHeader()
        url = self.xmlServicesUrl() + "/mef.import"
        with open(metadata, "rb") as f:
            files = {'mefFile': f}
            r = self._nam.session.post(url, files=files)
        r.raise_for_status()

    def deleteMetadata(self, uuid):
        url = self.apiUrl() + "/records/" + uuid
        self.request(url, method="delete")

    def me(self):
        url = self.apiUrl() + "/info?type=me"
        ret =  self.request(url)
        return ret

    def metadataUrl(self, uuid):
        return self.url + "/%s/api/records/%s" % (self.node, uuid)

    def openMetadata(self, uuid):        
        webbrowser.open_new_tab(self.metadataUrl(uuid))

    def setLayerUrl(self, uuid, url):
        pass

    def createMef(self, uuid, metadataFilename, mefFilename, thumbnailFilename):
        z = zipfile.ZipFile(mefFilename, "w")    
        z.write(metadataFilename, os.path.join(uuid, "metadata", os.path.basename(metadataFilename)))
        z.write(thumbnailFilename, os.path.join(uuid, "public", os.path.basename(thumbnailFilename)))
        info = self.getInfoXmlContent(uuid, thumbnailFilename)
        z.writestr(os.path.join(uuid, "info.xml"), info)
        z.close()
        self.logInfo("MEF file written to %s" % mefFilename)

    def _addSubElement(self, parent, tag, value=None, attrib=None):
        sub = SubElement(parent, tag, attrib=attrib or {})
        if value is not None:
            sub.text = value
        return sub

    def getInfoXmlContent(self, uuid, thumbnailFilename):
        root = Element("info", {"version": "1.1"})
        general = self._addSubElement(root, "general")
        d = datetime.now().isoformat()
        self._addSubElement(general, "changeDate", d)
        self._addSubElement(general, "createDate", d)
        self._addSubElement(general, "schema", "iso19139")
        self._addSubElement(general, "isTemplate", "n")
        self._addSubElement(general, "format", "full")
        self._addSubElement(general, "localId")
        self._addSubElement(general, "uuid", uuid)
        self._addSubElement(general, "siteId", "GeoCatBridge")
        self._addSubElement(general, "siteName", "GeoCatBridge")
        self._addSubElement(root, "categories")
        privs = self._addSubElement(root, "privileges")
        grp = self._addSubElement(privs, "group", attrib={"name":"all"})
        self._addSubElement(grp, "operation", attrib={"name":"dynamic"})
        self._addSubElement(grp, "operation", attrib={"name":"featured"})
        self._addSubElement(grp, "operation", attrib={"name":"view"})
        self._addSubElement(grp, "operation", attrib={"name":"download"})
        public = self._addSubElement(root, "public")
        self._addSubElement(public, "file", attrib = {"name": os.path.basename(thumbnailFilename), "changeDate": d})
        self._addSubElement(root, "private")    
        xmlstring = ElementTree.tostring(root, encoding='UTF-8', method='xml').decode()
        dom = minidom.parseString(xmlstring)    
        return dom.toprettyxml(indent="  ")