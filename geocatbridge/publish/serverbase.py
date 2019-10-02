import requests

from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsAuthMethodConfig,
    QgsApplication
)


class ServerBase():

    def __init__(self):
        self._warnings = []
        self._errors = []

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

    def getCredentials(self):
        authConfig = QgsAuthMethodConfig()
        QgsApplication.authManager().loadAuthenticationConfig(self.authid, authConfig, True)
        username = authConfig.config('username')
        password = authConfig.config('password')
        return username, password

    def request(self, url, data=None, method="put", headers={}):
        username, password = self.getCredentials()
        req_method = getattr(requests, method.lower())
        return req_method(url, headers=headers, data=data, auth=(username, password))
