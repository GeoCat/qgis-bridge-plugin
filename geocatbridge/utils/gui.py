from qgis.PyQt import QtCore
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication

from geocatbridge.utils import files
from geocatbridge.utils.feedback import logError


def loadUiType(controller) -> tuple:
    """ Returns a tuple of (widget, base) from a given controller (Python module path).
    The Qt view file (*.ui) should have the same name as the controller
    and needs to exist in the same folder.

    :param controller:  Controller module file path.
    :returns:           A tuple of (widget, base) derived from the UI file.
    """
    ui_file = files.getViewPath(controller)
    return uic.loadUiType(ui_file)


def execute(func):
    """ Blocks GUI thread (and sets a wait cursor) while `func` is being executed. """
    QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
    try:
        return func()
    finally:
        QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()


class ItemProcessor(QtCore.QThread):
    """ This class can be used to process a list of items using a given function.

    The processing is done on a separate (non-blocking) thread and emits signals,
    which can be connected to a progress indicator for example.
    """
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(list)

    def __init__(self, items: list, func):
        super().__init__()
        self._items = items
        self._func = func
        self._stop = False

    def run(self):
        results = []
        for count, item in enumerate(self._items, 1):
            try:
                results.append(self._func(item))
            except Exception as e:
                # Log a QGIS error message (should be thread-safe)
                logError(e)
            self.progress.emit(count)
            if self._stop:
                break
        self.finished.emit(results)

    def stop(self):
        self._stop = True
