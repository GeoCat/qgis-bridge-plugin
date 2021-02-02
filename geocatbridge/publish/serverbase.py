import requests
import json

from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsAuthMethodConfig,
    QgsApplication
)


class ServerBase:

    def __init__(self):
        self._warnings = []
        self._errors = []
        self._username = None
        self._password = None

    def logInfo(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)

    def logWarning(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
        self._warnings.append(text)

    def logError(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Critical)
        self._errors.append(text)

    def resetLog(self):
        self._warnings = []
        self._errors = []

    def loggedInfo(self):
        return self._warnings, self._errors

    def setBasicAuthCredentials(self, username, password):
        self._username = username
        self._password = password

    def getCredentials(self):
        if self._username is None or self._password is None:
            authConfig = QgsAuthMethodConfig()
            QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
            username = authConfig.config('username')
            password = authConfig.config('password')
            return username, password
        else:
            return self._username, self._password

    def request(self, url, data=None, method="get", headers=None, files=None):
        headers = headers or {}
        files = files or {}
        username, password = self.getCredentials()
        req_method = getattr(requests, method.lower())
        if isinstance(data, dict):
            # If the request contains data as a dictionary, serialize as JSON
            data = json.dumps(data)
            headers["content-type"] = "application/json"
        self.logInfo("Making %s request to '%s'" % (method.upper(), url))
        r = req_method(url, headers=headers, files=files, data=data, auth=(username, password))
        if not isinstance(r, requests.Response):
            self.logWarning("Empty or invalid response returned!")
        r.raise_for_status()
        return r

    def addOGCServers(self):
        pass

    def validateGeodataBeforePublication(self, errors, toPublish, onlySymbology):
        pass

    def validateMetadataBeforePublication(self, errors):
        pass
