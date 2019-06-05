# -*- coding: utf-8 -*-

__author__ = 'Victor Olaya'
__date__ = 'April 2019'
__copyright__ = '(C) 2019 Victor Olaya'

import os
import webbrowser

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsMessageLog, Qgis

from .extlibs.geocatbridgecommons import setLogger
from .extlibs.qgiscommons2.settings import readSettings
from .extlibs.qgiscommons2.gui.settings import addSettingsMenu, removeSettingsMenu
from .extlibs.qgiscommons2.gui import addAboutMenu, removeAboutMenu, addHelpMenu, removeHelpMenu
from .ui.geocatbridgedialog import GeocatBridgeDialog
from .publish.servers import readServers

class GeocatBridge:
    def __init__(self, iface):
        self.iface = iface
        
        readSettings()
        readServers()
        
        class QgisLogger():
            def logInfo(text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)
            def logWarning(text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
            def logError(text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Critical)

        logger = QgisLogger()
        setLogger(logger)

    def initGui(self):
        
        addSettingsMenu("GeoCatBridge")
        
        addHelpMenu("GeoCatBridge")
        
        addAboutMenu("GeoCatBridge")
        
        iconPublish = QIcon(os.path.join(os.path.dirname(__file__), "icons", "publish_button.png"))
        self.actionPublish = QAction(iconPublish, "Publish", self.iface.mainWindow())
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.publishClicked)
        self.iface.addPluginToMenu("GeoCatBridge", self.actionPublish)
        

    def unload(self):
        
        removeSettingsMenu("GeoCatBridge")
        
        removeHelpMenu("GeoCatBridge")
        
        removeAboveMenu("GeoCatBridge")
                
        self.iface.removePluginFromWebMenu("GeoCatBridge", self.actionPublish)
        

    
    def publishClicked(self):
        dialog = GeocatBridgeDialog(self.iface.mainWindow())
        dialog.exec_()
        