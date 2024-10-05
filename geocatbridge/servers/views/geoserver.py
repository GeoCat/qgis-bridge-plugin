import time
from functools import partial
from itertools import chain
from requests import HTTPError
from typing import Optional

from qgis.PyQt.QtWidgets import QHBoxLayout, QProgressDialog

from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.servers.models.gs_storage import GeoserverStorage
from geocatbridge.servers.views.geoserver_ds import GeoserverDatastoreDialog
from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class GeoServerWidget(ServerWidgetBase, BASE, WIDGET):
    dsThread: Optional[gui.QtCore.QThread]
    dsWorker: Optional[gui.BackgroundWorker]

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)

        self.dsThread = None
        self.dsWorker = None
        self.setupUi(self)

        self.geoserverAuth = gui.getBasicAuthSelectWidget(self)
        self.geoserverAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.populateStorageCombo()
        self.comboStorageType.currentIndexChanged.connect(self.datastoreChanged)
        self.btnRefreshDatabases.setToolTip(self.tr("Refresh datastores"))
        self.btnRefreshDatabases.setIcon(gui.getSvgIcon("refresh"))
        self.btnRefreshDatabases.clicked.connect(partial(self.updateDbServersCombo, True))
        self.btnAddDatastore.setIcon(gui.getSvgIcon("add"))
        self.btnAddDatastore.setToolTip(self.tr("Add new PostGIS datastore"))
        self.btnAddDatastore.clicked.connect(self.addPostgisDatastore)
        self.txtGeoserverName.textChanged.connect(self.setDirty)
        self.txtGeoserverUrl.textChanged.connect(self.setDirty)
        self.chkUseOriginalDataSource.stateChanged.connect(self.setDirty)
        self.chkUseVectorTiles.stateChanged.connect(self.setDirty)
        self.comboGeoserverDatabase.currentIndexChanged.connect(self.setDirty)

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        db = None
        storage = self.comboStorageType.currentIndex()
        if storage in (GeoserverStorage.POSTGIS_BRIDGE, GeoserverStorage.POSTGIS_GEOSERVER):
            db = self.comboGeoserverDatabase.currentText()

        try:
            name = self.txtGeoserverName.text().strip()
            url = self.txtGeoserverUrl.text().strip()
            if not name:
                raise RuntimeError(f'missing {self.serverType.getLabel()} name')
            if not url:
                raise RuntimeError(f'missing {self.serverType.getLabel()} URL')

            return self.serverType(
                name=name,
                authid=self.geoserverAuth.configId() or None,
                url=url,
                storage=storage,
                postgisdb=db,
                useOriginalDataSource=self.chkUseOriginalDataSource.isChecked(),
                useVectorTiles=self.chkUseVectorTiles.isChecked()
            )
        except Exception as e:
            self.parent.logError(f"Failed to create {self.serverType.getLabel()} instance: {e}")
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

    def populateStorageCombo(self):
        self.comboStorageType.clear()
        self.comboStorageType.addItems(GeoserverStorage.values())

    def datastoreChanged(self, storage, init_value=None):
        """ Called each time the database combobox selection changed. """
        if storage is None:
            storage = GeoserverStorage[self.comboStorageType.currentIndex()]

        self.setGeoserverDatastoreText(storage)
        if storage == GeoserverStorage.POSTGIS_BRIDGE:
            self.updateDbServersCombo(False, init_value)
        elif storage == GeoserverStorage.POSTGIS_GEOSERVER:
            self.updateDbServersCombo(True, init_value)

        self.setDirty()

    def setGeoserverDatastoreText(self, storage_type: GeoserverStorage):
        self.toggleDatastoreControls(False)
        self.labelGeoserverDatastore.setText('Database')
        self.labelGeoserverDatastore.setWhatsThis(None)
        self.labelGeoserverDatastore.setEnabled(False)
        self.comboGeoserverDatabase.setEnabled(False)

        if storage_type == GeoserverStorage.POSTGIS_BRIDGE:
            whats_this = """
                         <html>
                            <head/>
                            <body>
                                <p>Select the PostGIS connection to use when publishing vector layers to GeoServer.</p>
                                <p>Bridge will use this connection to import the layer data into PostGIS, 
                                and GeoServer will use it to read the layer data.</p>
                            </body>
                         </html>
                         """
            self.comboGeoserverDatabase.setEnabled(True)
            self.labelGeoserverDatastore.setEnabled(True)
            self.labelGeoserverDatastore.setWhatsThis(whats_this)
        elif storage_type == GeoserverStorage.POSTGIS_GEOSERVER:
            whats_this = """
                         <html>
                            <head/>
                            <body>
                                <p>Select an existing PostGIS datastore to use as a template 
                                when publishing vector layers, or add a new one.</p>
                                <p>Bridge will export the layer data to GeoServer and create a new datastore based 
                                on the one that you selected. 
                                Then, Bridge will instruct GeoServer to import the data into the PostGIS datastore.</p>
                            </body>
                         </html>
                         """
            self.toggleDatastoreControls(True)
            self.comboGeoserverDatabase.setEnabled(True)
            self.labelGeoserverDatastore.setEnabled(True)
            self.labelGeoserverDatastore.setText('Datastore')
            self.labelGeoserverDatastore.setWhatsThis(whats_this)

    def toggleDatastoreControls(self, enabled: bool):
        self.btnRefreshDatabases.setEnabled(enabled)
        self.btnAddDatastore.setEnabled(enabled)

    def updateDbServersCombo(self, managed_by_geoserver: bool, init_value=None):
        """ (Re)populate the combobox with database-driven datastores.

        :param managed_by_geoserver:    If True, GeoServer manages the DB connection. If False, Bridge manages it.
        :param init_value:              When the combobox shows for the first time and no databases have been loaded,
                                        this value can be set immediately as the only available and selected item.
                                        Doing so prevents a full refresh of GeoServer datastores.
        """
        def _addGeoserverPgDatastores(current_db_: str, worker_result):
            if worker_result:
                # Worker result might be a list of lists, so we should flatten it
                datastores = list(chain.from_iterable(worker_result))
                self.comboGeoserverDatabase.addItems(datastores)
                if current_db_:
                    self.comboGeoserverDatabase.setCurrentText(current_db_)
            else:
                self.parent.showWarningBar("Warning", "No PostGIS datastores on server or failed to retrieve any")

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
                self.dsWorker, self.dsThread = gui.BackgroundWorker.setup(server.getPostgisDatastores, workspaces)
                pg_dialog = self.parent.getProgressDialog("Retrieving PostGIS datastores...",
                                                          len(workspaces), self.dsThread.requestInterruption)
                self.dsWorker.progress.connect(pg_dialog.setValue)
                self.dsWorker.finished.connect(pg_dialog.close)
                self.dsWorker.results.connect(partial(_addGeoserverPgDatastores, current_db))
                self.dsWorker.start()
            except Exception as e:
                msg = f'Failed to retrieve datastores for {getattr(server, "serverName", self.txtGeoserverName.text())}'
                if isinstance(e, HTTPError) and e.response.status_code == 401:
                    msg = f'{msg}: please check credentials'
                else:
                    msg = f'{msg}: {e}'
                self.parent.showErrorBar("Error", msg)

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
