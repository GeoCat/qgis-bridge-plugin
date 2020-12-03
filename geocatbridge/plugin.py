import os
import sys
import traceback
import webbrowser
from functools import partial

from qgis.PyQt.QtCore import Qt, QTranslator, QSettings, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsApplication

from geocatbridge.errorhandler import handleError
from geocatbridge.processing.bridgeprovider import BridgeProvider
from geocatbridge.publish.servers import readServers
from geocatbridge.ui.bridgedialog import BridgeDialog
from geocatbridge.ui.multistylerwidget import MultistylerWidget
from geocatbridge.utils import meta, files


class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface
        self._mainWin = iface.mainWindow()

        readServers()

        self.name = meta.getAppName()
        self.provider = BridgeProvider()
        self.locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = files.getLocalePath(f"bridge_{self.locale}")

        self.translator = QTranslator()
        if os.path.exists(locale_path):
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.qgis_hook = sys.excepthook

        def plugin_hook(t, value, tb):
            error_list = traceback.format_exception(t, value, tb)
            trace = "".join(error_list)
            if meta.PLUGIN_NAMESPACE in trace.lower():
                try:
                    handleError(error_list)
                except:
                    pass  # we swallow all exceptions here, to avoid entering an endless loop
            else:
                self.qgis_hook(t, value, tb)          
        
        sys.excepthook = plugin_hook

    def initGui(self):
        iconPublish = QIcon(files.getIconPath("publish_button"))
        self.actionPublish = QAction(iconPublish, QCoreApplication.translate(self.name, "Publish"), self._mainWin)
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.publishClicked)

        self.iface.addPluginToWebMenu(self.name, self.actionPublish)
        self.iface.addWebToolBarIcon(self.actionPublish)
            
        self.actionHelp = QAction(QgsApplication().getThemeIcon('/mActionHelpContents.svg'), "Plugin help...", self._mainWin)
        self.actionHelp.setObjectName(f"{self.name} Help")
        self.actionHelp.triggered.connect(lambda: webbrowser.open_new(files.getHtmlDocsPath("index")))
        self.iface.addPluginToWebMenu(self.name, self.actionHelp)

        self.multistylerDialog = MultistylerWidget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.multistylerDialog)
        self.multistylerDialog.hide()        

        iconMultistyler = QIcon(files.getIconPath("symbology"))
        self.actionMultistyler = QAction(iconMultistyler, QCoreApplication.translate(self.name, "Multistyler"), self._mainWin)
        self.actionMultistyler.setObjectName("Multistyler")
        self.actionMultistyler.triggered.connect(self.multistylerDialog.show)
        self.iface.addPluginToWebMenu(self.name, self.actionMultistyler)

        self.iface.currentLayerChanged.connect(self.multistylerDialog.updateForCurrentLayer)

        QgsProject().instance().layerWasAdded.connect(self.layerWasAdded)
        QgsProject().instance().layerWillBeRemoved.connect(self.layerWillBeRemoved)

    def unload(self):
        files.removeTempFolder()
    
        self.iface.currentLayerChanged.disconnect(self.multistylerDialog.updateForCurrentLayer)
        QgsProject().instance().layerWasAdded.disconnect(self.layerWasAdded)

        for layer, func in self._layerSignals.items():
            layer.styleChanged.disconnect(func)

        self.iface.removePluginWebMenu(self.name, self.actionHelp)
        self.iface.removePluginWebMenu(self.name, self.actionPublish)
        self.iface.removePluginWebMenu(self.name, self.actionMultistyler)

        self.iface.removeWebToolBarIcon(self.actionPublish)

        sys.excepthook = self.qgis_hook

    _layerSignals = {}

    def layerWasAdded(self, layer):
        self._layerSignals[layer] = partial(self.multistylerDialog.updateLayer, layer) 
        layer.styleChanged.connect(self._layerSignals[layer])

    def layerWillBeRemoved(self, layerid):
        for layer, signal in self._layerSignals.items():
            if layer.id() == layerid:
                del signal
                return

    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
