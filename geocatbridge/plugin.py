# -*- coding: utf-8 -*-

__author__ = 'Victor Olaya'
__date__ = 'April 2019'
__copyright__ = '(C) 2019 Victor Olaya'

import os
import webbrowser

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis

from bridgecommon import log
from qgiscommons2.settings import readSettings
from qgiscommons2.gui.settings import addSettingsMenu, removeSettingsMenu
from qgiscommons2.gui import addAboutMenu, removeAboutMenu, addHelpMenu, removeHelpMenu
from .ui.bridgedialog import BridgeDialog
from .ui.multistylerdialog import MultistylerDialog
from .publish.servers import readServers

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

        logger = QgisLogger()
        log.setLogger(logger)

    def initGui(self):

        readSettings()
        
        addSettingsMenu("GeoCatBridge")
        
        addHelpMenu("GeoCatBridge")
        
        addAboutMenu("GeoCatBridge")
        
        iconPublish = QIcon(os.path.join(os.path.dirname(__file__), "icons", "publish_button.png"))
        self.actionPublish = QAction(iconPublish, "Publish", self.iface.mainWindow())
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.publishClicked)
        self.iface.addPluginToMenu("GeoCatBridge", self.actionPublish)

        self.multistylerDialog = MultistylerDialog()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.multistylerDialog)
        self.multistylerDialog.hide()        

        self.actionMultistyler = QAction("Multistyler", self.iface.mainWindow())
        self.actionMultistyler.setObjectName("multistyler")
        self.actionMultistyler.triggered.connect(self.multistylerDialog.show)
        self.iface.addPluginToMenu("GeoCatBridge", self.actionMultistyler)

        self.iface.currentLayerChanged.connect(self.multistylerDialog.updateForCurrentLayer)

    def unload(self):
        
        removeSettingsMenu("GeoCatBridge")
        
        removeHelpMenu("GeoCatBridge")
        
        removeAboutMenu("GeoCatBridge")
                
        self.iface.removePluginMenu("GeoCatBridge", self.actionPublish)
        self.iface.removePluginMenu("GeoCatBridge", self.actionMultistyler)
    
        self.iface.currentLayerChanged.disconnect(self.multistylerDialog.updateForCurrentLayer)
    
    def publishClicked(self):
        readSettings()
        dialog = BridgeDialog(self.iface.mainWindow())
        dialog.exec_()
        