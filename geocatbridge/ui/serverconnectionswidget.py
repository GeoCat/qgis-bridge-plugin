from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QListWidgetItem,
    QWidget,
    QFileDialog
)
from qgis.gui import QgsFileWidget, QgsAuthConfigSelect

from geocatbridge.publish.geonetwork import GeonetworkServer
from geocatbridge.publish.geoserver import GeoserverServer
from geocatbridge.publish.mapserver import MapserverServer
from geocatbridge.publish.postgis import PostgisServer
from geocatbridge.publish.servers import *
from geocatbridge.ui.newdataset import NewDatasetDialog
from geocatbridge.utils import gui, files
from geocatbridge.utils.feedback import FeedbackMixin

WIDGET, BASE = gui.loadUiType(__file__)


class ServerConnectionsWidget(FeedbackMixin, BASE, WIDGET):

    def __init__(self):
        super().__init__()
        self.currentServer = None
        self.currentServerHasChanges = False
        self.setupUi(self)

        self.cswAuth = QgsAuthConfigSelect()
        self.postgisAuth = QgsAuthConfigSelect()
        self.geoserverAuth = QgsAuthConfigSelect()
        self.mapserverAuth = QgsAuthConfigSelect()

        self.addMenuToButtonNew()
        self.addAuthWidgets()
        self.buttonRemove.clicked.connect(self.buttonRemoveClicked)
        self.populateServers()
        self.listServers.currentItemChanged.connect(self.currentServerChanged)
        self.setCurrentServer(None)
        self.buttonSave.clicked.connect(self.saveButtonClicked)
        self.comboGeoserverDataStorage.currentIndexChanged.connect(self.geoserverDatastorageChanged)
        self.btnConnectGeoserver.clicked.connect(self.testConnectionGeoserver)
        self.btnConnectPostgis.clicked.connect(self.testConnectionPostgis)
        self.btnConnectCsw.clicked.connect(self.testConnectionCsw)
        self.btnAddDatastore.clicked.connect(self.addPostgisDatastore)
        self.btnRefreshDatabases.clicked.connect(self.populatePostgisComboWithGeoserverPostgisServers)

        self.txtCswName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtCswNode.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisName.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtGeoserverUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtCswUrl.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisServerAddress.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisPort.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisSchema.textChanged.connect(self._setCurrentServerHasChanges)
        self.txtPostgisDatabase.textChanged.connect(self._setCurrentServerHasChanges)
        self.comboMetadataProfile.currentIndexChanged.connect(self._setCurrentServerHasChanges)
        self.comboGeoserverDatabase.currentIndexChanged.connect(self._setCurrentServerHasChanges)

        self.radioLocalPath.toggled.connect(self.mapserverStorageChanged)

        self.fileMapserver.setStorageMode(QgsFileWidget.GetDirectory)

        self.btnSaveServers.clicked.connect(self.saveServers)
        self.btnLoadServers.clicked.connect(self.loadServers)

        self.comboMetadataProfile.setVisible(False)
        self.labelMetadataProfile.setVisible(False)

    def checkServersHaveBeenDefined(self):
        if self.listServers.count():
            self.txtNoServers.setVisible(False)
            self.listServers.setVisible(True)
        else:
            self.txtNoServers.setVisible(True)
            self.listServers.setVisible(False)

    def saveServers(self):
        filename = QFileDialog.getSaveFileName(self, self.tr("Save servers"), "", '*.json')[0]
        if filename:
            if not filename.endswith("json"):
                filename += ".json"
            with open(filename, "w") as f:
                f.write(serversAsJsonString())

    def loadServers(self):
        filename = QFileDialog.getOpenFileName(self, self.tr("Load servers"), "", '*.json')[0]
        if filename:
            with open(filename) as f:
                servers = json.load(f)
            for server in servers:
                s = serverFromDefinition(server)
                if s.name not in allServers():
                    self.addServerItem(s)
                    addServer(s)

    def geoserverDatastorageChanged(self):
        storage = self.comboGeoserverDataStorage.currentIndex()
        if storage == GeoserverServer.POSTGIS_MANAGED_BY_BRIDGE:
            self.populatePostgisComboWithPostgisServers()
            self.comboGeoserverDatabase.setVisible(True)
            self.btnAddDatastore.setVisible(False)
            self.labelGeoserverDatastore.setVisible(True)
            self.btnRefreshDatabases.setVisible(False)
        elif storage == GeoserverServer.POSTGIS_MANAGED_BY_GEOSERVER:
            self.comboGeoserverDatabase.setVisible(True)
            self.btnAddDatastore.setVisible(True)
            self.labelGeoserverDatastore.setVisible(True)
            self.btnRefreshDatabases.setVisible(True)
            self.populatePostgisComboWithGeoserverPostgisServers()
        else:
            self.comboGeoserverDatabase.setVisible(False)
            self.btnAddDatastore.setVisible(False)
            self.labelGeoserverDatastore.setVisible(False)
            self.btnRefreshDatabases.setVisible(False)
        self._setCurrentServerHasChanges()

    def addPostgisDatastore(self):
        server = self.createGeoserverServer()
        if server is None:
            self.showErrorBar("Error", "Wrong values in server definition")
            return
        dlg = NewDatasetDialog(self)
        dlg.exec_()
        name = dlg.name
        if name is None:
            return

        def _entry(k, v):
            return {"@key": k, "$": v}

        ds = {
            "dataStore": {
                "name": dlg.name,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "entry": [
                        _entry("schema", dlg.schema),
                        _entry("port", dlg.port),
                        _entry("database", dlg.database),
                        _entry("passwd", dlg.password),
                        _entry("user", dlg.username),
                        _entry("host", dlg.host),
                        _entry("dbtype", "postgis")
                    ]
                }
            }
        }
        try:
            gui.execute(lambda: server.addPostgisDatastore(ds))
            self.populatePostgisComboWithGeoserverPostgisServers()
        except Exception as e:
            self.showErrorBar("Error", "Could not create new PostGIS dataset", propagate=e)

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
                res = self.showQuestionBox("Servers", "Do you want to save changes to the current server?",
                                           buttons=self.Buttons.CANCEL | self.Buttons.NO | self.Buttons.YES,
                                           defaultButton=self.Buttons.YES)
                if res == self.Buttons.YES:
                    if not self.saveCurrentServer():
                        self.showErrorBar("Error", "Wrong values in current item")
                        self.listServers.setCurrentItem(old)
                    else:
                        self.setCurrentServer(server)
                elif res == self.Buttons.CANCEL:
                    self.listServers.setCurrentItem(old)
                else:
                    self.setCurrentServer(server)
            else:
                self.setCurrentServer(server)

    def _testConnection(self, server):
        if server is None:
            self.showErrorBar("Error", "Wrong values in current item")
        else:
            if gui.execute(server.testConnection):
                self.showSuccessBar("Success", "Connection succesfully established with server")
            else:
                self.showErrorBar("Error", "Could not connect with server")

    def testConnectionPostgis(self):
        server = self.createPostgisServer()
        self._testConnection(server)

    def testConnectionGeoserver(self):
        server = self.createGeoserverServer()
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
        # TODO check validity of name and values
        name = self.txtGeoserverName.text().strip()
        url = self.txtGeoserverUrl.text().strip()
        authid = self.geoserverAuth.configId()
        if not bool(authid):
            return None
        storage = self.comboGeoserverDataStorage.currentIndex()
        postgisdb = None
        if storage in [GeoserverServer.POSTGIS_MANAGED_BY_BRIDGE, GeoserverServer.POSTGIS_MANAGED_BY_GEOSERVER]:
            postgisdb = self.comboGeoserverDatabase.currentText()
        use_original_data_source = self.chkUseOriginalDataSource.isChecked()
        use_vector_tiles = self.chkUseVectorTiles.isChecked()

        if "" in [name, url]:
            return None
        server = GeoserverServer(
            name, url, authid, storage, postgisdb, use_original_data_source,
            use_vector_tiles
        )
        return server

    def createPostgisServer(self):
        # TODO check validity of name and values
        name = self.txtPostgisName.text()
        host = self.txtPostgisServerAddress.text()
        port = self.txtPostgisPort.text()
        schema = self.txtPostgisSchema.text()
        database = self.txtPostgisDatabase.text()
        authid = self.postgisAuth.configId()
        server = PostgisServer(name, authid, host, port, schema, database)
        return server

    def createGeonetworkServer(self):
        # TODO check validity of name and values
        name = self.txtCswName.text()
        node = self.txtCswNode.text()
        authid = self.cswAuth.configId()
        if bool(authid):
            url = self.txtCswUrl.text()
            profile = self.comboMetadataProfile.currentIndex()
            server = GeonetworkServer(name, url, authid, profile, node)
            return server

    def createMapserverServer(self):
        # TODO check validity of name and values
        name = self.txtMapserverName.text()
        authid = self.mapserverAuth.configId()
        host = self.txtMapserverHost.text()
        try:
            port = int(self.txtMapserverPort.text())
        except Exception as e:
            self.logWarning(e)
            return None
        local = self.radioLocalPath.isChecked()
        if local:
            folder = self.fileMapserver.filePath()
        else:
            folder = self.txtRemoteFolder.text()
        url = self.txtMapserverUrl.text()
        services_path = self.txtMapServicesPath.text()
        proj_folder = self.txtProjFolder.text()
        server = MapserverServer(name, url, local, folder, authid, host, port, services_path, proj_folder)
        return server

    def addAuthWidgets(self):
        self.geoserverAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.geoserverAuth)
        self.geoserverAuthWidget.setLayout(layout)
        self.geoserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.mapserverAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.mapserverAuth)
        self.mapserverAuthWidget.setLayout(layout)
        self.mapserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.postgisAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(layout)
        self.postgisAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())
        self.cswAuth.selectedConfigIdChanged.connect(self._setCurrentServerHasChanges)
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.cswAuth)
        self.cswAuthWidget.setLayout(layout)
        self.cswAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())

    def addMenuToButtonNew(self):
        menu = QMenu()
        menu.addAction("GeoServer", lambda: self._addServer("GeoServer", GeoserverServer))
        menu.addAction("MapServer", lambda: self._addServer("MapServer", MapserverServer))
        menu.addAction("GeoNetwork", lambda: self._addServer("GeoNetwork", GeonetworkServer))
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
        self.checkServersHaveBeenDefined()

    def populateServers(self):
        self.listServers.clear()
        servers = allServers().values()
        for server in servers:
            self.addServerItem(server)
        self.checkServersHaveBeenDefined()

    def addServerItem(self, server):
        widget = ServerItemWidget(server)
        item = QListWidgetItem(self.listServers)
        item.setSizeHint(widget.sizeHint())
        self.listServers.addItem(item)
        self.listServers.setItemWidget(item, widget)
        self.checkServersHaveBeenDefined()
        return item

    def _addServer(self, name, clazz):
        if self.currentServerHasChanges:
            self.showWarningBar("Warning", "Save changes to current server before creating one")
        else:
            name = self.getNewName(name)
            server = clazz(name)
            addServer(server)
            self.setCurrentServer(server)
            item = self.addServerItem(server)
            self.listServers.setCurrentItem(item)

    def populatePostgisComboWithPostgisServers(self):
        self.comboGeoserverDatabase.clear()
        servers = allServers().values()
        for s in servers:
            if isinstance(s, PostgisServer):
                self.comboGeoserverDatabase.addItem(s.name)

    def populatePostgisComboWithGeoserverPostgisServers(self):
        self.comboGeoserverDatabase.clear()
        server = self.createGeoserverServer()
        if server is None:
            self.showErrorBar("Error", "Wrong values in server definition")
            return
        try:
            datastores = gui.execute(server.postgisDatastores)
        except Exception as e:
            self.logWarning(e)
            datastores = []
        if datastores:
            self.comboGeoserverDatabase.addItems(datastores)
        else:
            self.showWarningBar("Warning", "No PostGIS datastores in server or could not retrieve them")

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
            self.geoserverAuth.setConfigId(server.authid)
            self.comboGeoserverDataStorage.blockSignals(True)
            self.comboGeoserverDataStorage.setCurrentIndex(server.storage)
            self.geoserverDatastorageChanged()
            if server.postgisdb is not None:
                self.comboGeoserverDatabase.setCurrentText(server.postgisdb)
            self.chkUseOriginalDataSource.setChecked(server.useOriginalDataSource)
            self.chkUseVectorTiles.setChecked(server.useVectorTiles)
            self.comboGeoserverDataStorage.blockSignals(False)
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

        self.currentServerHasChanges = False

    @staticmethod
    def getNewName(name):
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
            self.showErrorBar("Error", "Wrong values in current item")

    def canClose(self):
        if self.currentServerHasChanges:
            res = self.showQuestionBox("Servers", "Do you want to close without saving the current changes?",
                                       buttons=self.Buttons.CANCEL | self.Buttons.NO | self.Buttons.YES,
                                       defaultButton=self.Buttons.YES)

            return res == self.Buttons.YES
        else:
            return True


class ServerItemWidget(QWidget):
    def __init__(self, server, parent=None):
        super(ServerItemWidget, self).__init__(parent)
        self.server = server
        self.layout = QHBoxLayout()
        self.label = QLabel()
        self.label.setText(server.name)
        self.iconLabel = QLabel()
        self.iconLabel.setPixmap(QPixmap(self.iconPath()))
        self.iconLabel.setFixedWidth(50)
        self.layout.addWidget(self.iconLabel)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    def iconPath(self):
        return files.getIconPath(f"{self.server.__class__.__name__.lower()[:-6]}_black")

    def setServerName(self, name):
        self.label.setText(name)

    def serverName(self):
        return self.label.text()
