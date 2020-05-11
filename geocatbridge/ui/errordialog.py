import os

from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIcon, QPixmap

from geocatbridge.publish import mygeocat

rootFolder = os.path.dirname(os.path.dirname(__file__))


def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)


WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), "errordialog.ui"))


class ErrorDialog(BASE, WIDGET):
    def __init__(self, error, parent=None):
        super(ErrorDialog, self).__init__(parent)
        self.setupUi(self)

        pixmap = QPixmap(iconPath("geocatlogo.png"))
        self.labelIcon.setPixmap(pixmap)

        self.txtError.setHtml(error)
        self.btnClose.clicked.connect(self.close)

        self.btnSendReport.setEnabled(mygeocat.client.isLoggedIn())
