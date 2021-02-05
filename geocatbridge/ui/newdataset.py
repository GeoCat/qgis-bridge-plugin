from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class NewDatasetDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(NewDatasetDialog, self).__init__(parent)
        self.setupUi(self)
        self.name = None
        self.host = None
        self.port = None
        self.schema = None
        self.database = None
        self.username = None
        self.password = None

    def accept(self):
        self.name = self.txtName.text()
        self.host = self.txtHost.text()
        self.port = self.txtPort.text()
        self.schema = self.txtSchema.text()
        self.database = self.txtDatabase.text()
        self.username = self.txtUsername.text()
        self.password = self.txtPassword.text()
        self.close()
