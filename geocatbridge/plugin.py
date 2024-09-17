import os
import sys
import traceback
import webbrowser
from functools import partial

from qgis.PyQt.QtCore import Qt, QTranslator, QSettings, QCoreApplication, QLocale
from qgis.PyQt.QtGui import QHideEvent, QShowEvent
from qgis.PyQt.QtWidgets import QAction, QWidget, QDockWidget
from qgis.core import QgsProject, QgsApplication

from geocatbridge.errorhandler import handleError
from geocatbridge.process.provider import BridgeProvider
from geocatbridge.servers import manager
from geocatbridge.ui.bridgedialog import BridgeDialog
from geocatbridge.ui.styleviewerwidget import StyleViewerWidget
from geocatbridge.utils import meta, files, feedback, gui


class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface
        self._win = iface.mainWindow()

        self.main_dialog = None
        self.action_publish = None
        self.action_help = None
        self.action_styleviewer = None
        self.widget_styleviewer = StyleViewerWidget()
        self.widget_styleviewer.hideEvent = partial(self.styleviewerHidden)
        self.widget_styleviewer.showEvent = partial(self.styleviewerShown)

        self._layerSignals = LayerStyleEventManager()

        # Load server configuration from QSettings
        manager.loadConfiguredServers()

        self.name = meta.getAppName()
        self.short_name = meta.getShortAppName()
        self.provider = None
        self.locale = QSettings().value("locale/userLocale", QLocale().name())[0:2]
        locale_path = files.getLocalePath(f"bridge_{self.locale}")

        self.translator = QTranslator()
        if os.path.exists(locale_path):
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.qgis_hook = sys.excepthook

        def plugin_hook(t, value, tb):
            """ Exception handling (catch all) """
            error_list = traceback.format_exception(t, value, tb)
            trace = "".join(error_list)
            if meta.PLUGIN_NAMESPACE in trace.lower():
                try:
                    # Show error report dialog
                    handleError(error_list)
                except Exception as err:
                    # Swallow all exceptions here, to avoid entering an endless loop
                    feedback.logWarning(f"A failure occurred while handling an exception: {err}")
            else:
                # Handle regular QGIS exception
                self.qgis_hook(t, value, tb)          
        
        sys.excepthook = plugin_hook

    @staticmethod
    def openDocUrl():
        """ Opens the web-based documentation in a new tab of the default browser. """
        webbrowser.open_new_tab(meta.getDocsUrl())

    def initProcessing(self):
        """ Initializes and adds a processing provider. """
        self.provider = BridgeProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)  # noqa

    def initGui(self):
        self.initProcessing()

        # Publish / main dialog menu item + toolbar button
        self.action_publish = QAction(gui.getSvgIcon("bridge_icon"),
                                      QCoreApplication.translate(self.name, f"{self.short_name} Publisher"),
                                      self._win)
        self.action_publish.setObjectName("startPublish")
        self.action_publish.triggered.connect(self.bridgeButtonClicked)
        self.iface.addPluginToWebMenu(self.name, self.action_publish)
        self.iface.addWebToolBarIcon(self.action_publish)

        # Register dockable StyleViewer widget (also registers to View > Panels) but keep hidden
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.widget_styleviewer)
        self.widget_styleviewer.hide()

        # StyleViewer menu item
        self.action_styleviewer = QAction(gui.getSvgIcon("styleviewer"),
                                          QCoreApplication.translate(self.name, "StyleViewer"),
                                          self._win)
        self.action_styleviewer.setObjectName("Style Viewer")
        self.action_styleviewer.triggered.connect(self.widget_styleviewer.show)
        self.iface.addPluginToWebMenu(self.name, self.action_styleviewer)

        # Help menu item
        self.action_help = QAction(QgsApplication.getThemeIcon('/mActionHelpContents.svg'),
                                   f"{self.short_name} Documentation...", self._win)
        self.action_help.setObjectName(f"{self.name} Help")
        self.action_help.triggered.connect(self.openDocUrl)
        self.iface.addPluginToWebMenu(self.name, self.action_help)

        # Add layer event handlers
        QgsProject().instance().layersAdded.connect(self.layersAdded)
        QgsProject().instance().layersWillBeRemoved.connect(self.layersWillBeRemoved)

    def unload(self):
        files.removeTempFolder()

        # Remove layer event handlers
        try:
            QgsProject().instance().layersAdded.disconnect(self.layersAdded)
            QgsProject().instance().layersWillBeRemoved.disconnect(self.layersWillBeRemoved)
        except TypeError:
            # Event handlers were never connected in the first place:
            # initGui() was probably never called, so abort the unload method
            if self.qgis_hook and self.qgis_hook != sys.excepthook:
                sys.excepthook = self.qgis_hook
            return
        self._layerSignals.clear()

        # Remove StyleViewer button and destroy StyleViewer
        self.action_styleviewer.triggered.disconnect(self.widget_styleviewer.show)
        self.iface.removePluginWebMenu(self.name, self.action_styleviewer)
        self.removeStyleViewer()
        self.action_styleviewer = None

        # Remove Publish button and close Publish dialog
        self.action_publish.triggered.disconnect(self.bridgeButtonClicked)
        self.iface.removePluginWebMenu(self.name, self.action_publish)
        self.iface.removeWebToolBarIcon(self.action_publish)
        self.closeDialog(self.main_dialog)
        self.action_publish = None

        # Remove Help button
        self.action_help.triggered.disconnect(self.openDocUrl)
        self.iface.removePluginWebMenu(self.name, self.action_help)
        self.action_help = None

        # Remove processing provider
        QgsApplication.processingRegistry().removeProvider(self.provider)  # noqa

        sys.excepthook = self.qgis_hook

    def layersAdded(self, layers):
        for lyr in layers:
            self._layerSignals.connect(lyr, self.widget_styleviewer.updateLayer)

    def layersWillBeRemoved(self, layer_ids):
        layer_ids = frozenset(layer_ids)
        for lyr_id in layer_ids:
            self._layerSignals.disconnect(lyr_id)

    def bridgeButtonClicked(self):
        """ Opens the Bridge Publish dialog. This will always create a new BridgeDialog instance."""
        if self.main_dialog and self.main_dialog.isVisible():
            # For macOS and Linux, we need to check if the window is visible. If it is, don't open another window.
            # For Windows, the Qt window modality settings should take care of this.
            return self.main_dialog.setFocus()
        self.closeDialog(self.main_dialog)
        self.main_dialog = BridgeDialog(self.iface.mainWindow())
        self.main_dialog.show()

    def styleviewerHidden(self, event: QHideEvent):
        """ Detaches the 'currentLayerChanged' event handler from the StyleViewer widget if it is hidden. """
        if self.iface and self.widget_styleviewer:
            try:
                self.iface.currentLayerChanged.disconnect(self.widget_styleviewer.updateForCurrentLayer)
            except TypeError:
                # currentLayerChanged was never connected
                pass
        event.accept()

    def styleviewerShown(self, event: QShowEvent):
        """ Attaches the 'currentLayerChanged' event handler to the StyleViewer widget if it is shown.
        Also calls 'updateForCurrentLayer' to make sure that the initial view is refreshed.
        """
        if self.iface and self.widget_styleviewer:
            self.iface.currentLayerChanged.connect(self.widget_styleviewer.updateForCurrentLayer)
            self.widget_styleviewer.updateForCurrentLayer()
        event.accept()

    @staticmethod
    def closeDialog(dialog: QWidget):
        """ Closes (hides) and destroys the given dialog. Do not use for dock widgets! """
        if dialog is None or dialog is QDockWidget:
            return
        dialog.hide()
        dialog.destroy()

    def removeStyleViewer(self):
        """ Removes the StyleViewer widget from the QGIS interface and releases its resources. """
        if self.iface is None or self.widget_styleviewer is None:
            return
        self.widget_styleviewer.hide()
        self.iface.removeDockWidget(self.widget_styleviewer)
        self.widget_styleviewer.deleteLater()
        del self.widget_styleviewer
        self.widget_styleviewer = None


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
            except (TypeError, RuntimeError):
                pass
        try:
            del self._store[layer_id]
        except KeyError:
            pass

    def clear(self):
        all_ids = list(self._store.keys())
        for lyr_id in all_ids:
            self.disconnect(lyr_id)
