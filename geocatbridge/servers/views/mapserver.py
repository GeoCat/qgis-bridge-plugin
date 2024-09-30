from qgis.PyQt.QtWidgets import QHBoxLayout

from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class MapServerWidget(ServerWidgetBase, BASE, WIDGET):

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)
        self.setupUi(self)

        self.mapserverAuth = gui.getBasicAuthSelectWidget(self)
        self.mapserverAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.radioLocalPath.toggled.connect(self.showLocalStorageFields)
        self.fileMapserver.setStorageMode(self.fileMapserver.GetDirectory)

        self.txtMapserverName.textChanged.connect(self.setDirty)
        self.txtMapserverUrl.textChanged.connect(self.setDirty)
        self.txtMapserverHost.textChanged.connect(self.setDirty)
        self.txtMapserverPort.textChanged.connect(self.setDirty)
        self.txtMapserverUrl.textChanged.connect(self.setDirty)
        self.txtMapServicesPath.textChanged.connect(self.setDirty)
        self.txtProjFolder.textChanged.connect(self.setDirty)

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        options = {
            'authid': self.mapserverAuth.configId(),
            'servicesPath': self.txtMapServicesPath.text().strip(),
            'projFolder': self.txtProjFolder.text().strip()
        }

        port = None
        host = None
        local_storage = self.radioLocalPath.isChecked()
        if local_storage:
            folder = self.fileMapserver.filePath()
        else:
            folder = self.txtRemoteFolder.text().strip()
            host = self.txtMapserverHost.text().strip()
            try:
                port = int(self.txtMapserverPort.text())
            except (ValueError, TypeError):
                pass

        try:
            name = self.txtMapserverName.text().strip()
            url = self.txtMapserverUrl.text().strip()
            if not name:
                raise RuntimeError(f'missing {self.serverType.getLabel()} name')
            if not url:
                raise RuntimeError(f'missing {self.serverType.getLabel()} URL')
            if not local_storage:
                if not host:
                    raise RuntimeError(f'missing FTP host address')
                if not port:
                    raise RuntimeError(f'missing or invalid FTP port specified')

            options.update({
                'name': name,
                'url': url,
                'useLocalFolder': local_storage,
                'folder': folder,
                'port': port
            })

            return self.serverType(**{k: v for k, v in options.items() if v})
        except Exception as e:
            self.parent.logError(f"Failed to create {self.serverType.getLabel()} instance: {e}")
            return None

    def newFromName(self, name: str):
        """ Sets the name field and keeps all others empty. """
        self.txtMapserverName.setText(name)
        self.txtMapserverHost.clear()
        self.txtMapserverPort.clear()
        self.mapserverAuth.setConfigId(None)
        self.txtMapserverUrl.clear()
        self.txtMapServicesPath.clear()
        self.txtProjFolder.clear()
        self.radioLocalPath.setChecked(True)
        self.radioFtp.setChecked(False)
        self.showLocalStorageFields(True)

    def loadFromInstance(self, server):
        """ Populates the form fields with the values from the given server instance. """
        self.txtMapserverName.setText(server.serverName)
        self.fileMapserver.setFilePath(server.folder)
        self.txtRemoteFolder.setText(server.folder)
        self.txtMapserverHost.setText(server.host)
        self.txtMapserverPort.setText(str(server.port))
        self.mapserverAuth.setConfigId(server.authId)
        self.txtMapserverUrl.setText(server.baseUrl)
        self.txtMapServicesPath.setText(server.servicesPath)
        self.txtProjFolder.setText(server.projFolder)
        self.radioLocalPath.setChecked(server.useLocalFolder)
        self.radioFtp.setChecked(not server.useLocalFolder)
        self.showLocalStorageFields(server.useLocalFolder)

        # After the data has loaded, the form is "clean"
        self.setClean()

    def addAuthWidget(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)
        layout.addWidget(self.mapserverAuth)
        self.mapserverAuthWidget.setLayout(layout)
        self.mapserverAuthWidget.setFixedHeight(self.txtMapserverUrl.height())

    def showLocalStorageFields(self, checked):
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
        self.setDirty()
