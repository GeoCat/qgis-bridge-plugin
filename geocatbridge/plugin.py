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
from geocatbridge.process.provider import BridgeProvider
from geocatbridge.servers import manager
from geocatbridge.ui.bridgedialog import BridgeDialog
from geocatbridge.ui.multistylerwidget import MultistylerWidget
from geocatbridge.utils import meta, files


class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface
        self._win = iface.mainWindow()

        self.action_publish = None
        self.action_help = None
        self.action_multistyler = None
        self.widget_multistyler = None

        self._layerSignals = LayerStyleEventManager()

        # Load server configuration from QSettings
        manager.loadConfiguredServers()

        self.name = meta.getAppName()
        self.provider = None
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

    @staticmethod
    def openDocUrl():
        """ Opens the web-based documentation in a new tab of the default browser. """
        doc_url = meta.getProperty('docs').rstrip('/')
        version = meta.getProperty('version')
        full_url = f"{doc_url}/v{version}/"
        webbrowser.open_new_tab(full_url)

    def initProcessing(self):
        self.provider = BridgeProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)  # noqa

    def initGui(self):
        self.initProcessing()

        self.action_publish = QAction(QIcon(files.getIconPath("publish_button")),
                                      QCoreApplication.translate(self.name, "Publish"), self._win)
        self.action_publish.setObjectName("startPublish")
        self.action_publish.triggered.connect(self.publishClicked)

        self.iface.addPluginToWebMenu(self.name, self.action_publish)
        self.iface.addWebToolBarIcon(self.action_publish)
            
        self.widget_multistyler = MultistylerWidget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.widget_multistyler)
        self.widget_multistyler.hide()

        self.action_multistyler = QAction(QIcon(files.getIconPath("symbology")),
                                          QCoreApplication.translate(self.name, "Multistyler"), self._win)
        self.action_multistyler.setObjectName("Multistyler")
        self.action_multistyler.triggered.connect(self.widget_multistyler.show)
        self.iface.addPluginToWebMenu(self.name, self.action_multistyler)

        self.iface.currentLayerChanged.connect(self.widget_multistyler.updateForCurrentLayer)

        self.action_help = QAction(QgsApplication.getThemeIcon('/mActionHelpContents.svg'),
                                   "Plugin Help...", self._win)
        self.action_help.setObjectName(f"{self.name} Help")
        self.action_help.triggered.connect(self.openDocUrl)
        self.iface.addPluginToWebMenu(self.name, self.action_help)

        QgsProject().instance().layersAdded.connect(self.layersAdded)
        QgsProject().instance().layersWillBeRemoved.connect(self.layersWillBeRemoved)

    def unload(self):
        files.removeTempFolder()
    
        self.iface.currentLayerChanged.disconnect(self.widget_multistyler.updateForCurrentLayer)
        QgsProject().instance().layersAdded.disconnect(self.layersAdded)

        self._layerSignals.clear()

        self.iface.removePluginWebMenu(self.name, self.action_help)
        self.iface.removePluginWebMenu(self.name, self.action_publish)
        self.iface.removePluginWebMenu(self.name, self.action_multistyler)

        self.iface.removeWebToolBarIcon(self.action_publish)

        QgsApplication.processingRegistry().removeProvider(self.provider)  # noqa

        sys.excepthook = self.qgis_hook

    def layersAdded(self, layers):
        for lyr in layers:
            self._layerSignals.connect(lyr, self.widget_multistyler.updateLayer)

    def layersWillBeRemoved(self, layer_ids):
        layer_ids = frozenset(layer_ids)
        for lyr_id in layer_ids:
            self._layerSignals.disconnect(lyr_id)

    def publishClicked(self):
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.show()


class LayerStyleEventManager:
    def __init__(self):
        self._store = dict()

    def connect(self, lyr, handler, *args, **kwargs):
        """ Connects an event handler function to the layer styleChanged event.
        It is expected that the handler function requires a layer argument.
        Optionally, other *args and **kwargs may be passed on to the function.
        """
        try:
            func = partial(handler, lyr, *args, **kwargs)
            lyr.styleChanged.connect(func)
            self._store[lyr.id()] = lyr, func
        except RuntimeError:
            pass

    def disconnect(self, layer_id):
        lyr, func = self._store.get(layer_id, (None, None))
        if lyr and func:
            try:
                lyr.styleChanged.disconnect(func)  # noqa
            except RuntimeError:
                pass
        try:
            del self._store[layer_id]
        except KeyError:
            pass

    def clear(self):
        all_ids = list(self._store.keys())
        for lyr_id in all_ids:
            self.disconnect(lyr_id)
