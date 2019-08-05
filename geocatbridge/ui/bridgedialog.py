import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtCore import *
from qgis.gui import *
from qgis.core import *
from .publishwidget import PublishWidget
from .serverconnectionswidget import ServerConnectionsWidget

def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'bridgedialog.ui'))

class BridgeDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(BridgeDialog, self).__init__(parent)
        self.setupUi(self)
        self.publishWidget = PublishWidget()
        self.serversWidget = ServerConnectionsWidget()
        self.stackedWidget.addWidget(self.publishWidget)
        self.stackedWidget.addWidget(self.serversWidget)
        self.listWidget.setMinimumSize(QSize(100, 200))
        self.listWidget.setMaximumSize(QSize(153, 16777215))
        self.listWidget.setStyleSheet("QListWidget{\n"
            "    background-color: rgb(69, 69, 69, 220);\n"
            "    outline: 0;\n"
            "}\n"
            "QListWidget::item {\n"
            "    color: white;\n"
            "    padding: 3px;\n"
            "}\n"
            "QListWidget::item::selected {\n"
            "    color: black;\n"
            "    background-color:palette(Window);\n"
            "    padding-right: 0px;\n"
            "}")
        self.listWidget.setFrameShape(QFrame.Box)
        self.listWidget.setLineWidth(0)
        self.listWidget.setIconSize(QSize(32, 32))
        self.listWidget.setUniformItemSizes(True)
        item = self.listWidget.item(0)
        item.setIcon(QIcon(iconPath('preview.png')))
        self.listWidget.setCurrentItem(item)
        self.setCurrentPanel(0)
        item = self.listWidget.item(1)
        item.setIcon(QIcon(iconPath('preview.png')))
        self.listWidget.currentRowChanged.connect(self.sectionChanged)

    def sectionChanged(self):
        idx = self.listWidget.currentRow()
        self.setCurrentPanel(idx)

    def setCurrentPanel(self, idx):
        if idx == 0:
            self.stackedWidget.setCurrentWidget(self.publishWidget)
            self.publishWidget.updateServers()
        else:
            self.stackedWidget.setCurrentWidget(self.serversWidget)

    def closeEvent(self, evt):
        self.publishWidget.storeMetadata() 
        evt.accept()