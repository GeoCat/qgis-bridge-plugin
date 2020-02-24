import os
import sys
import webbrowser
import traceback
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
from .errorhandler import handleError

PLUGIN_NAMESPACE = "geocatbridge"

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

        self.qgis_hook = sys.excepthook

        def plugin_hook(t, value, tb):
            errorList = traceback.format_exception(t, value, tb)
            trace = "".join(errorList)            
            if PLUGIN_NAMESPACE in trace.lower():
                try:
                    handleError(errorList)
                except:
                    pass #we swallow all exceptions here, to avoid entering an endless loop
            else:
                self.qgis_hook(t, value, tb)          
        
        sys.excepthook = plugin_hook


    def initGui(self):
        iconPublish = QIcon(os.path.join(os.path.dirname(__file__), "icons", "publish_button.png"))
        self.actionPublish = QAction(iconPublish, QCoreApplication.translate("GeocatBridge", "Publish"), self.iface.mainWindow())
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.publishClicked)

        self.iface.addPluginToWebMenu("GeoCatBridge", self.actionPublish)
        self.iface.addWebToolBarIcon(self.actionPublish)
            
        helpPath = "file://{}".format(os.path.join(os.path.dirname(__file__), "docs", "index.html"))
        self.actionHelp = QAction(QgsApplication.getThemeIcon('/mActionHelpContents.svg'), "Plugin help...", self.iface.mainWindow())
        self.actionHelp.setObjectName("GeocatBridgeHelp")
        self.actionHelp.triggered.connect(lambda: webbrowser.open_new(helpPath))
        self.iface.addPluginToWebMenu("GeoCatBridge", self.actionHelp)

        self.multistylerDialog = MultistylerDialog()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.multistylerDialog)
        self.multistylerDialog.hide()        

        iconMultistyler = QIcon(os.path.join(os.path.dirname(__file__), "icons", "symbology.png"))
        self.actionMultistyler = QAction(iconMultistyler, QCoreApplication.translate("GeocatBridge", "Multistyler"), self.iface.mainWindow())
        self.actionMultistyler.setObjectName("multistyler")
        self.actionMultistyler.triggered.connect(self.multistylerDialog.show)
        self.iface.addPluginToWebMenu("GeoCatBridge", self.actionMultistyler)

        self.iface.currentLayerChanged.connect(self.multistylerDialog.updateForCurrentLayer)

        QgsProject.instance().layerWasAdded.connect(self.layerWasAdded)
        QgsProject.instance().layerWillBeRemoved.connect(self.layerWillBeRemoved)

        #QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):

        removeTempFolder()                        
    
        self.iface.currentLayerChanged.disconnect(self.multistylerDialog.updateForCurrentLayer)

        QgsProject.instance().layerWasAdded.disconnect(self.layerWasAdded)

        for layer, func in self._layerSignals.items():
            layer.styleChanged.disconnect(func)

        self.iface.removePluginWebMenu("GeoCatBridge", self.actionHelp)
        self.iface.removePluginWebMenu("GeoCatBridge", self.actionPublish)
        self.iface.removePluginWebMenu("GeoCatBridge", self.actionMultistyler)

        self.iface.removeWebToolBarIcon(self.actionPublish)

        #QgsApplication.processingRegistry().removeProvider(self.provider)

        sys.excepthook = self.qgis_hook

    _layerSignals = {}

    def layerWasAdded(self, layer):
        self._layerSignals[layer] = partial(self.multistylerDialog.updateLayer, layer) 
        layer.styleChanged.connect(self._layerSignals[layer])

    def layerWillBeRemoved(self, layerid):
        for layer in self._layerSignals.keys():
            if layer.id() == layerid:
                del self._layerSignals[layer]
                return

    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
        