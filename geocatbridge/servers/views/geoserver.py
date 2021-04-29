from itertools import chain
from functools import partial

from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QProgressDialog
)
from qgis.PyQt import QtCore
from qgis.gui import QgsAuthConfigSelect

from geocatbridge.servers.models.gs_storage import GeoserverStorage
from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.servers.views.geoserver_ds import GeoserverDatastoreDialog
from geocatbridge.utils import gui
from geocatbridge.utils.meta import getAppName

WIDGET, BASE = gui.loadUiType(__file__)


class GeoServerWidget(ServerWidgetBase, BASE, WIDGET):

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)
        self.setupUi(self)

        self.geoserverAuth = QgsAuthConfigSelect()
        self.geoserverAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.populateStorageCombo()
        self.comboStorageType.currentIndexChanged.connect(self.datastoreChanged)
        self.btnConnectGeoserver.clicked.connect(self.testConnection)
        self.btnRefreshDatabases.clicked.connect(partial(self.updateDbServersCombo, True))
        self.btnAddDatastore.clicked.connect(self.addPostgisDatastore)
        self.txtGeoserverName.textChanged.connect(self.setDirty)
        self.txtGeoserverUrl.textChanged.connect(self.setDirty)
        self.chkUseOriginalDataSource.stateChanged.connect(self.setDirty)
        self.chkUseVectorTiles.stateChanged.connect(self.setDirty)
        self.comboGeoserverDatabase.currentIndexChanged.connect(self.setDirty)

        # Declare progress dialog
        self._pgdialog = None

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        db = None
        storage = self.comboStorageType.currentIndex()
        if storage in (GeoserverStorage.POSTGIS_BRIDGE, GeoserverStorage.POSTGIS_GEOSERVER):
            db = self.comboGeoserverDatabase.currentText()

        try:
            return self.serverType(
                name=self.txtGeoserverName.text().strip(),
                authid=self.geoserverAuth.configId() or None,
                url=self.txtGeoserverUrl.text().strip(),
                storage=storage,
                postgisdb=db,
                useOriginalDataSource=self.chkUseOriginalDataSource.isChecked(),
                useVectorTiles=self.chkUseVectorTiles.isChecked()
            )
        except Exception as e:
            self.parent.logError(f"Failed to create server instance:\n{e}")
            return None

    def newFromName(self, name: str):
        """ Sets the name field and keeps all others empty. """
        self.txtGeoserverName.setText(name)
        self.txtGeoserverUrl.clear()
        self.geoserverAuth.setConfigId(None)

        # Set datastore and database comboboxes
        self.comboStorageType.blockSignals(True)
        self.comboStorageType.setCurrentIndex(GeoserverStorage.FILE_BASED)
        self.datastoreChanged(GeoserverStorage.FILE_BASED)
        self.chkUseOriginalDataSource.setChecked(False)
        self.chkUseVectorTiles.setChecked(False)
        self.comboStorageType.blockSignals(False)

    def loadFromInstance(self, server):
        """ Populates the form fields with the values from the given server instance. """
        self.txtGeoserverName.setText(server.serverName)
        self.txtGeoserverUrl.setText(server.baseUrl)
        self.geoserverAuth.setConfigId(server.authId)

        # Set datastore and database comboboxes
        self.comboStorageType.blockSignals(True)
        self.comboStorageType.setCurrentIndex(server.storage)
        self.datastoreChanged(server.storage, server.postgisdb)
        self.chkUseOriginalDataSource.setChecked(server.useOriginalDataSource)
        self.chkUseVectorTiles.setChecked(server.useVectorTiles)
        self.comboStorageType.blockSignals(False)

        # After the data has loaded, the form is "clean"
        self.setClean()

    def addAuthWidget(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)
        layout.addWidget(self.geoserverAuth)
        self.geoserverAuthWidget.setLayout(layout)
        self.geoserverAuthWidget.setFixedHeight(self.txtGeoserverUrl.height())

    def testConnection(self):
        server = self.createServerInstance()
        self.parent.testConnection(server)

    def populateStorageCombo(self):
        self.comboStorageType.clear()
        self.comboStorageType.addItems(GeoserverStorage.values())

    def datastoreChanged(self, storage, init_value=None):
        """ Called each time the database combobox selection changed. """
        if storage is None:
            storage = GeoserverStorage[self.comboStorageType.currentIndex()]
        if storage == GeoserverStorage.POSTGIS_BRIDGE:
            self.updateDbServersCombo(False, init_value)
            self.comboGeoserverDatabase.setVisible(True)
            self.labelGeoserverDatastore.setText('Database')
            self.labelGeoserverDatastore.setVisible(True)
            self.datastoreControls.setVisible(False)
        elif storage == GeoserverStorage.POSTGIS_GEOSERVER:
            self.comboGeoserverDatabase.setVisible(True)
            self.labelGeoserverDatastore.setText('Datastore')
            self.labelGeoserverDatastore.setVisible(True)
            self.datastoreControls.setVisible(True)
            self.updateDbServersCombo(True, init_value)
        elif storage == GeoserverStorage.FILE_BASED:
            self.comboGeoserverDatabase.setVisible(False)
            self.labelGeoserverDatastore.setVisible(False)
            self.datastoreControls.setVisible(False)
        self.setDirty()

    def addGeoserverPgDatastores(self, current, result):
        if self._pgdialog and self._pgdialog.isVisible():
            self._pgdialog.hide()
        if result:
            # Worker result might be a list of lists, so we should flatten it
            datastores = list(chain.from_iterable(result))
            self.comboGeoserverDatabase.addItems(datastores)
            if current:
                self.comboGeoserverDatabase.setCurrentText(current)
        else:
            self.parent.showWarningBar("Warning", "No PostGIS datastores on server or could not retrieve them")

    def showProgressDialog(self, text, length, handler):
        self._pgdialog = QProgressDialog(text, "Cancel", 0, length, self)
        self._pgdialog.setWindowTitle(getAppName())
        self._pgdialog.setWindowModality(QtCore.Qt.WindowModal)
        self._pgdialog.canceled.connect(handler, type=QtCore.Qt.DirectConnection)
        self._pgdialog.forceShow()

    def updateDbServersCombo(self, managed_by_geoserver: bool, init_value=None):
        """ (Re)populate the combobox with database-driven datastores.

        :param managed_by_geoserver:    If True, GeoServer manages the DB connection. If False, Bridge manages it.
        :param init_value:              When the combobox shows for the first time and no databases have been loaded,
                                        this value can be set immediately as the only available and selected item.
                                        Doing so prevents a full refresh of GeoServer datastores.
        """
        if managed_by_geoserver and init_value:
            if self.comboGeoserverDatabase.count() == 0:
                # Only add the given init_value item to the empty combo (user should manually refresh)
                self.comboGeoserverDatabase.addItem(init_value)
                self.comboGeoserverDatabase.setCurrentText(init_value)
                return
            # If combo has values, try and find the init_value and set it to that (user should manually refresh)
            index = self.comboGeoserverDatabase.findText(init_value)
            if index >= 0:
                self.comboGeoserverDatabase.setCurrentIndex(index)
                return

        current_db = self.comboGeoserverDatabase.currentText() or init_value
        self.comboGeoserverDatabase.clear()

        if managed_by_geoserver:
            # Database is managed by GeoServer: instantiate server and retrieve datastores
            # TODO: only PostGIS datastores are supported for now
            server = self.createServerInstance()
            if not server:
                self.parent.showErrorBar("Error", "Bad values in server definition")
                return

            try:
                # Retrieve workspaces (single REST request)
                workspaces = gui.execute(server.getWorkspaces)
                if not workspaces:
                    return
                # Retrieve datastores for each workspace:
                # This is a potentially long-running operation and uses a separate QThread
                worker = gui.ItemProcessor(workspaces, server.getPostgisDatastores)
                self.showProgressDialog("Fetching PostGIS datastores...", len(workspaces), worker.stop)
                worker.progress.connect(self._pgdialog.setValue)
                worker.finished.connect(partial(self.addGeoserverPgDatastores, current_db))
                worker.run()
            except Exception as e:
                self.parent.logError(f"Failed to retrieve datastores:\n{e}")

        else:
            # Database is managed by Bridge: iterate over all user-defined database connections
            db_servers = self.parent.serverManager.getDbServerNames()
            self.comboGeoserverDatabase.addItems(db_servers)
            if current_db in db_servers:
                self.comboGeoserverDatabase.setCurrentText(current_db)

    def addPostgisDatastore(self):
        server = self.createServerInstance()
        if server is None:
            self.parent.showErrorBar("Error", "Wrong values in server definition")
            return
        dlg = GeoserverDatastoreDialog(self)
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
            gui.execute(partial(server.addPostgisDatastore, ds))
        except Exception as e:
            self.parent.showErrorBar("Error", "Could not create new PostGIS dataset", propagate=e)
        else:
            self.updateDbServersCombo(True)
