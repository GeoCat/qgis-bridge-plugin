import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import allServers
 
WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'serverconnectionsdialog.ui'))

class ServerConnectionsDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeocatBridgeDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.buttonNew.clicked.connect(self.buttonNewClicked)
        self.buttonRemove.clicked.connect(self.buttonRemoveClicked)
        self.populateServers()

        
    def buttonNewClicked(self):
        pass

    def buttonNewClicked(self):
        pass

    def populateLayers(self):
        servers = allServers
    	layers = QgsProject.instance().mapLayers().values()
    	self.tableWidget.setRowCount(len(layers))
    	for i, layer in enumerate(layers):
    		item = QListWidgetItem()
    		item.setCheckState(Qt.Unchecked)
    		self.tableWidget.setItem(i, 0, item)
    		self.tableWidget.setItem(i, 1, QTableWidgetItem(layer.name()))
    		self.tableWidget.setItem(i, 2, QTableWidgetItem("X" if isMetadataOnServer(layer) else ""))
    		self.tableWidget.setItem(i, 3, QTableWidgetItem("X" if isDataOnServer(layer) else ""))

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
    	layer = layers[self.tableWidget.currentRow()]




