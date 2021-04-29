from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class GeoserverDatastoreDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeoserverDatastoreDialog, self).__init__(parent)
        self.setupUi(self)
        self.name = None
        self.host = None
        self.port = None
        self.schema = None
        self.database = None
        self.username = None
        self.password = None

    def accept(self):
        self.name = self.txtName.text().strip()
        self.host = self.txtHost.text().strip()
        self.port = self.txtPort.text().strip()
        self.schema = self.txtSchema.text().strip()
        self.database = self.txtDatabase.text().strip()
        self.username = self.txtUsername.text().strip()
        self.password = self.txtPassword.text().strip()
        self.close()
