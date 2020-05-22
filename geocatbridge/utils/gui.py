from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtCore import Qt, QCoreApplication

def execute(func):
    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
    try:
        return func()
    finally:
        QApplication.restoreOverrideCursor()
        QCoreApplication.processEvents()