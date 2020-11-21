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

        path = os.path.join(rootFolder, "resources", "geocat", "index.html")
        url = QUrl.fromLocalFile(path)
        self.txtAbout.load(url)
        self.txtAbout.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.txtAbout.linkClicked.connect(lambda url: webbrowser.open_new_tab(url.toString()))

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.centralLayout.insertWidget(0, self.bar)

        self.tabWidget.setCurrentIndex(0)
        self.stackedWidget.setCurrentIndex(0)
