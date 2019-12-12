import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'bridgedialog.ui'))

class GeoCatWidget(QWidget):

    def __init__(self, parent=None):
        super(GeoCatWidget, self).__init__(parent)
        #self.setupUi(self)
        