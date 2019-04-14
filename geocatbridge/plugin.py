# -*- coding: utf-8 -*-

__author__ = 'Victor Olaya'
__date__ = 'April 2019'
__copyright__ = '(C) 2019 Victor Olaya'

import os
import webbrowser

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .extlibs.qgiscommons2.settings import readSettings
from .extlibs.qgiscommons2.gui.settings import addSettingsMenu, removeSettingsMenu
from .extlibs.qgiscommons2.gui import addAboutMenu, removeAboutMenu, addHelpMenu, removeHelpMenu
        

class Geocatbridge:
    def __init__(self, iface):
        self.iface = iface
        
        readSettings()
        

    def initGui(self):
        
        addSettingsMenu("geocatbridge")
        
        addHelpMenu("geocatbridge")
        
        addAboutMenu("geocatbridge")
        
        iconPublish = QIcon(os.path.join(os.path.dirname(__file__), "icons", "publish_button.png"))
        self.actionPublish = QAction(iconPublish, "Publish", self.iface.mainWindow())
        self.actionPublish.setObjectName("startPublish")
        self.actionPublish.triggered.connect(self.PublishClicked)
        self.iface.addPluginToWebMenu("GeoCatBridge", self.actionPublish)
        

    def unload(self):
        
        removeSettingsMenu("geocatbridge")
        
        removeHelpMenu("geocatbridge")
        
        removeAboveMenu("geocatbridge")
                
        self.iface.removePluginFromWebMenu("GeoCatBridge", self.actionPublish)
        

    
    def PublishClicked(self):
        pass
        