from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.gui import QgsAuthConfigSelect

from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class PostgisWidget(ServerWidgetBase, BASE, WIDGET):

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)
        self.setupUi(self)

        self.postgisAuth = QgsAuthConfigSelect()
        self.postgisAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.btnConnectPostgis.clicked.connect(self.testConnection)
        self.txtPostgisName.textChanged.connect(self.setDirty)
        self.txtPostgisServerAddress.textChanged.connect(self.setDirty)
        self.txtPostgisPort.textChanged.connect(self.setDirty)
        self.txtPostgisSchema.textChanged.connect(self.setDirty)
        self.txtPostgisDatabase.textChanged.connect(self.setDirty)

    def getName(self):
        return self.txtPostgisName.text().strip()

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        try:
            port = int(self.txtPostgisPort.text())
        except (ValueError, TypeError):
            self.parent.logError('Invalid PostGIS port specified')
            return None

        try:
            return self.serverType(
                name=self.getName(),
                authid=self.postgisAuth.configId(),
                host=self.txtPostgisServerAddress.text().strip(),
                port=port,
                schema=self.txtPostgisSchema.text().strip(),
                database=self.txtPostgisDatabase.text().strip()
            )
        except Exception as e:
            self.parent.logError(f"Failed to create server instance:\n{e}")
            return None

    def newFromName(self, name: str):
        """ Sets the name field and keeps all others empty. """
        self.txtPostgisName.setText(name)
        self.txtPostgisDatabase.clear()
        self.txtPostgisPort.clear()
        self.txtPostgisServerAddress.clear()
        self.txtPostgisSchema.clear()
        self.postgisAuth.setConfigId(None)

    def loadFromInstance(self, server):
        """ Populates the form fields with the values from the given server instance. """
        self.txtPostgisName.setText(server.serverName)
        self.txtPostgisDatabase.setText(server.database)
        self.txtPostgisPort.setText(server.port)
        self.txtPostgisServerAddress.setText(server.host)
        self.txtPostgisSchema.setText(server.schema)
        self.postgisAuth.setConfigId(server.authid)

        # After the data has loaded, the form is "clean"
        self.setClean()

    def addAuthWidget(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)
        layout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(layout)
        self.postgisAuthWidget.setFixedHeight(self.txtPostgisServerAddress.height())

    def testConnection(self):
        server = self.createServerInstance()
        self.parent.testConnection(server)
