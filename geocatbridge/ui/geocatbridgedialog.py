import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import geodataServers, metadataServers
from geocatbridge.ui.serverconnectionsdialog import ServerConnectionsDialog
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.utils import iface

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'geocatbridgedialog.ui'))

class GeocatBridgeDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeocatBridgeDialog, self).__init__(parent)
        self.isMetadataPublished = {}
        self.isDataPublished = {}
        self.currentRow = None
        self.setupUi(self)

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.bar)

        self.populateComboBoxes()
        self.populateLayers()
        self.tableLayers.clicked.connect(self.layerClicked)
        self.tableLayers.customContextMenuRequested.connect(self.showContextMenu)
        self.tableLayers.currentCellChanged.connect(self.currentCellChanged)
        self.comboMapServer.currentIndexChanged.connect(self.populateLayers)
        self.comboCatalogue.currentIndexChanged.connect(self.populateLayers)
        self.btnDefineConnectionsData.clicked.connect(self.defineConnectionsData)
        self.btnDefineConnectionsMetadata.clicked.connect(self.defineConnectionsMetadata)
        self.btnPublish.clicked.connect(self.publish)
        self.btnClose.clicked.connect(self.close)
        self.labelSelect.linkActivated.connect(self.selectLabelClicked)

    def selectLabelClicked(self, url):
        state = Qt.Unchecked if url == "none" else Qt.Checked
        for i in range (self.tableLayers.rowCount()):
            item = self.tableLayers.item(i, 0)
            item.setCheckState(state)


    def currentCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        layers = self.publishableLayers()
        if self.currentRow == currentRow:
            return
        layer = layers[currentRow]
        self.populateLayerMetadata(layer)
        self.populateLayerFields(layer)
        self.tabLayerInfo.setCurrentWidget(self.tabMetadata)


    def populateLayerMetadata(self, layer):
        pass


    def populateLayerFields(self, layer):
        if layer.type() == layer.VectorLayer:
            self.tabLayerInfo.setTabEnabled(1, True)
            fields = layer.fields()
            self.tableFields.setRowCount(len(fields))
            for i, field in enumerate(fields):
                item = QTableWidgetItem()
                item.setCheckState(Qt.Checked)
                self.tableFields.setItem(i, 0, item)
                self.tableFields.setItem(i, 1, QTableWidgetItem(field.name()))             
        else:
            self.tabLayerInfo.setTabEnabled(1, False)

    def showContextMenu(self, pos):
        item = self.tableLayers.itemAt(pos)
        if item is None:
            return
        row = self.tableLayers.row(item)
        name = self.tableLayers.item(row, 1).text()
        menu = QMenu()
        menu.addAction("View metadata", lambda: self.viewMetadata(name))
        if self.isDataPublished[name]:
            menu.addAction("View WMS layer", lambda: self.viewWms(name))
            menu.addAction("Unpublish data", lambda: self.unpublishData(name))
        if self.isMetadataPublished[name]:    
            menu.addAction("Unpublish metadata", lambda: self.unpublishMetadata(name))
        menu.popup(self.tableLayers.viewport().mapToGlobal(pos))

    def publishableLayers(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() 
                if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]]
        return layers

    def populateLayers(self):
        self.tableLayers.setRowCount(0)
        layers = self.publishableLayers()
        self.tableLayers.setRowCount(len(layers))
        for i, layer in enumerate(layers):
            item = QTableWidgetItem()
            item.setCheckState(Qt.Unchecked)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 0, item)
            item = QTableWidgetItem(layer.name())
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 1, item)
            self.isMetadataPublished[layer.name()] = self.isMetadataOnServer(layer)
            item = QTableWidgetItem("X" if self.isMetadataPublished[layer.name()] else "")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 2, item)
            self.isDataPublished[layer.name()] = self.isDataOnServer(layer)            
            item = QTableWidgetItem("X" if self.isDataPublished[layer.name()] else "")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 3, item)

    def populateComboBoxes(self):
        self.populateComboCatalogue()
        self.populateComboMapServer()

    def populateComboMapServer(self):
        self.comboMapServer.clear()
        self.comboMapServer.addItems(geodataServers().keys())

    def populateComboCatalogue(self):
        self.comboCatalogue.clear()
        self.comboCatalogue.addItems(metadataServers().keys())

    def layerClicked(self):
        layers = list(QgsProject.instance().mapLayers().values())
        layer = layers[self.tableLayers.currentRow()]

    def isMetadataOnServer(self, layer):
        try:
            catalog = metadataServers()[self.comboCatalogue.currentText()].catalog()
            return catalog.metadata_exists(layer.name())
        except KeyError:
            return False
        except:
            self.bar.pushMessage("Error", "Could not connect to selected metadata server", level=Qgis.Warning, duration=5)

    def isDataOnServer(self, layer):
        try:
            catalog = geodataServers()[self.comboMapServer.currentText()].catalog()
            return catalog.layer_exists(layer.name())
        except KeyError:
            return False
        except:
            self.bar.pushMessage("Error", "Could not connect to selected data server", level=Qgis.Warning, duration=5)


    def defineConnectionsData(self):
        current = self.comboMapServer.currentText()
        self.openConnectionsDialog()
        self.populateComboMapServer()
        if current in geodataServers().keys():
            self.comboMapServer.setCurrentText(current)

    def defineConnectionsMetadata(self):
        current = self.comboMapServer.currentText()
        self.openConnectionsDialog()
        self.populateComboCatalogue()
        if current in metadataServers().keys():
            self.comboCatalogue.setCurrentText(current)            

    def openConnectionsDialog(self):
        dlg = ServerConnectionsDialog(iface.mainWindow())
        dlg.exec_()

    def unpublishData(self, name):
        catalog = geodataServers()[self.comboMapServer.currentText()].catalog()
        catalog.delete_layer(name)

    def unpublishMetadata(self, name):
        catalog = metadataServers()[self.comboCatalogue.currentText()].catalog()
        catalog.delete_metadata(name)

    def viewWms(self, name):
        pass

    def viewMetadata(self, name):
        pass        

    def publish(self):
        pass






