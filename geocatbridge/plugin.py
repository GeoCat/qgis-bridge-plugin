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
# from geocatbridge.processing.bridgeprovider import BridgeProvider
from geocatbridge.servers import manager
from geocatbridge.ui.bridgedialog import BridgeDialog
from geocatbridge.ui.multistylerwidget import MultistylerWidget
from geocatbridge.utils import meta, files


# Enable PyCharm remote debugger, if debug folder exists
_debug_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '_debug'))
if os.path.isdir(_debug_dir):
    sys.path.append(_debug_dir)
    import pydevd_pycharm
    from warnings import simplefilter
    try:
        # Suppress ResourceWarning when remote debug server is not running
        simplefilter('ignore', category=ResourceWarning)
        pydevd_pycharm.settrace('localhost', True, True, 53100)
    except (ConnectionRefusedError, AttributeError):
        # PyCharm remote debug server is not running on localhost:53100
        # Restore ResourceWarnings
        simplefilter('default', category=ResourceWarning)    


class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface
        self._win = iface.mainWindow()

        self.action_publish = None
        self.action_help = None
        self.action_multistyler = None
        self.widget_multistyler = None

        # readServers()  # TODO: remove
        manager.loadConfiguredServers()

        self.name = meta.getAppName()
        # self.provider = BridgeProvider()  FIXME
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
        self.action_publish = QAction(QIcon(files.getIconPath("publish_button")),
                                      QCoreApplication.translate(self.name, "Publish"), self._win)
        self.action_publish.setObjectName("startPublish")
        self.action_publish.triggered.connect(self.publishClicked)

        self.iface.addPluginToWebMenu(self.name, self.action_publish)
        self.iface.addWebToolBarIcon(self.action_publish)
            
        self.action_help = QAction(QgsApplication.getThemeIcon('/mActionHelpContents.svg'), "Plugin help...", self._win)
        self.action_help.setObjectName(f"{self.name} Help")
        self.action_help.triggered.connect(lambda: webbrowser.open_new(files.getHtmlDocsPath("index")))
        self.iface.addPluginToWebMenu(self.name, self.action_help)

        self.widget_multistyler = MultistylerWidget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.widget_multistyler)
        self.widget_multistyler.hide()

        self.action_multistyler = QAction(QIcon(files.getIconPath("symbology")),
                                          QCoreApplication.translate(self.name, "Multistyler"), self._win)
        self.action_multistyler.setObjectName("Multistyler")
        self.action_multistyler.triggered.connect(self.widget_multistyler.show)
        self.iface.addPluginToWebMenu(self.name, self.action_multistyler)

        self.iface.currentLayerChanged.connect(self.widget_multistyler.updateForCurrentLayer)

        QgsProject().instance().layerWasAdded.connect(self.layerWasAdded)
        QgsProject().instance().layerWillBeRemoved.connect(self.layerWillBeRemoved)

    def unload(self):
        files.removeTempFolder()
    
        self.iface.currentLayerChanged.disconnect(self.widget_multistyler.updateForCurrentLayer)
        QgsProject().instance().layerWasAdded.disconnect(self.layerWasAdded)

        for layer, func in self._layerSignals.items():
            layer.styleChanged.disconnect(func)

        self.iface.removePluginWebMenu(self.name, self.action_help)
        self.iface.removePluginWebMenu(self.name, self.action_publish)
        self.iface.removePluginWebMenu(self.name, self.action_multistyler)

        self.iface.removeWebToolBarIcon(self.action_publish)

        sys.excepthook = self.qgis_hook

    _layerSignals = {}

    def layerWasAdded(self, layer):
        self._layerSignals[layer] = partial(self.widget_multistyler.updateLayer, layer)
        layer.styleChanged.connect(self._layerSignals[layer])

    def layerWillBeRemoved(self, layerid):
        for layer, signal in self._layerSignals.items():
            if layer.id() == layerid:
                del signal
                return

    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
