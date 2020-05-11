import os
import zipfile
import webbrowser
import requests
from requests.auth import HTTPBasicAuth

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsMessageLog,
    Qgis
)

from .metadata import saveMetadata
from .serverbase import ServerBase


class TokenNetworkAccessManager:
    def __init__(self, url, username, password):
        self.url = url.strip("/")
        self.token = None
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)

    def setTokenInHeader(self):
        if self.token is None:
            self.getToken()
        self.session.headers.update({"X-XSRF-TOKEN": self.token})

    def request(self, url, data=None, method="get", headers={}):
        QgsMessageLog.logMessage(
            QCoreApplication.translate("GeocatBridge", "Making '%s' request to '%s'")
            % (method, url),
            "GeoCat Bridge",
            level=Qgis.Info,
        )
        self.setTokenInHeader()
        method = getattr(self.session, method.lower())
        resp = method(url, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    def getToken(self):
        signinUrl = self.url + "/eng/catalog.signin"
        self.session.post(signinUrl)
        self.token = self.session.cookies.get("XSRF-TOKEN")
        self.session.headers.update({"X-XSRF-TOKEN": self.token})


class GeonetworkServer(ServerBase):

    PROFILE_DEFAULT = 0
    PROFILE_INSPIRE = 1
    PROFILE_DUTCH = 2

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

    def request(self, url, data=None, method="get", headers={}):
        return self._nam.request(url, data, method, headers)

    def publishLayerMetadata(self, layer, wms, wfs, layerName):
        mefFilename = saveMetadata(layer, None, self.apiUrl(), wms, wfs, layerName)
        self.publishMetadata(mefFilename)

    def testConnection(self):
        try:
            self.me()
            return True
        except Exception as e:
            return False

    def apiUrl(self):
        return self.url + "/%s/api" % self.node

    def xmlServicesUrl(self):
        return self.url + "/%s/eng" % self.node

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
        url = self.apiUrl() + "/records"
        headers = {"Accept": "application/json"}
        params = {"uuidProcessing", "OVERWRITE"}

        with open(metadata, "rb") as f:
            files = {"file": f}
            r = self._nam.session.post(url, files=files, headers=headers)
            r.raise_for_status()

    def deleteMetadata(self, uuid):
        url = self.apiUrl() + "/records/" + uuid
        self.request(url, method="delete")

    def me(self):
        url = self.apiUrl() + "/info?type=me"
        ret = self.request(url)
        return ret

    def metadataUrl(self, uuid):
        return self.url + "/%s/api/records/%s" % (self.node, uuid)

    def openMetadata(self, uuid):
        webbrowser.open_new_tab(self.metadataUrl(uuid))
