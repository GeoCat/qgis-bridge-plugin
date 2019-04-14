import os
from qgis.PyQt import uic
 
WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'geocatbridgedialog.ui'))

class GeocatbridgeDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeocatbridgeDialog, self).__init__(parent)
        self.setupUi(self)

