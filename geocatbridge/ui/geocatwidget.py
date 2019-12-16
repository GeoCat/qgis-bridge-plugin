import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QSizePolicy
from qgis.PyQt.QtCore import QUrl
from qgis.core import Qgis

from geocatbridge.publish.servers import *
from geocatbridge.publish.geocatlive import GeocatLiveServer

from qgis.gui import QgsMessageBar

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'geocatwidget.ui'))

class GeoCatWidget(WIDGET, BASE):

    def __init__(self, parent=None):
        super(GeoCatWidget, self).__init__(parent)
        self.setupUi(self)

        self.btnLogin.clicked.connect(self.login)
        self.btnLogout.clicked.connect(self.logout)

        path = os.path.join(os.path.dirname(os.path.dirname(__file__), "resources", "aboutgeocat.html"))
        self.txtAbout.loadResource(QUrl(path))

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.centralLayout.insertWidget(0, self.bar)

    def login(self):
        user = self.txtUsername.text()
        password = self.txtPassword.text()
        self.client = MyGeoCatClient()
        try:
            self.client.login(user, password)
            self.txtMyGeoCat.setHtml(self.client.getUserPage())
            self.stackedWidget.setCurrentIndex(1)
            self.client.addLiveServer()
        except:
            self.bar.pushMessage(self.tr("Login"), self.tr("Could not log in"), level=Qgis.Warning, duration=5)

    def logout(self):
        self.client = None
        self.stackedWidget.setCurrentIndex(0)

class MyGeoCatClient():

    URL = ""

    def login(user, password):
        self.user = user
        self.password = password

    def addLiveServer():
        for server in allServers.values():
            if isinstance(server, GeocatLiveServer):
                if server.userid == self.user:
                    return
        server = GeocatLiveServer("GeoCat Live - " + self.user, self.user, "", "")
        addServer(server)

    def getUserPage(self):
        return ""