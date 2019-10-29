import os
import webbrowser
from functools import partial

from qgis.PyQt.QtCore import Qt, QTranslator, QSettings, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsApplication

from .utils.files import removeTempFolder
from .ui.bridgedialog import BridgeDialog
from .publish.servers import readServers
from .processing.bridgeprovider import BridgeProvider

class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface

        readServers()

        self.provider = BridgeProvider()

        self.pluginFolder = os.path.dirname(__file__)
        localePath = ""
        self.locale = QSettings().value("locale/userLocale")[0:2]

        if os.path.exists(self.pluginFolder):
            localePath = os.path.join(self.pluginFolder, "i18n", "bridge_" + self.locale + ".qm")

        self.translator = QTranslator()
        if os.path.exists(localePath):
            self.translator.load(localePath)
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        iconPublish = QIcon(os.path.join(os.path.dirname(__file__), "icons", "publish_button.png"))
        self.actionPublish = QAction(iconPublish, QCoreApplication.translate("GeocatBridge", "Publish"), self.iface.mainWindow())
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.publishClicked)
        self.iface.addPluginToWebMenu("GeoCatBridge", self.actionPublish)
        self.iface.addWebToolBarIcon(self.actionPublish)

        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):

        removeTempFolder()
                
        self.iface.removePluginWebMenu("GeoCatBridge", self.actionPublish)
        self.iface.removeWebToolBarIcon(self.actionPublish)

        QgsApplication.processingRegistry().removeProvider(self.provider)
    
    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
        