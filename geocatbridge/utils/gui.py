from functools import partial
from typing import Iterable, Any, Callable
from inspect import isgenerator
from pathlib import Path

from qgis.PyQt import QtCore, QtGui, uic
from qgis.PyQt.QtWidgets import QApplication, QWidget
from qgis.gui import QgsAuthConfigSelect

from geocatbridge.utils import files
from geocatbridge.utils.feedback import logError

COLOR_SCHEME = None


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
    QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
    try:
        return func(*args, **kwargs)
    finally:
        QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()


def isDarkMode() -> bool:
    """ Returns True if the application is running in dark mode, or false otherwise. """
    scheme = QApplication.styleHints().colorScheme()
    return scheme == QtCore.Qt.ColorScheme.Dark


def getDarkPath(file_path: str | Path) -> str:
    """ Returns the path to the dark mode version of a given file path, if it exists.
    If no dark mode version is found, returns the original file path.

    :param file_path:   Full path to the image file.
    :returns:           Full path to the dark mode image file (if available), or the original file path.
    """
    file_path = Path(file_path)
    if isDarkMode():
        dark_path = file_path.with_stem(file_path.stem + "_dark")
        if dark_path.exists():
            return str(dark_path)
    return str(file_path)


def getCustomIcon(file_path: Path) -> QtGui.QIcon:
    """ Returns a QIcon object for a given image path. File should exist (no checks performed).

    :param file_path:   Full path to the image file.
    :returns:           A QIcon object.
    """
    return QtGui.QIcon(getDarkPath(file_path.resolve()))


def getSvgIconByName(name: str) -> QtGui.QIcon:
    """ Returns a QIcon object for a given SVG image. File should exist in the ./images folder.

    :param name:    The SVG icon name (without extension).
    :returns:       A QIcon object.
    """
    file_path = files.getIconPath(name)
    return getCustomIcon(Path(file_path))


def getPixmap(file_path: Path, width: int, height: int) -> QtGui.QPixmap:
    """ Returns a QPixmap object for a given image path. File should exist (no checks performed).
    Uses QIcon to open the image and then scales it to the given width and height by calling its pixmap() method.

    :param file_path:   Full path to the image file.
    :param width:       The desired width of the pixmap (pixels).
    :param height:      The desired height of the pixmap (pixels).
    :returns:           A QPixmap object.
    """
    return getCustomIcon(file_path).pixmap(QtCore.QSize(width, height))


def getSvgPixmap(name: str, width: int, height: int) -> QtGui.QPixmap:
    """ Returns a QPixmap object for a given SVG image. File should exist in the ./images folder.

    :param name:    The SVG image name (without extension).
    :param width:   The desired width of the pixmap (pixels).
    :param height:  The desired height of the pixmap (pixels).
    :returns:       A QPixmap object.
    """
    return getSvgIconByName(name).pixmap(QtCore.QSize(width, height))


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

    def _run(self, func: Callable, items: Iterable):
        results_ = []
        try:
            if isgenerator(items):
                # Flatten generators into a tuple
                items = tuple(items)
            for step, item in enumerate(items, 1):
                self.progress.emit(step)
                try:
                    results_.append(func(item))
                except Exception as e:
                    # Log a QGIS error message (should be thread-safe)
                    logError(e)
                    results_.append(e)
                if self.thread().isInterruptionRequested():
                    break
            # Tiny delay so user can see the progress bar at 100%
            self.thread().msleep(100)
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
