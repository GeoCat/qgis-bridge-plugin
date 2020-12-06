from typing import Union

from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QListWidgetItem,
    QWidget
)
from qgis.gui import QgsFileWidget, QgsAuthConfigSelect

from geocatbridge.utils import gui
from geocatbridge.utils.feedback import FeedbackMixin

from geocatbridge.servers import manager
from geocatbridge.servers.bases import ServerWidgetBase

WIDGET, BASE = gui.loadUiType(__file__)


class ServerConnectionsWidget(FeedbackMixin, BASE, WIDGET):

    def __init__(self):
        super().__init__()
        self._server_widgets = {}
        self.setupUi(self)

        # self.cswAuth = QgsAuthConfigSelect()
        self.postgisAuth = QgsAuthConfigSelect()
        # self.geoserverAuth = QgsAuthConfigSelect()
        # self.mapserverAuth = QgsAuthConfigSelect()

        self.addMenuToButtonNew()
        self.addAuthWidgets()
        self.buttonRemove.clicked.connect(self.buttonRemoveClicked)
        self.populateServerList()
        self.listServers.currentItemChanged.connect(self.currentServerChanged)
        self.showServerWidget()
        self.buttonSave.clicked.connect(self.saveButtonClicked)
        # self.comboGeoserverDataStorage.currentIndexChanged.connect(self.datastoreChanged)
        # self.btnConnectGeoserver.clicked.connect(self.testConnectionGeoserver)
        self.btnConnectPostgis.clicked.connect(self.testConnectionPostgis)
        # self.btnConnectCsw.clicked.connect(self.testConnectionCsw)
        # self.btnAddDatastore.clicked.connect(self.addPostgisDatastore)
        # self.btnRefreshDatabases.clicked.connect(self.loadManagedDbServers)

        # self.txtCswName.textChanged.connect(self.setDirty)
        # self.txtCswNode.textChanged.connect(self.setDirty)
        # # self.txtGeoserverName.textChanged.connect(self.setDirty)
        self.txtPostgisName.textChanged.connect(self.setDirty)
        # # self.txtGeoserverUrl.textChanged.connect(self.setDirty)
        # self.txtCswUrl.textChanged.connect(self.setDirty)
        self.txtPostgisServerAddress.textChanged.connect(self.setDirty)
        self.txtPostgisPort.textChanged.connect(self.setDirty)
        self.txtPostgisSchema.textChanged.connect(self.setDirty)
        self.txtPostgisDatabase.textChanged.connect(self.setDirty)
        # self.comboMetadataProfile.currentIndexChanged.connect(self.setDirty)

        # self.radioLocalPath.toggled.connect(self.mapserverStorageChanged)

        # self.fileMapserver.setStorageMode(QgsFileWidget.GetDirectory)

        # self.btnSaveServers.clicked.connect(self.saveServers)
        # self.btnLoadServers.clicked.connect(self.loadServers)

    @property
    def serverManager(self):
        return manager

    def toggleServerList(self):
        has_servers = self.listServers.count() > 0
        self.txtNoServers.setVisible(not has_servers)
        self.listServers.setVisible(has_servers)

    # def saveServers(self):
    #     filename = QFileDialog.getSaveFileName(self, self.tr("Save servers"), "", '*.json')[0]
    #     if filename:
    #         if not filename.endswith("json"):
    #             filename += ".json"
    #         with open(filename, "w") as f:
    #             f.write(serversAsJsonString())
    #
    # def loadServers(self):
    #     filename = QFileDialog.getOpenFileName(self, self.tr("Load servers"), "", '*.json')[0]
    #     if filename:
    #         with open(filename) as f:
    #             servers = json.load(f)
    #         for server in servers:
    #             s = serverFromDefinition(server)
    #             if s.name not in allServers():
    #                 self.addServerListItem(s)
    #                 addServer(s)

    def serverIsDirty(self) -> bool:
        widget = self.stackedWidget.currentWidget()
        if widget and hasattr(widget, ServerWidgetBase.isDirty.__name__):
            return widget.isDirty
        return False

    def serverSetClean(self):
        widget = self.stackedWidget.currentWidget()
        if widget and hasattr(widget, ServerWidgetBase.setClean.__name__):
            widget.setClean()

    def askToSave(self, question: str):
        return self.showQuestionBox("Servers", question,
                                    buttons=self.BUTTONS.CANCEL | self.BUTTONS.NO | self.BUTTONS.YES,
                                    defaultButton=self.BUTTONS.YES)

    def currentServerChanged(self, new, old):
        new_server = self.getServerFromItem(new)

        if not new_server:
            # Nothing was selected or no matching server was found (should not happen)
            self.showServerWidget()

        if old and self.serverIsDirty():
            # Current server has edits: ask user if we should save them
            answer = self.askToSave("Do you want to save your changes to the current server?")
            if (answer == self.BUTTONS.YES and not self.saveServer()) or answer == self.BUTTONS.CANCEL:
                # User wants to save but saving failed OR user canceled: reset to old server
                self.listServers.setCurrentItem(old)
                return

        self.showServerWidget(new_server)

    def testConnection(self, server):
        """ Tests if the server instance can actually connect to it. """
        if server is None:
            self.showErrorBar("Error", "Wrong value(s) in current server settings")
        else:
            if gui.execute(server.testConnection):
                self.showSuccessBar("Success", "Successfully established server connection")
            else:
                self.showErrorBar("Error", "Could not connect to server")

    def testConnectionPostgis(self):
        server = self.createPostgisServer()
        self._testConnection(server)

    def saveServer(self) -> bool:
        widget = self.stackedWidget.currentWidget()
        if not widget or not hasattr(widget, ServerWidgetBase.createServerInstance.__name__):
            # No (valid) current server widget
            return True
        server = widget.createServerInstance()
        if not server:
            self.showErrorBar("Error", "Wrong values in current server settings")
            return False
        return manager.addServer(server)

    def getServerFromItem(self, item):
        if not item:
            return
        list_widget = self.listServers.itemWidget(item)
        return manager.getServer(list_widget.serverName)

    # def createGeoserverServer(self):
    #     # TODO check validity of name and values
    #     name = self.txtGeoserverName.text().strip()
    #     url = self.txtGeoserverUrl.text().strip()
    #     authid = self.geoserverAuth.configId()
    #     if not bool(authid):
    #         return None
    #     storage = self.comboGeoserverDataStorage.currentIndex()
    #     postgisdb = None
    #     if storage in [GeoserverServer.POSTGIS_BRIDGE, GeoserverServer.POSTGIS_GEOSERVER]:
    #         postgisdb = self.comboGeoserverDatabase.currentText()
    #     use_original_data_source = self.chkUseOriginalDataSource.isChecked()
    #     use_vector_tiles = self.chkUseVectorTiles.isChecked()
    #
    #     if "" in [name, url]:
    #         return None
    #     server = GeoserverServer(
    #         name, url, authid, storage, postgisdb, use_original_data_source,
    #         use_vector_tiles
    #     )
    #     return server

    # def createPostgisServer(self):
    #     # TODO check validity of name and values
    #     name = self.txtPostgisName.text()
    #     host = self.txtPostgisServerAddress.text()
    #     port = self.txtPostgisPort.text()
    #     schema = self.txtPostgisSchema.text()
    #     database = self.txtPostgisDatabase.text()
    #     authid = self.postgisAuth.configId()
    #     server = PostgisServer(name, authid, host, port, schema, database)
    #     return server
    #
    # def createGeonetworkServer(self):
    #     # TODO check validity of name and values
    #     name = self.txtCswName.text()
    #     node = self.txtCswNode.text()
    #     authid = self.cswAuth.configId()
    #     if bool(authid):
    #         url = self.txtCswUrl.text()
    #         profile = self.comboMetadataProfile.currentIndex()
    #         server = GeonetworkServer(name, url, authid, profile, node)
    #         return server

    # def createMapserverServer(self):
    #     # TODO check validity of name and values
    #     name = self.txtMapserverName.text()
    #     authid = self.mapserverAuth.configId()
    #     host = self.txtMapserverHost.text()
    #     try:
    #         port = int(self.txtMapserverPort.text())
    #     except Exception as e:
    #         self.logWarning(e)
    #         return None
    #     local = self.radioLocalPath.isChecked()
    #     if local:
    #         folder = self.fileMapserver.filePath()
    #     else:
    #         folder = self.txtRemoteFolder.text()
    #     url = self.txtMapserverUrl.text()
    #     services_path = self.txtMapServicesPath.text()
    #     proj_folder = self.txtProjFolder.text()
    #     server = MapserverServer(name, url, local, folder, authid, host, port, services_path, proj_folder)
    #     return server

    def addAuthWidgets(self):
        layout = QHBoxLayout()
        layout.setMargin(0)
        layout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(layout)
        self.postgisAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())

    def addMenuToButtonNew(self):
        menu = QMenu()
        for s in manager.getServerTypes():
            menu.addAction(s.getServerTypeLabel(), lambda: self.addNewServer(s))
        # menu.addAction("GeoServer", lambda: self.addNewServer("GeoServer", GeoserverServer))
        # menu.addAction("MapServer", lambda: self.addNewServer("MapServer", MapserverServer))
        # menu.addAction("GeoNetwork", lambda: self.addNewServer("GeoNetwork", GeonetworkServer))
        # menu.addAction("PostGIS", lambda: self.addNewServer("PostGIS", PostgisServer))
        self.buttonNew.setMenu(menu)

    def buttonRemoveClicked(self):
        item = self.listServers.currentItem()
        if item is None:
            return
        name = self.listServers.itemWidget(item).serverName
        manager.removeServer(name)
        self.listServers.takeItem(self.listServers.currentRow())
        self.listServers.setCurrentItem(None)
        self.toggleServerList()

    def populateServerList(self):
        self.listServers.clear()
        for server in manager.getServers():
            self.addServerListItem(server.__class__, server.serverName)
        self.toggleServerList()

    def addServerListItem(self, server_class, server_name: str, set_active: bool = False):
        widget = ServerItemWidget(server_class, server_name)
        item = QListWidgetItem(self.listServers)
        item.setSizeHint(widget.sizeHint())
        self.listServers.blockSignals(True)
        self.listServers.addItem(item)
        self.listServers.setItemWidget(item, widget)
        if set_active:
            self.listServers.setCurrentItem(item)
        self.listServers.blockSignals(False)

    def addNewServer(self, cls):
        if self.serverIsDirty():
            # Current server has edits: ask user if we should save them
            answer = self.askToSave("Do you want to save your changes to the current server?")
            if (answer == self.BUTTONS.YES and not self.saveServer()) or answer == self.BUTTONS.CANCEL:
                # User wants to save but saving failed OR user canceled: do not add new server
                return

        assigned_name = self.showServerWidget(cls)
        if assigned_name:
            self.addServerListItem(cls, assigned_name, True)
            self.toggleServerList()
        else:
            self.showErrorBar("Error", f"Failed to add {cls.getServerTypeLabel()} server. Please check logs.")

    def showServerWidget(self, server=None) -> Union[str, None]:
        """ Sets the current server configuration widget.
        If `server` is a class, a new server of that class will be added with a generated name.

        :param server:  An existing server instance or a server class (for new servers).
                        If this argument is omitted, an empty widget will be shown.
        :returns:       The currently shown server name or None (if unsuccessful).
        """

        if server is None:
            # If there's no current server, show empty widget
            self.stackedWidget.setCurrentWidget(self.widgetEmpty)
            return

        server_cls = server.__class__
        if server_cls is type:
            # Server is not an instance but a model/class: we're dealing with a new server
            server_cls = server

        # Retrieve widget class from server
        cls = server.getWidgetClass()
        if not issubclass(cls, ServerWidgetBase):
            # All server widgets must implement the ServerWidgetBase class
            self.logError(f"Server widget {cls.__name__} does not implement {ServerWidgetBase.__name__}")
            return

        # Lookup existing widget instance
        widget = self._server_widgets.get(cls.__name__, None)

        # If the widget does not exist yet, instantiate and add it to the stackedWidget
        if not widget:
            widget = cls(self, server_cls)
            self._server_widgets[cls.__name__] = widget
            self.stackedWidget.addWidget(widget)

        # Set as current widget and populate its form fields
        self.stackedWidget.setCurrentWidget(widget)
        if server_cls == server:
            srv_name = manager.generateName(server_cls)
            widget.newFromName(srv_name)
        else:
            srv_name = server.serverName
            widget.loadFromInstance(server)

        return srv_name

        # elif isinstance(server, GeoserverServer):
        #     self.stackedWidget.setCurrentWidget(self.widgetGeoserver)

        # elif isinstance(server, MapserverServer):
        #     self.stackedWidget.setCurrentWidget(self.widgetMapserver)
        #     self.txtMapserverName.setText(server.serverName)
        #     self.fileMapserver.setFilePath(server.folder)
        #     self.txtRemoteFolder.setText(server.folder)
        #     self.txtMapserverHost.setText(server.host)
        #     self.txtMapserverPort.setText(str(server.port))
        #     self.mapserverAuth.setConfigId(server.authid)
        #     self.txtMapserverUrl.setText(server.url)
        #     self.txtMapServicesPath.setText(server.servicesPath)
        #     self.txtProjFolder.setText(server.projFolder)
        #     self.radioLocalPath.setChecked(server.useLocalFolder)
        #     self.radioFtp.setChecked(not server.useLocalFolder)
        #     self.mapserverStorageChanged(server.useLocalFolder)
        # elif isinstance(server, PostgisServer):
        #     self.stackedWidget.setCurrentWidget(self.widgetPostgis)
        #     self.txtPostgisName.setText(server.serverName)
        #     self.txtPostgisDatabase.setText(server.database)
        #     self.txtPostgisPort.setText(server.port)
        #     self.txtPostgisServerAddress.setText(server.host)
        #     self.txtPostgisSchema.setText(server.schema)
        #     self.postgisAuth.setConfigId(server.authid)

        # self.setDirty()

    def saveButtonClicked(self):
        if not self.saveServer():
            return
        self.serverSetClean()

    def canClose(self):
        if self.serverIsDirty():
            res = self.askToSave("Do you want to close without saving the current server?")
            return res == self.BUTTONS.YES
        return True


class ServerItemWidget(QWidget):
    def __init__(self, server_class, server_name, parent=None):
        super(ServerItemWidget, self).__init__(parent)
        icon = server_class.getWidgetClass().getPngIcon()
        self.layout = QHBoxLayout()
        self.label = QLabel()
        self.serverName = server_name
        self.iconLabel = QLabel()
        self.iconLabel.setPixmap(icon)
        self.iconLabel.setFixedWidth(50)
        self.layout.addWidget(self.iconLabel)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

    @property
    def serverName(self):
        return self.label.text()

    @serverName.setter
    def serverName(self, name):
        self.label.setText(name)
