from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QBrush, QColor
from qgis.PyQt.QtWidgets import QTreeWidgetItem

from geocatbridge.utils import gui
from geocatbridge.utils import layers as lyr_utils

WIDGET, BASE = gui.loadUiType(__file__)

SYMBOLOGY, DATA, METADATA, GROUPS = range(4)

DATA_ICON = gui.getSvgIcon("layer")
METADATA_ICON = gui.getSvgIcon("metadata")
SYMBOLOGY_ICON = gui.getSvgIcon("symbology")
GROUPS_ICON = gui.getSvgIcon("group")
CHECK_ICON = gui.getSvgIcon("checkmark")


class ProgressDialog(BASE, WIDGET):

    def __init__(self, layer_ids, parent=None):
        super(ProgressDialog, self).__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(gui.getSvgIcon('geocat_icon'))

        self.layer_ids = layer_ids
        self.populateTree()

    def populateTree(self):
        for lyr_name in (lyr_utils.layerById(id_).name() for id_ in self.layer_ids):
            item = QTreeWidgetItem()
            item.setText(0, lyr_name)
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

    def getItem(self, layer_id, category, expand=False) -> tuple:
        """ Toggles the tree appearance by setting the current layer item.
        Returns the current item (if not a group) and sub-item.
        """
        item = None
        if category == GROUPS:
            subitem = self.treeWidget.topLevelItem(len(self.layer_ids))
        else:
            item_pos = self.layer_ids.index(layer_id)
            item = self.treeWidget.topLevelItem(item_pos)
            if expand:
                item.setExpanded(True)
                self.treeWidget.resizeColumnToContents(0)
            subitem = item.child(category)
        self.treeWidget.scrollToItem(subitem)
        return item, subitem

    @staticmethod
    def setMetadata(item, category):
        if item and category == METADATA:
            item.setForeground(1, QBrush(Qt.blue))
            item.setIcon(1, CHECK_ICON)

    def setFinished(self, layer_id, category):
        item, subitem = self.getItem(layer_id, category)
        green = QColor()
        green.setNamedColor("#00851F")
        subitem.setForeground(1, QBrush(green))
        subitem.setText(1, "Finished")
        subitem.setBackground(0, QBrush(Qt.white))
        subitem.setBackground(1, QBrush(Qt.white))
        self.setMetadata(item, category)
        QCoreApplication.processEvents()

    def setSkipped(self, layer_id, category):
        item, subitem = self.getItem(layer_id, category, True)
        subitem.setForeground(1, QBrush(Qt.gray))
        subitem.setText(1, "Skipped")
        self.setMetadata(item, category)
        QCoreApplication.processEvents()

    def setInProgress(self, layer_id, category):
        item, subitem = self.getItem(layer_id, category, True)
        subitem.setText(1, "In progress...")
        grey = QColor()
        grey.setNamedColor("#cccccc")
        subitem.setBackground(0, QBrush(grey))
        subitem.setBackground(1, QBrush(grey))
        QCoreApplication.processEvents()
