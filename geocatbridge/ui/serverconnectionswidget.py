import os
from qgis.PyQt import uic
from geocatbridge.publish.servers import *
from geocatbridge.publish.geonetwork import GeonetworkServer
from geocatbridge.publish.geoserver import GeoserverServer
from geocatbridge.publish.geocatlive import GeocatLiveServer
from geocatbridge.publish.mapserver import MapserverServer
from geocatbridge.publish.postgis import PostgisServer
from qgis.PyQt.QtWidgets import (
    QSizePolicy, 
    QHBoxLayout, 
    QMessageBox, 
    QLabel, 
    QMenu, 
    QListWidgetItem, 
    QWidget
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.gui import QgsMessageBar, QgsFileWidget, QgsAuthConfigSelect
from qgis.core import Qgis
from geocatbridge.utils.gui import execute

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'serverconnectionswidget.ui'))

class ServerConnectionsWidget(BASE, WIDGET):

    def __init__(self):
        super(ServerConnectionsWidget, self).__init__()
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
        self.buttonSave.clicked.connect(self.saveButtonClicked)
        self.radioUploadData.toggled.connect(self.datastoreChanged)
        self.radioLocalPath.toggled.connect(self.mapserverStorageChanged)
        self.btnConnectGeoserver.clicked.connect(self.testConnectionGeoserver)
        self.btnConnectPostgis.clicked.connect(self.testConnectionPostgis)
        self.btnConnectGeocatLive.clicked.connect(self.testConnectionGeocatLive)
        self.btnConnectCsw.clicked.connect(self.testConnectionCsw)
        self.chkManagedWorkspace.stateChanged.connect(self.managedWorkspaceChanged)

        self.txtCswName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtCswNode.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeocatLiveName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtCswUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisServerAddress.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisPort.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisSchema.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisDatabase.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverWorkspace.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeocatLiveIdentifier.textChanged.connect(self._setCurrentServerHasChanges)
        self.comboMetadataProfile.currentIndexChanged.connect(self._setCurrentServerHasChanges)
        self.comboDatastore.currentIndexChanged.connect(self._setCurrentServerHasChanges)

        self.fileMapserver.setStorageMode(QgsFileWidget.GetDirectory)

    def datastoreChanged(self, checked):
        self.comboDatastore.setEnabled(not checked)
        #self.btnNewDatastore.setEnabled(not checked)
        self._setCurrentServerHasChanges()

    def managedWorkspaceChanged(self, state):
        self.txtGeoserverWorkspace.setEnabled(state == Qt.Unchecked)
        self._setCurrentServerHasChanges()

    def mapserverStorageChanged(self, checked):
        self.labelLocalFolder.setVisible(checked)
        self.labelRemoteFolder.setVisible(not checked)
        self.fileMapserver.setVisible(checked)
        self.txtRemoteFolder.setVisible(not checked)
        self.labelHost.setVisible(not checked)
        self.labelPort.setVisible(not checked)
        self.labelMapserverCredentials.setVisible(not checked)
        self.txtMapserverHost.setVisible(not checked)
        self.txtMapserverPort.setVisible(not checked)
        self.mapserverAuthWidget.setVisible(not checked)
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
                res = QMessageBox.question(self, self.tr("Servers"), self.tr("Do you want to save changes to the current server?"),
                                QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes,
                                QMessageBox.Yes)        
                if res == QMessageBox.Yes:
                    if not self.saveCurrentServer():
                        self.bar.pushMessage(self.tr("Error"), self.tr("Wrong values in current item"), level=Qgis.Warning, duration=5)
                        self.listServers.setCurrentItem(old)
                    else:
                        self.setCurrentServer(server)
                elif res == QMessageBox.Cancel:
                    self.listServers.setCurrentItem(old)
                else:
                    self.setCurrentServer(server)
            else:
                self.setCurrentServer(server)                    

    def _testConnection(self, server):
        if server is None:
            self.bar.pushMessage(self.tr("Error"), self.tr("Wrong values in current item"), level=Qgis.Warning, duration=5)
        else:
            if execute(server.testConnection):
                self.bar.pushMessage(self.tr("Success"), self.tr("Connection succesfully established with server"), level=Qgis.Success, duration=5)
            else:
                self.bar.pushMessage(self.tr("Error"), self.tr("Could not connect with server"), level=Qgis.Warning, duration=5)                    
    
    def testConnectionPostgis(self):
        server = self.createPostgisServer()
        self._testConnection(server)
        
    def testConnectionGeoserver(self):
        server = self.createGeoserverServer()
        self._testConnection(server)

    def testConnectionGeocatLive(self):
        server = self.createGeocatLiveServer()        
        self._testConnection(server)

    def testConnectionCsw(self):
        server = self.createGeonetworkServer()
        self._testConnection(server)

    def saveCurrentServer(self):
        w = self.stackedWidget.currentWidget()
        server = None
        if w == self.widgetEmpty:
            return True
        elif w == self.widgetGeoserver:
            server = self.createGeoserverServer()
        elif w == self.widgetMapserver:
            server = self.createMapserverServer()             
        elif w == self.widgetPostgis:
            server = self.createPostgisServer()
        elif w == self.widgetMetadataCatalog:
            server = self.createGeonetworkServer()
        elif w == self.widgetGeocatLive:
            server = self.createGeocatLiveServer()            
        if server is None:
            return False
        else:
            if self.currentServer is not None:
                removeServer(self.currentServer.name)
                item = self.itemFromServerName(self.currentServer.name)
                self.listServers.itemWidget(item).setServerName(server.name)
            addServer(server)
            self.currentServer = server
            return True
        
    def itemFromServerName(self, name):
        for i in range(self.listServers.count()):
            item = self.listServers.item(i)
            if name == self.listServers.itemWidget(item).serverName():
                return item

    def createGeoserverServer(self):
        ##TODO check validity of name and values        
        name = self.txtGeoserverName.text().strip()
        url = self.txtGeoserverUrl.text().strip()
        if self.chkManagedWorkspace.isChecked():
            workspace = None
        else:
            workspace = self.txtGeoserverWorkspace.text().strip()
        authid = self.geoserverAuth.configId()
        if self.radioUploadData.isChecked():
            storage = GeoserverServer.UPLOAD_DATA
            postgisdb = None
        else:
            storage = GeoserverServer.STORE_IN_POSTGIS
            postgisdb = self.comboDatastore.currentText()
        if "" in [name, url, workspace]:
            return None
        server = GeoserverServer(name, url, authid, storage, workspace, postgisdb)
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
        node = self.txtCswNode.text()
        authid = self.cswAuth.configId()
        url = self.txtCswUrl.text()
        profile = self.comboMetadataProfile.currentIndex()
        server = GeonetworkServer(name, url, authid, profile, node)
        return server

    def createMapserverServer(self):
        ##TODO check validity of name and values        
        name = self.txtMapserverName.text()                
        authid = self.mapserverAuth.configId()
        host = self.txtMapserverHost.text()
        try:
            port = int(self.txtMapserverPort.text())
        except:
            return None
        local = self.radioLocalPath.isChecked()
        if local:
            folder = self.fileMapserver.filePath()
        else:
            folder = self.txtRemoteFolder.text()
        url = self.txtMapserverUrl.text()
        servicesPath = self.txtMapServicesPath.text()
        projFolder = self.txtProjFolder.text()
        server = MapserverServer(name, url, local, folder, authid, host, port, servicesPath, projFolder)
        return server

    def createGeocatLiveServer(self):
        name = self.txtGeocatLiveName.text()        
        geoserverAuthid = self.geocatLiveGeoserverAuth.configId()
        geonetworkAuthid = self.geocatLiveGeonetworkAuth.configId()
        userid = self.txtGeocatLiveIdentifier.text()        
        server = GeocatLiveServer(name, userid, geoserverAuthid, geonetworkAuthid)
        return server

    def addAuthWidgets(self):
        self.geoserverAuth = QgsAuthConfigSelect()
        self.geoserverAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.geoserverAuth)
        self.geoserverAuthWidget.setLayout(layout)
        self.geoserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.mapserverAuth = QgsAuthConfigSelect()
        self.mapserverAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.mapserverAuth)
        self.mapserverAuthWidget.setLayout(layout)
        self.mapserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.postgisAuth = QgsAuthConfigSelect()        
        self.postgisAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(layout)
        self.postgisAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.cswAuth = QgsAuthConfigSelect()
        self.cswAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.cswAuth)
        self.cswAuthWidget.setLayout(layout)
        self.cswAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.geocatLiveGeoserverAuth = QgsAuthConfigSelect()
        self.geocatLiveGeoserverAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.geocatLiveGeoserverAuth)
        self.geocatLiveGeoserverAuthWidget.setLayout(layout)
        self.geocatLiveGeoserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.geocatLiveGeonetworkAuth = QgsAuthConfigSelect()
        self.geocatLiveGeonetworkAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.geocatLiveGeonetworkAuth)
        self.geocatLiveGeonetworkAuthWidget.setLayout(layout)
        self.geocatLiveGeonetworkAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())

    def addMenuToButtonNew(self):
        menu = QMenu()
        menu.addAction("GeoServer", lambda: self._addServer("GeoServer", GeoserverServer))
        menu.addAction("MapServer", lambda: self._addServer("MapServer", MapserverServer))
        menu.addAction("GeoCat Live", lambda: self._addServer("GeoCat Live", GeocatLiveServer))
        menu.addAction("GeoNetwork", lambda: self._addServer("GeoNetwork", GeonetworkServer))
        #menu.addAction("CSW", lambda: self._addServer("CSW", CswServer))
        menu.addAction("PostGIS", lambda: self._addServer("PostGIS", PostgisServer))
        self.buttonNew.setMenu(menu)

    def buttonRemoveClicked(self):
        item = self.listServers.currentItem()
        if item is None:
            return
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
        if self.currentServerHasChanges:
            self.bar.pushMessage(self.tr("Save changes to current server before creating one"), level=Qgis.Warning, duration=5)
        else:        
            name = self.getNewName(name)
            server = clazz(name)            
            addServer(server)
            self.setCurrentServer(server)
            item = self.addServerItem(server)
            self.listServers.setCurrentItem(item)

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
            if server.workspace is None:
                self.txtGeoserverWorkspace.setText("")
                self.chkManagedWorkspace.setChecked(True)
            else:
                self.txtGeoserverWorkspace.setText(server.workspace)
                self.chkManagedWorkspace.setChecked(False)
            self.geoserverAuth.setConfigId(server.authid)
            self.populatePostgisCombo()
            if server.postgisdb is not None:
                self.comboDatastore.setCurrentText(server.postgisdb)
            self.radioUploadData.setChecked(server.storage == server.UPLOAD_DATA)
            self.radioStoreInPostgis.setChecked(server.storage == server.STORE_IN_POSTGIS)                
        elif isinstance(server, MapserverServer):
            self.stackedWidget.setCurrentWidget(self.widgetMapserver)
            self.txtMapserverName.setText(server.name)            
            self.fileMapserver.setFilePath(server.folder)
            self.txtRemoteFolder.setText(server.folder)
            self.txtMapserverHost.setText(server.host)
            self.txtMapserverPort.setText(str(server.port))
            self.mapserverAuth.setConfigId(server.authid)
            self.txtMapserverUrl.setText(server.url)
            self.txtMapServicesPath.setText(server.servicesPath)
            self.txtProjFolder.setText(server.projFolder)
            self.radioLocalPath.setChecked(server.useLocalFolder)
            self.radioFtp.setChecked(not server.useLocalFolder)
            self.mapserverStorageChanged(server.useLocalFolder)
        elif isinstance(server, PostgisServer):
            self.stackedWidget.setCurrentWidget(self.widgetPostgis)
            self.txtPostgisName.setText(server.name)
            self.txtPostgisDatabase.setText(server.database)
            self.txtPostgisPort.setText(server.port)
            self.txtPostgisServerAddress.setText(server.host)
            self.txtPostgisSchema.setText(server.schema)            
            self.postgisAuth.setConfigId(server.authid)
        elif isinstance(server, (GeonetworkServer, CswServer)):
            self.stackedWidget.setCurrentWidget(self.widgetMetadataCatalog)
            self.txtCswName.setText(server.name)
            self.txtCswNode.setText(server.node)
            self.txtCswUrl.setText(server.url)            
            self.cswAuth.setConfigId(server.authid)
            self.comboMetadataProfile.setCurrentIndex(server.profile)
        elif isinstance(server, GeocatLiveServer):
            self.stackedWidget.setCurrentWidget(self.widgetGeocatLive)
            self.txtGeocatLiveName.setText(server.name)
            self.txtGeocatLiveIdentifier.setText(server.userid)          
            self.geocatLiveGeoserverAuth.setConfigId(server.geoserverAuthid)
            self.geocatLiveGeonetworkAuth.setConfigId(server.geonetworkAuthid)

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
            self.bar.pushMessage(self.tr("Error"), self.tr("Wrong values in current item"), level=Qgis.Warning, duration=5)    

    def onClose(self, evt):
        if self.currentServerHasChanges:
            res = QMessageBox.question(self, self.tr("Servers"), self.tr("Do you want to close without saving the current changes?"),
                                QMessageBox.Cancel | QMessageBox.No | QMessageBox.Yes,
                                QMessageBox.Yes)
        
            if res == QMessageBox.Yes:
                evt.accept()
            else:
                evt.ignore()
        else:
            evt.accept()

class ServerItemWidget(QWidget):
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