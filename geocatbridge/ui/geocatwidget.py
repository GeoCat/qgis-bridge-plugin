import os
import requests
import webbrowser

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget, QSizePolicy
from qgis.PyQt.QtGui import QTextDocument, QPixmap
from qgis.PyQt.QtCore import QUrl, QSize
from qgis.PyQt.QtWebKitWidgets import QWebPage
from qgis.core import Qgis, QgsApplication
from qgis.gui import QgsMessageBar

from geocatbridge.publish import mygeocat

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
        try:
            mygeocat.client.login(user)
            self.labelLoggedInAs.setText("Logged in as <b>%s</b>" % user)
            self.labelUrlGeoserver.setText("<a href='{0}'>{0}</a>".format(mygeocat.client.geoserverUrl))
            self.labelUrlGeonetwork.setText("<a href='{0}'>{0}</a>".format(mygeocat.client.geonetworkUrl))
            self.labelStatusGeoserver.setText(self._statusText(mygeocat.client.geoserverStatus))
            self.labelStatusGeoserver.setStyleSheet(self._statusCss(mygeocat.client.geoserverStatus))
            self.labelStatusGeonetwork.setText(self._statusText(mygeocat.client.geonetworkStatus))
            self.labelStatusGeonetwork.setStyleSheet(self._statusCss(mygeocat.client.geonetworkStatus))
            self.stackedWidget.setCurrentIndex(1)
            mygeocat.client.addLiveServer()
        except:
            self.bar.pushMessage(self.tr("Login"), self.tr("Could not log in"), level=Qgis.Warning, duration=5)
            return

    def logout(self):
        mygeocat.client.logout()
        self.stackedWidget.setCurrentIndex(0)
        self.txtUsername.setText("")



    
        