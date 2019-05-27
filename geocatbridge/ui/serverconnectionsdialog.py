import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtCore import *
from qgis.gui import *
from qgis.core import *

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'serverconnectionsdialog.ui'))

class ServerConnectionsDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(ServerConnectionsDialog, self).__init__(parent)
        self.currentServer = None
        self.setupUi(self)
        
        self.addMenuToButtonNew()
        self.addAuthWidgets()
        self.buttonRemove.clicked.connect(self.buttonRemoveClicked)
        self.populateServers()
        self.listServers.currentItemChanged.connect(self.currentServerChanged)
        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.bar)
        self.setCurrentServer(None)
        self.buttonBox.accepted.connect(self.accepted)
        self.buttonBox.rejected.connect(self.close)

    def currentServerChanged(self, new, old):
        if new is None:
            self.setCurrentServer(new)
            return
        else:
            server = geodataServers()[new.text()]
            if self.currentServer is not None and new is not None:
                if server.name == self.currentServer.name:
                    return
            if not self.saveCurrentServer():
                self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)
                self.listServers.setCurrentItem(old)
                return
            self.setCurrentServer(server)
                    
    def saveCurrentServer(self):
        w = self.stackedWidget.currentWidget()
        server = None
        if w == self.widgetEmpty:
            return True
        elif w == self.widgetGeoserver:
            server = self.createGeoserverServer()
        elif w == self.widgetPostgis:
            pass
        elif w == self.widgetMetadata:
            pass
        elif w == self.widgetGeocatLive:
            pass

        if server is None:
            return False
        else:
            if self.currentServer is not None:
                print(self.currentServer.name)
                removeServer(self.currentServer)
                item = self.listServers.findItems(self.currentServer.name, Qt.MatchExactly)[0]
                item.setText(server.name)
            print (server.name)
            addServer(server)
            return True
        
    def createGeoserverServer(self):
        ##TODO check validity of name and values        
        name = self.txtGeoserverName.text()
        url = self.txtGeoserverUrl.text()
        workspace = self.txtGeoserverWorkspace.text()
        url = self.txtGeoserverUrl.text()
        authid = self.geoserverAuth.configId()
        datastore = self.comboDatastore.currentText()
        storage = GeoserverServer.UPLOAD_DATA if self.radioUploadData.isChecked() else self.STORE_IN_POSTGIS
        server = GeoserverServer(name, url, authid, storage, workspace, datastore)
        return server

    def addAuthWidgets(self):
        self.geoserverAuth = QgsAuthConfigSelect()
        vlayout = QHBoxLayout()
        vlayout.addWidget(self.geoserverAuth)
        self.geoserverAuthWidget.setLayout(vlayout)
        ##

    def addMenuToButtonNew(self):
        menu = QMenu()
        menu.addAction("GeoServer", self.addGeoserver)
        menu.addAction("MapServer", self.addMapserver)
        menu.addAction("GeoCat Live", self.addGeocatLive)
        menu.addAction("GeoNetwork", self.addGeonetwork)
        menu.addAction("CSW", self.addCSW)
        menu.addAction("PostGIS", self.addPostGis)
        self.buttonNew.setMenu(menu)

    def buttonRemoveClicked(self):
        item = self.listServers.currentItem()
        name = item.text()
        removeServer(name)
        self.listServers.takeItem(self.listServers.currentRow)
        self.listServers.setCurrentItem(None)        

    def populateServers(self):
        self.listServers.clear()
        servers = allServers().keys()      
        for server in servers:
            self.listServers.addItem(server)

    def addGeoserver(self):
        if self.saveCurrentServer():                    
            name = self.getNewName("Geoserver")
            server = GeoserverServer(name)            
            addServer(server)
            item = self.listServers.addItem(server.name)
            self.listServers.setCurrentItem(item)
            self.setCurrentServer(server)       

    def addMapserver(self):
        if self.saveCurrentServer():
            pass

    def addGeocatLive(self):
        if self.saveCurrentServer():
            pass

    def addGeonetwork(self):
        if self.saveCurrentServer():
            pass

    def addCSW(self):
        if self.saveCurrentServer():
            pass

    def addPostGis(self):
        if self.saveCurrentServer():
            pass

    def setCurrentServer(self, server):
        self.currentServer = server
        if server is None:
            self.stackedWidget.setCurrentWidget(self.widgetEmpty)
        elif isinstance(server, GeoserverServer):
            self.stackedWidget.setCurrentWidget(self.widgetGeoserver)
            self.txtGeoserverName.setText(server.name)
            self.txtGeoserverUrl.setText(server.url)
            self.txtGeoserverWorkspace.setText(server.workspace)
            self.radioUploadData.setChecked(server.storage == server.UPLOAD_DATA)
            self.radioStoreInPostgis.setChecked(server.storage == server.STORE_IN_POSTGIS)
            self.geoserverAuth.setConfigId(server.authid)
        elif isinstance(server, MapserverServer):
            pass
            #TODO
        elif isinstance(server, PostgisServer):
            pass
            #TODO
        elif isinstance(server, GeonetworkServer):
            pass
            #TODO
        elif isinstance(server, GeocatLiveServer):
            pass
            #TODO
        elif isinstance(server, CswServer):
            pass
            #TODO

    def getNewName(self, name):
        servers = list(allServers().keys())
        i = 1
        while True:
            n = name + str(i)
            if n not in servers:
                return n
            else:
                i += 1

    def hasChanges(self):
        return False

    def accepted(self):
        if self.saveCurrentServer():
            self.close()
        else:
            self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)    

    def onClose(self, evt):
        if self.hasChanges():
            res = QMessageBox.question(self, "Servers", "Do you want to close without saving the current changes?",
                                QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes,
                                QMessageBox.Yes)
        
            if res == QMessageBox.Yes:
                evt.accept()
            else:
                evt.ignore()
        else:
            evt.accept()
