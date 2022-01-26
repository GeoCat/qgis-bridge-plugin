from typing import Iterable

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


def execute(func, *args, **kwargs):
    """ Blocks GUI thread (and sets a wait cursor) while `func` is being executed. """
    QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
    try:
        return func(*args, **kwargs)
    finally:
        QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()  # noqa


class ItemProcessor(QtCore.QThread):
    """ This class can be used to process a list of items using a given function.

    The processing is done on a separate (non-blocking) thread and emits signals,
    which can be connected to a progress indicator for example.
    The processor can be aborted by calling requestInterruption().

    :param items:       Iterable of items to process.
    :param processor:   The processor function to call on each item. This function must accept one argument.
    :returns:           The resultReady signal slot receives a list of results for each processed item.
    """
    progress = QtCore.pyqtSignal(int)
    resultReady = QtCore.pyqtSignal(list)

    def __init__(self, items: Iterable, processor):
        super().__init__()
        self._items = items
        self._func = processor

    def run(self):
        results = []
        total_steps = 0
        QApplication.processEvents()
        for step, item in enumerate(self._items):
            total_steps += 1
            self.progress.emit(step)  # noqa
            try:
                results.append(self._func(item))
            except Exception as e:
                # Log a QGIS error message (should be thread-safe)
                logError(e)
            if self.isInterruptionRequested():
                break
        if not self.isInterruptionRequested():
            # Emit 100% progress and wait briefly so that user sees it
            self.progress.emit(total_steps)  # noqa
            self.msleep(500)
        self.resultReady.emit(results)  # noqa
        self.finished.emit()  # noqa
