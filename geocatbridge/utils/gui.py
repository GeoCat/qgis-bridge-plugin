from typing import Iterable
from pathlib import Path

from qgis.PyQt import QtCore
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QCursor, QIcon, QPixmap
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


def getSvgIcon(name: str) -> QIcon:
    """ Returns a QIcon object for a given SVG image. File should exist in the ./images folder.

    :param name:    The SVG icon name (without extension).
    :returns:       A QIcon object.
    """
    return QIcon(files.getIconPath(name))


def getPixmap(file_path: Path, width: int, height: int) -> QPixmap:
    """ Returns a QPixmap object for a given image path. File should exist (no checks performed).
    Uses QIcon to open the image and then scales it to the given width and height by calling its pixmap() method.

    :param file_path:   Full path to the image file.
    :param width:       The desired width of the pixmap (pixels).
    :param height:      The desired height of the pixmap (pixels).
    :returns:           A QPixmap object.
    """
    return QIcon(str(file_path)).pixmap(QtCore.QSize(width, height))


def getSvgPixmap(name: str, width: int, height: int) -> QPixmap:
    """ Returns a QPixmap object for a given SVG image. File should exist in the ./images folder.

    :param name:    The SVG image name (without extension).
    :param width:   The desired width of the pixmap (pixels).
    :param height:  The desired height of the pixmap (pixels).
    :returns:       A QPixmap object.
    """
    return getSvgIcon(name).pixmap(QtCore.QSize(width, height))


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
