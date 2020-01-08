import os
import requests
import webbrowser

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QSizePolicy
from qgis.PyQt.QtGui import QTextDocument, QPixmap
from qgis.PyQt.QtCore import QUrl, QSize
from qgis.PyQt.QtWebKitWidgets import QWebPage
from qgis.core import Qgis, QgsApplication

from geocatbridge.publish.servers import *
from geocatbridge.publish.geocatlive import GeocatLiveServer
from geocatbridge.utils.gui import execute

from qgis.gui import QgsMessageBar

GEOCAT_AUTH_KEY = "geocat_credentials"

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'geocatwidget.ui'))

rootFolder = os.path.dirname(os.path.dirname(__file__))

class GeoCatWidget(WIDGET, BASE):

    def __init__(self, parent=None):
        super(GeoCatWidget, self).__init__(parent)
        self.setupUi(self)
        
        pixmap = QPixmap(os.path.join(rootFolder, "icons", "livelogo.png"))
        self.labelLiveLogo.setPixmap(pixmap)

        self.btnLogin.clicked.connect(self.login)
        self.btnLogout.clicked.connect(self.logout)
        self.btnSendReport.clicked.connect(self.sendReport)

        path = os.path.join(rootFolder, "resources", "geocatlivepage", "index.html")
        url = QUrl.fromLocalFile(path)
        self.txtAbout.load(url)
        self.txtAbout.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.txtAbout.linkClicked.connect(lambda url: webbrowser.open_new_tab(url.toString()))


        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.centralLayout.insertWidget(0, self.bar)

        self.tabWidget.setCurrentIndex(0)
        self.stackedWidget.setCurrentIndex(0)
        self.retrieveCredentials()

    def sendReport(self):
        pass

    def _statusCss(self, status):
        colors = {"SERVICE_RUNNING": "green",
                "SERVICE_ERROR": "red",
                "SERVICE_WAITING": "blue"}
        color = colors.get(status, "red")
        return '''
            border: 0px solid black; border-radius: 4px; background: %s; color: white;
            ''' % color

    def _statusText(self, status):
        texts =  {"SERVICE_RUNNING": "Running",
                "SERVICE_ERROR": "Error",
                "SERVICE_WAITING": "Waiting"}
        return texts.get(status, "Error")

    def login(self):
        user = self.txtUsername.text()
        password = self.txtPassword.text()        
        self.client = MyGeoCatClient()
        try:
            self.client.login(user, password)
            self.labelLoggedInAs.setText("Logged in as <b>%s</b>" % user)
            self.labelUrlGeoserver.setText("<a href='{0}'>{0}</a>".format(self.client.geoserverUrl))
            self.labelUrlGeonetwork.setText("<a href='{0}'>{0}</a>".format(self.client.geonetworkUrl))
            self.labelStatusGeoserver.setText(self._statusText(self.client.geoserverStatus))
            self.labelStatusGeoserver.setStyleSheet(self._statusCss(self.client.geoserverStatus))
            self.labelStatusGeonetwork.setText(self._statusText(self.client.geonetworkStatus))
            self.labelStatusGeonetwork.setStyleSheet(self._statusCss(self.client.geonetworkStatus))
            self.stackedWidget.setCurrentIndex(1)
            self.client.addLiveServer()            
        except:
            self.bar.pushMessage(self.tr("Login"), self.tr("Could not log in"), level=Qgis.Warning, duration=5)
            return

        if self.chkSaveCredentials.isChecked():
            auth = "{}/{}".format(user, password)
            QgsApplication.authManager().storeAuthSetting(GEOCAT_AUTH_KEY, auth, True)
        else:
            QgsApplication.authManager().removeAuthSetting(GEOCAT_AUTH_KEY)

    def logout(self):
        self.client = None
        self.stackedWidget.setCurrentIndex(0)
        self.retrieveCredentials()

    def retrieveCredentials(self):
        auth = QgsApplication.authManager().authSetting(GEOCAT_AUTH_KEY, defaultValue='', decrypt=True)
        if auth:
            username, password = auth.split("/")            
        else:
            username, password = "", ""
        self.txtUsername.setText(username)
        self.txtPassword.setText(password)

class MyGeoCatClient():

    BASE_URL = "https://live-services.geocat.net/geocat-live/api/1.0/order"

    def __init__(self):
        self.geoserverUrl = ""
        self.geoserverStatus = ""
        self.geonetworkUrl = ""
        self.geonetworkStatus = ""

    def login(self, user, password):
        self.user = user
        self.password = password
        self.server = GeocatLiveServer("GeoCat Live - " + self.user, self.user, "", "")
        url = "%s/%s" % (self.BASE_URL, self.user)
        response = execute(lambda: requests.get(url))
        responsejson =response.json()
        for serv in responsejson["services"]:
            if serv["application"] == "geoserver":
                self.geoserverUrl = serv["url"] + "/rest"
                self.geoserverStatus = serv["status"]
            if serv["application"] == "geonetwork":
                self.geonetworkUrl = serv["url"]
                self.geonetworkStatus = serv["status"]

    def addLiveServer(self):
        for server in allServers().values():
            if isinstance(server, GeocatLiveServer):
                if server.userid == self.user:
                    return        
        addServer(self.server)

    
        