import os

from qgis.PyQt import uic

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QBrush, QIcon, QColor
from qgis.PyQt.QtWidgets import QTreeWidgetItem


WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'progressdialog.ui'))

SYMBOLOGY, DATA, METADATA, GROUPS = range(4)

def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)

DATA_ICON = QIcon(iconPath("layer.png"))
METADATA_ICON = QIcon(iconPath("metadata.png"))
SYMBOLOGY_ICON = QIcon(iconPath("symbology.png"))
GROUPS_ICON = QIcon(iconPath("group.png"))
CHECK_ICON = QIcon(iconPath("checkmark.png"))

class ProgressDialog(BASE, WIDGET):

    def __init__(self, layers, parent=None):
        super(ProgressDialog, self).__init__(parent)
        self.setupUi(self)
        self.layers = layers
        self.populateTree()

    def populateTree(self):
        for layer in self.layers:
            item = QTreeWidgetItem()
            item.setText(0, layer)
            subitem = QTreeWidgetItem()
            subitem.setText(0, "Publish symbology")
            subitem.setIcon(0, SYMBOLOGY_ICON)
            item.addChild(subitem)
            subitem = QTreeWidgetItem()
            subitem.setText(0, "Publish data")
            subitem.setIcon(0, DATA_ICON)
            item.addChild(subitem)            
            subitem = QTreeWidgetItem()
            subitem.setText(0, "Publish metadata")
            subitem.setIcon(0, METADATA_ICON)
            item.addChild(subitem)            
            self.treeWidget.addTopLevelItem(item)
            item.setExpanded(False)
        item = QTreeWidgetItem()
        item.setText(0, "Create layer groups")
        item.setIcon(0, GROUPS_ICON)
        self.treeWidget.addTopLevelItem(item)
        QCoreApplication.processEvents()

    def setFinished(self, layer, category):
        if category == GROUPS:
            subitem = self.treeWidget.topLevelItem(len(self.layers))
        else:
            idx = self.layers.index(layer)
            item = self.treeWidget.topLevelItem(idx)
            subitem = item.child(category)
        self.treeWidget.scrollToItem(subitem)
        green = QColor()
        green.setNamedColor("#00851F")
        subitem.setForeground(1, QBrush(green))
        subitem.setText(1, "Finished")
        subitem.setBackground(0, QBrush(Qt.white))
        subitem.setBackground(1, QBrush(Qt.white))
        if category == METADATA:
            item.setForeground(1, QBrush(Qt.blue))
            item.setIcon(1, CHECK_ICON)
            #item.setExpanded(False)
        QCoreApplication.processEvents()

    def setSkipped(self, layer, category):
        if category == GROUPS:
            subitem = self.treeWidget.topLevelItem(len(self.layers))
        else:
            idx = self.layers.index(layer)
            item = self.treeWidget.topLevelItem(idx)
            item.setExpanded(True)
            self.treeWidget.resizeColumnToContents(0)
            subitem = item.child(category)
        self.treeWidget.scrollToItem(subitem)
        subitem.setForeground(1, QBrush(Qt.gray))
        subitem.setText(1, "Skipped")
        if category == METADATA:
            item.setForeground(1, QBrush(Qt.blue))
            item.setIcon(1, CHECK_ICON)
            #item.setExpanded(False)
        QCoreApplication.processEvents()

    def setInProgress(self, layer, category):
        if category == GROUPS:
            subitem = self.treeWidget.topLevelItem(len(self.layers))
        else:
            idx = self.layers.index(layer)
            item = self.treeWidget.topLevelItem(idx)
            item.setExpanded(True)
            self.treeWidget.resizeColumnToContents(0)
            subitem = item.child(category)
        self.treeWidget.scrollToItem(subitem)
        subitem.setText(1, "In progress...")
        grey = QColor()
        grey.setNamedColor("#cccccc")
        subitem.setBackground(0, QBrush(grey))
        subitem.setBackground(1, QBrush(grey))
        QCoreApplication.processEvents()