from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt import uic

from geocatbridge.utils import files


def loadUiType(controller):
    """ Returns a tuple of (widget, base) from a given controller (Python module path). """
    ui_name = files.Path(controller).stem
    ui_file = files.getUiPath(ui_name)
    return uic.loadUiType(ui_file)


def execute(func):
    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
    try:
        return func()
    finally:
        QApplication.restoreOverrideCursor()
        QCoreApplication.processEvents()
