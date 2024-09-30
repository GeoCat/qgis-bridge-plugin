from qgis.PyQt.QtWidgets import QHBoxLayout

from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class PostgisWidget(ServerWidgetBase, BASE, WIDGET):

    DEFAULT_PORT = 5432

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)
        self.setupUi(self)

        self.postgisAuth = gui.getBasicAuthSelectWidget(self)
        self.postgisAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.txtPostgisName.textChanged.connect(self.setDirty)
        self.txtPostgisServerAddress.textChanged.connect(self.setDirty)
        self.txtPostgisPort.textChanged.connect(self.setDirty)
        self.txtPostgisSchema.textChanged.connect(self.setDirty)
        self.txtPostgisDatabase.textChanged.connect(self.setDirty)

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        try:
            name = self.txtPostgisName.text().strip()
            host = self.txtPostgisServerAddress.text().strip()
            if not name:
                raise RuntimeError(f'missing {self.serverType.getLabel()} name')
            if not host:
                raise RuntimeError(f'missing {self.serverType.getLabel()} host address')

            try:
                port = int(self.txtPostgisPort.text().strip() or self.DEFAULT_PORT)
            except ValueError:
                self.parent.logError(f'invalid {self.serverType.getLabel()} port: defaulting to {self.DEFAULT_PORT}')
                port = self.DEFAULT_PORT

            return self.serverType(
                name=name,
                authid=self.postgisAuth.configId(),
                host=host,
                port=port,
                schema=self.txtPostgisSchema.text().strip(),
                database=self.txtPostgisDatabase.text().strip()
            )
        except Exception as e:
            self.parent.logError(f"Failed to create {self.serverType.getLabel()} instance: {e}")
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
        self.txtPostgisPort.setText(str(server.port))
        self.txtPostgisServerAddress.setText(server.host)
        self.txtPostgisSchema.setText(server.schema)
        self.postgisAuth.setConfigId(server.authId)

        # After the data has loaded, the form is "clean"
        self.setClean()

    def addAuthWidget(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)
        layout.addWidget(self.postgisAuth)
        self.postgisAuthWidget.setLayout(layout)
        self.postgisAuthWidget.setFixedHeight(self.txtPostgisServerAddress.height())
