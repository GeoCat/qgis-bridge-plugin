import os
import webbrowser
from functools import partial

from qgis.PyQt.QtCore import Qt, QTranslator, QSettings, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsApplication

from .utils.files import removeTempFolder
from .ui.bridgedialog import BridgeDialog
from .ui.multistylerdialog import MultistylerDialog
from .publish.servers import readServers
from .processing.bridgeprovider import BridgeProvider

class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface

        readServers()
        
        class QgisLogger():
            def logInfo(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)
            def logWarning(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
            def logError(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Critical)

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
        self.iface.addPluginToMenu("GeoCatBridge", self.actionPublish)

        self.multistylerDialog = MultistylerDialog()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.multistylerDialog)
        self.multistylerDialog.hide()        

        self.actionMultistyler = QAction(QCoreApplication.translate("GeocatBridge", "Multistyler"), self.iface.mainWindow())
        self.actionMultistyler.setObjectName("multistyler")
        self.actionMultistyler.triggered.connect(self.multistylerDialog.show)
        self.iface.addPluginToMenu("GeoCatBridge", self.actionMultistyler)

        self.iface.currentLayerChanged.connect(self.multistylerDialog.updateForCurrentLayer)

        QgsProject.instance().layerWasAdded.connect(self.layerWasAdded)

        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):

        removeTempFolder()
                
        self.iface.removePluginMenu("GeoCatBridge", self.actionPublish)
        self.iface.removePluginMenu("GeoCatBridge", self.actionMultistyler)
    
        self.iface.currentLayerChanged.disconnect(self.multistylerDialog.updateForCurrentLayer)

        QgsProject.instance().layerWasAdded.disconnect(self.layerWasAdded)

        for layer, func in self._layerSignals.items():
            layer.styleChanged.disconnect(func)

        QgsApplication.processingRegistry().removeProvider(self.provider)

    _layerSignals = {}

    def layerWasAdded(self, layer):
        self._layerSignals[layer] = partial(self.multistylerDialog.updateLayer, layer) 
        layer.styleChanged.connect(self._layerSignals[layer])
    
    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
        