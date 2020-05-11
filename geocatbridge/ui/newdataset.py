import os

from qgis.PyQt import uic


def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)


WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), "newdataset.ui"))


class NewDatasetDialog(BASE, WIDGET):
    def __init__(self, parent=None):
        super(NewDatasetDialog, self).__init__(parent)
        self.setupUi(self)
        self.name = None

    def accept(self):
        self.name = self.txtName.text()
        self.host = self.txtHost.text()
        self.port = self.txtPort.text()
        self.schema = self.txtSchema.text()
        self.database = self.txtDatabase.text()
        self.username = self.txtUsername.text()
        self.password = self.txtPassword.text()
        print("acc")
        self.close()
