from functools import partial
from typing import Iterable, Any, Callable
from inspect import isgenerator
from pathlib import Path

from qgis.PyQt import QtCore
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QCursor, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QApplication, QWidget
from qgis.gui import QgsAuthConfigSelect

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


def execute(func, *args, **kwargs) -> Any:
    """ Sets a wait cursor while `func` is being executed. Runs on GUI thread if called from a UI view model. """
    QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
    try:
        return func(*args, **kwargs)
    finally:
        QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()


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


def getBasicAuthSelectWidget(parent: QWidget) -> QgsAuthConfigSelect:
    """ Returns a QgsAuthConfigSelect widget for selecting a basic authentication configuration only. """
    # Use "proxy", "gdal", "ogr", or "oracle" data provider argument to filter for Basic Auth only.
    # It doesn't matter which provider is set, as long as it's not used for other auth methods.
    # See https://tinyurl.com/4nw7x87f for details.
    return QgsAuthConfigSelect(parent, "proxy")


class BackgroundWorker(QtCore.QObject):
    """ This class can be used to process multiple items using a function on a separate thread."""
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal()
    results = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def _run(self, func: Callable, items: Iterable):
        results_ = []
        try:
            if isgenerator(items):
                # Flatten generators into a tuple
                items = tuple(items)
            for step, item in enumerate(items):
                self.progress.emit(step)
                try:
                    results_.append(func(item))
                except Exception as e:
                    # Log a QGIS error message (should be thread-safe)
                    logError(e)
                    results_.append(e)
                if self.thread().isInterruptionRequested():
                    break
        finally:
            self.results.emit(results_)
            self.finished.emit()

    def start(self):
        """ Shortcut method to start the thread, which will also start the worker (if setup() was called first). """
        thread = self.thread()
        if not thread:
            name = self.__class__.__name__
            raise RuntimeError(f"{name} is not assigned to a thread. Call setup() first.")
        if not thread.isRunning():
            thread.start()

    @staticmethod
    def setup(fn: Callable, items: Iterable) -> tuple['BackgroundWorker', QtCore.QThread]:
        """ Convenience method to schedule a function on a separate thread using a `BackgroundWorker` object.

        This method instantiates the thread and worker and connects the signals and slots required to run the function
        on the background thread and clean up afterward.
        Call the `start()` method on the worker or the thread (makes no difference).
        You may want to connect additional signals and slots to the worker before starting the thread.

        :param fn:      The function to run on a separate thread.
                        The function should at least accept 1 item argument that needs to be processed.
                        If the function has multiple arguments, use `functools.partial` to bind them,
                        and make sure that the last (!) argument is the item that needs processing.
                        If
        :param items:   An iterable of items to process.
        :returns:       A tuple of (BackgroundWorker, QThread) objects for reference.
        """

        # Set up the background thread assign the worker to it
        thread = QtCore.QThread()
        worker = BackgroundWorker()
        worker.moveToThread(thread)

        # Connect signals and slots
        thread.started.connect(partial(worker._run, fn, items))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        return worker, thread
