import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtCore import *
from qgis.gui import *
from qgis.core import *
from qgiscommons2.gui import execute

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
        self.populatePostgisCombo()
        self.listServers.currentItemChanged.connect(self.currentServerChanged)
        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.bar)
        self.setCurrentServer(None)
        self.buttonBox.accepted.connect(self.saveButtonClicked)
        self.buttonBox.rejected.connect(self.close)
        self.radioUploadData.toggled.connect(self.datastoreChanged)
        self.btnConnectGeoserver.clicked.connect(self.testConnectionGeoserver)
        self.btnConnectPostgis.clicked.connect(self.testConnectionPostgis)

        self.txtCswName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtCswUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisServerAddress.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisPort.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisSchema.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisDatabase.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverWorkspace.textChanged.connect(self._setCurrentServerHasChanges)
        self.comboMetadataProfile.currentIndexChanged.connect(self._setCurrentServerHasChanges)
        self.comboDatastore.currentIndexChanged.connect(self._setCurrentServerHasChanges)

    def datastoreChanged(self, checked):
        self.comboDatastore.setEnabled(not checked)
        #self.btnNewDatastore.setEnabled(not checked)
        self._setCurrentServerHasChanges()

    def currentServerChanged(self, new, old):
        if new is None:
            self.setCurrentServer(new)
            return
        else:
            name = self.listServers.itemWidget(new).serverName()
            server = allServers()[name]
            if self.currentServer is not None and new is not None:
                if server.name == self.currentServer.name:
                    return
            if self.currentServerHasChanges:
                res = QMessageBox.question(self, "Servers", "Do you want to save changes to the current server?",
                                QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes,
                                QMessageBox.Yes)        
                if res == QMessageBox.Yes:
                    if not self.saveCurrentServer():
                        self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)
                        self.listServers.setCurrentItem(old)
                    else:
                        self.setCurrentServer(server)
                elif res == QMessageBox.Cancel:
                    print(self.listServers.itemWidget(old).serverName())
                    self.listServers.setCurrentItem(old)
                else:
                    self.setCurrentServer(server)
            else:
                self.setCurrentServer(server)
                    
    def testConnectionPostgis(self):
        server = self.createPostgisServer()
        if server is None:
            self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)
        else:
            if execute(server.testConnection):
                self.bar.pushMessage("Success", "Connection succesfully established with server", level=Qgis.Success, duration=5)
            else:
                self.bar.pushMessage("Error", "Could not connect with server", level=Qgis.Warning, duration=5)

    def testConnectionGeoserver(self):
        server = self.createGeoserverServer()
        if server is None:
            self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)
        else:
            if execute(server.testConnection):
                self.bar.pushMessage("Success", "Connection succesfully established with server", level=Qgis.Success, duration=5)
            else:
                self.bar.pushMessage("Error", "Could not connect with server", level=Qgis.Warning, duration=5)

    def saveCurrentServer(self):
        w = self.stackedWidget.currentWidget()
        server = None
        if w == self.widgetEmpty:
            return True
        elif w == self.widgetGeoserver:
            server = self.createGeoserverServer()
        elif w == self.widgetPostgis:
            server = self.createPostgisServer()
        elif w == self.widgetMetadata:
            pass
        elif w == self.widgetGeocatLive:
            pass

        if server is None:
            return False
        else:
            if self.currentServer is not None:
                removeServer(self.currentServer.name)
                item = self.itemFromServerName(self.currentServer.name)
                self.listServers.itemWidget(item).setServerName(server.name)
            addServer(server)
            return True
        
    def itemFromServerName(self, name):
        for i in range(self.listServers.count()):
            item = self.listServers.item(i)
            if name == self.listServers.itemWidget(item).serverName():
                return item

    def createGeoserverServer(self):
        ##TODO check validity of name and values        
        name = self.txtGeoserverName.text()
        url = self.txtGeoserverUrl.text()
        workspace = self.txtGeoserverWorkspace.text()
        url = self.txtGeoserverUrl.text()
        authid = self.geoserverAuth.configId()
        datastore = self.comboDatastore.currentText()
        if self.radioUploadData.isChecked():
            storage = GeoserverServer.UPLOAD_DATA
            postgisdb = None
        else:
            storage = self.STORE_IN_POSTGIS
            postgisdb = self.comboDatastore.currentText()
        server = GeoserverServer(name, url, authid, storage, workspace, datastore, postgisdb)
        return server

    def createPostgisServer(self):
        ##TODO check validity of name and values        
        name = self.txtPostgisName.text()
        host = self.txtPostgisServerAddress.text()
        port = self.txtPostgisPort.text()
        schema = self.txtPostgisSchema.text()
        database = self.txtPostgisDatabase.text()
        authid = self.postgisAuth.configId()
        server = PostgisServer(name, authid, host, port, schema, database)
        return server

    def createGeonetworkServer(self):
        ##TODO check validity of name and values        
        name = self.txtCswName.text()        
        authid = self.cswAuth.configId()
        url = self.txtCswUrl.text()
        profile = self.comboMetadataProfile.currentIndex()
        server = GeonetworkServer(name, url, authid, profile)
        return server

    def addAuthWidgets(self):
        self.geoserverAuth = QgsAuthConfigSelect()
        vlayout = QHBoxLayout()
        vlayout.addWidget(self.geoserverAuth)
        self.geoserverAuthWidget.setLayout(vlayout)
        self.geoserverAuthWidget.setFixedHeight(2 * self.txtGeoserverUrl.height())
        self.postgisAuth = QgsAuthConfigSelect()
        vlayout = QHBoxLayout()
        vlayout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(vlayout)
        self.postgisAuthWidget.setFixedHeight(2 * self.txtGeoserverUrl.height())
        self.cswAuth = QgsAuthConfigSelect()
        vlayout = QHBoxLayout()
        vlayout.addWidget(self.cswAuth)
        self.cswAuthWidget.setLayout(vlayout)
        self.cswAuthWidget.setFixedHeight(2 * self.txtGeoserverUrl.height())
        ##

    def addMenuToButtonNew(self):
        menu = QMenu()
        menu.addAction("GeoServer", lambda: self._addServer("GeoServer", GeoserverServer))
        menu.addAction("MapServer", lambda: self._addServer("MapServer", MapserverServer))
        menu.addAction("GeoCat Live", lambda: self._addServer("GeoCat Live", GeocatLiveServer))
        menu.addAction("GeoNetwork", lambda: self._addServer("GeoNetwork", GeonetworkServer))
        menu.addAction("CSW", lambda: self._addServer("CSW", CswServer))
        menu.addAction("PostGIS", lambda: self._addServer("PostGIS", PostgisServer))
        self.buttonNew.setMenu(menu)

    def buttonRemoveClicked(self):
        item = self.listServers.currentItem()
        name = self.listServers.itemWidget(item).serverName()
        removeServer(name)
        self.listServers.takeItem(self.listServers.currentRow())
        self.listServers.setCurrentItem(None)        

    def populateServers(self):
        self.listServers.clear()
        servers = allServers().values()      
        for server in servers:
            self.addServerItem(server)
            
    def addServerItem(self, server):
        widget = ServerItemWidget(server)
        item = QListWidgetItem(self.listServers)
        item.setSizeHint(widget.sizeHint())
        self.listServers.addItem(item)
        self.listServers.setItemWidget(item, widget)
        return item

    def _addServer(self, name, clazz):
        if self.saveCurrentServer():                    
            name = self.getNewName(name)
            server = clazz(name)            
            addServer(server)
            item = self.addServerItem(server)
            self.listServers.setCurrentItem(item)
            self.setCurrentServer(server) 

    def populatePostgisCombo(self):
        self.comboDatastore.clear()
        servers = allServers().values()
        for s in servers:
            if isinstance(s, PostgisServer):
                self.comboDatastore.addItem(s.name)

    def _setCurrentServerHasChanges(self):
        self.currentServerHasChanges = True

    def setCurrentServer(self, server):
        self.currentServer = server
        if server is None:
            self.stackedWidget.setCurrentWidget(self.widgetEmpty)
        elif isinstance(server, GeoserverServer):
            self.stackedWidget.setCurrentWidget(self.widgetGeoserver)
            self.txtGeoserverName.setText(server.name)
            self.txtGeoserverUrl.setText(server.url)
            self.txtGeoserverWorkspace.setText(server.workspace)            
            self.geoserverAuth.setConfigId(server.authid)
            self.populatePostgisCombo()
            if server.postgisdb is not None:
                self.comboDatastore.setCurrentText(server.postgisdb)
            self.radioUploadData.setChecked(server.storage == server.UPLOAD_DATA)
            self.radioStoreInPostgis.setChecked(server.storage == server.STORE_IN_POSTGIS)                
        elif isinstance(server, MapserverServer):
            pass
            #TODO
        elif isinstance(server, PostgisServer):
            self.stackedWidget.setCurrentWidget(self.widgetPostgis)
            self.txtPostgisName.setText(server.name)
            self.txtPostgisDatabase.setText(server.database)
            self.txtPostgisPort.setText(server.port)
            self.txtPostgisServerAddress.setText(server.host)
            self.txtPostgisSchema.setText(server.schema)            
            self.postgisAuth.setConfigId(server.authid)
        elif isinstance(server, GeonetworkServer):
            pass
            #TODO
        elif isinstance(server, GeocatLiveServer):
            pass
            #TODO
        elif isinstance(server, CswServer):
            pass
            #TODO
        self.currentServerHasChanges = False

    def getNewName(self, name):
        servers = list(allServers().keys())
        i = 1
        while True:
            n = name + str(i)
            if n not in servers:
                return n
            else:
                i += 1

    def saveButtonClicked(self):
        if self.saveCurrentServer():
            self.currentServerHasChanges = False
        else:
            self.bar.pushMessage("Error", "Wrong values in current item", level=Qgis.Warning, duration=5)    

    def onClose(self, evt):
        if self.currentServerHasChanges:
            res = QMessageBox.question(self, "Servers", "Do you want to close without saving the current changes?",
                                QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes,
                                QMessageBox.Yes)
        
            if res == QMessageBox.Yes:
                evt.accept()
            else:
                evt.ignore()
        else:
            evt.accept()

class ServerItemWidget (QWidget):
    def __init__ (self, server, parent = None):
        super(ServerItemWidget, self).__init__(parent)
        self.server = server
        self.layout = QHBoxLayout()
        self.label = QLabel()
        self.label.setText(server.name)
        self.iconLabel = QLabel()
        self.iconLabel.setPixmap(QPixmap(self.iconPath(server)))
        self.iconLabel.setFixedWidth(50)
        self.layout.addWidget(self.iconLabel)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        
    def iconPath(self, server):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", 
                        "%s_black.png" % self.server.__class__.__name__.lower()[:-6])

    def setServerName(self, name):
        self.label.setText(name)

    def serverName(self):
        return self.label.text()