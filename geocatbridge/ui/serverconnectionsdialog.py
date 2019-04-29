import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import allServers
 
WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'serverconnectionsdialog.ui'))

class ServerConnectionsDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeocatBridgeDialog, self).__init__(parent)
        self.currentServer = None
        self.setupUi(self)
        
        self.addMenuToButtonNew()
        self.buttonRemove.clicked.connect(self.buttonRemoveClicked)
        self.populateServers()

        
    def addMenuToButtonNew(self):
        menu = QMenu()
        menu.addAction("GeoServer", self.addGeoserver)
        menu.addAction("MapServer", self.addMapserver)
        menu.addAction("GeoCat Live", self.addGeocatLive)
        menu.addAction("GeoNetwork", self.addGeonetwork)
        menu.addAction("CSW", self.addCSW)
        menu.addAction("PostGIS", self.addPostGis)

    def buttonRemoveClicked(self):
        pass

    def populateServers(self):
        servers = allServers()    	
    	for i, layer in enumerate(layers):
    		item = QListWidgetItem()
    		item.setCheckState(Qt.Unchecked)
    		self.tableWidget.setItem(i, 0, item)
    		self.tableWidget.setItem(i, 1, QTableWidgetItem(layer.name()))
    		self.tableWidget.setItem(i, 2, QTableWidgetItem("X" if isMetadataOnServer(layer) else ""))
    		self.tableWidget.setItem(i, 3, QTableWidgetItem("X" if isDataOnServer(layer) else ""))





