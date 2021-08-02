from qgis.PyQt import QtCore
from qgis.PyQt.QtWidgets import QMessageBox, QWidget, QProgressDialog
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.core import Qgis, QgsMessageLog, QgsMessageOutput
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from geocatbridge.utils.meta import getAppName

_LOGGER = QgsMessageLog()


def _log(message, level):
    """ Simple log wrapper function. """
    if isinstance(message, Exception):
        message = str(message)
    _LOGGER.logMessage(message, getAppName(), level)


def _translate(message):
    """ Tries to translate the given message within the GeoCat Bridge context. """
    return QtCore.QCoreApplication.translate(getAppName(), str(message))


def logInfo(message):
    """ Logs a basic information message. """
    _log(_translate(message), Qgis.Info)


def logWarning(message):
    """ Logs a basic warning message. """
    _log(_translate(message), Qgis.Warning)


def logError(message):
    """ Logs a basic error message. """
    _log(_translate(message), Qgis.Critical)


class Buttons:
    OK = QMessageBox.Ok
    NO = QMessageBox.No
    YES = QMessageBox.Yes
    CANCEL = QMessageBox.Cancel


class FeedbackMixin:

    BUTTONS = Buttons()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._errors = []
        self._warnings = []
        self._main_bar = iface.messageBar()
        self._widget_bar = self._main_bar
        if not hasattr(self, 'tr'):
            # Do not reset the translate function if it's already there
            self.tr = None

    def _updateWidgetBar(self):
        """ Updates the _widget_bar property if the widget layout has been initialized. """
        if hasattr(self, 'layout') and self.layout():
            self._widget_bar = QgsMessageBar(self if isinstance(self, QWidget) else None)
            self._widget_bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.layout().insertWidget(0, self._widget_bar)

    def _translate(self, message, context=None):
        if context:
            return QtCore.QCoreApplication.translate(context, message)
        if self.tr:
            return self.tr(message)
        # No translation without context or QTranslator
        return message

    def _log(self, message, level, context=None):
        if isinstance(message, Exception):
            message = str(message)
        text = self.translate(context or getAppName(), message)
        _log(text, level)
        if level == Qgis.Warning:
            self._warnings.append(text)
        elif level == Qgis.Critical:
            self._errors.append(text)

    def _propagate(self, message, level, **kwargs):
        value = kwargs.get("propagate")
        if not value or level not in (Qgis.Critical, Qgis.Warning):
            return
        self._log(message if value is True else value, level)

    def _show_bar(self, title, message, level, **kwargs):
        title = self._translate(title)
        message = self._translate(message)
        self._updateWidgetBar()
        bar = self._main_bar if kwargs.get('main') else self._widget_bar
        bar.pushMessage(title, message, level=level, duration=5)
        self._propagate(message, level, **kwargs)

    def _show_box(self, f, title, message, **kwargs):
        parent = self
        if not isinstance(parent, QWidget):
            parent = None
        self._propagate(message, getattr(Qgis, f.__name__.title(), None), **kwargs)
        return f(parent, self._translate(title), self._translate(message), **kwargs)

    def translate(self, context, message):
        """ Tries to translate a message within the provided context. """
        return self._translate(message, context)

    def logInfo(self, message, context=None):
        """ Logs an information message. """
        self._log(message, Qgis.Info, context)

    def logWarning(self, message, context=None):
        """ Logs a warning message. """
        self._log(message, Qgis.Warning, context)

    def logError(self, message, context=None):
        """ Logs an error message. """
        self._log(message, Qgis.Critical, context)

    def getLogIssues(self):
        """ Returns a tuple of all logged (warnings, errors). """
        return self._warnings, self._errors

    def resetLogIssues(self):
        """ Reset the logged warnings and errors lists. """
        self._errors = []
        self._warnings = []

    def showSuccessBar(self, title, message, **kwargs):
        """
        Display a success message bar for 5 seconds at the top of the widget or main application.

        :param title:       Header of the message bar (set to "" if no header is required).
        :param message:     The message that should be displayed in the message bar.
        :keyword main:      When set to `True`, this will display the message bar at the top
                            of the main application window. By default, the bar will be displayed
                            at the top of the current widget, unless there is none.
        """
        self._show_bar(title, message, Qgis.Success, **kwargs)

    def showWarningBar(self, title, message, **kwargs):
        """
        Display a warning message bar for 5 seconds at the top of the widget or main application.

        :param title:       Header of the message bar (set to "" if no header is required).
        :param message:     The message that should be displayed in the message bar.
        :keyword main:      When set to `True`, this will display the message bar at the top
                            of the main application window. By default, the bar will be displayed
                            at the top of the current widget, unless there is none.
        :keyword propagate: When set to `True`, the message will also be logged.
                            When set to a string or Exception, it's value will be logged.
        """
        self._show_bar(title, message, Qgis.Warning, **kwargs)

    def showErrorBar(self, title, message, **kwargs):
        """
        Display an error message bar for 5 seconds at the top of the widget or main application.

        :param title:       Header of the message bar (set to "" if no header is required).
        :param message:     The message that should be displayed in the message bar.
        :keyword main:      When set to `True`, this will display the message bar at the top
                            of the main application window. By default, the bar will be displayed
                            at the top of the current widget, unless there is none.
        :keyword propagate: When set to `True`, the message will also be logged.
                            When set to a string or Exception, it's value will be logged.
        """
        self._show_bar(title, message, Qgis.Critical, **kwargs)

    def getProgressDialog(self, label, max_length, callback=None) -> QProgressDialog:
        """
        Sets up a modal progress dialog, shows it and returns the dialog instance for control.

        :param label:           Message to show above the progress bar.
        :param max_length:      Maximum number of steps of the progress bar (at 100%).
        :param callback:        Callback function to be executed when the user presses "Cancel".
        :return:                A QProgressDialog instance.
        """
        pg_dialog = QProgressDialog(label, self.tr("Cancel"), 0, max_length,
                                    self if isinstance(self, QWidget) else None)
        pg_dialog.canceled.connect(callback, type=QtCore.Qt.DirectConnection)  # noqa
        pg_dialog.setWindowModality(QtCore.Qt.WindowModal)
        pg_dialog.setWindowTitle(getAppName())
        pg_dialog.open()
        return pg_dialog

    def showErrorBox(self, title, message, **kwargs):
        """
        Show an error message box and return a response class.

        :param title:               Header of the message box (set to "" if no header is required).
        :param message:             The message that should be displayed in the message box.
        :keyword buttons:           Optional override of the standard warning box buttons (use BUTTONS.YES/NO/etc.).
        :keyword defaultButton:     Optional override of the default button (use BUTTONS.YES/NO/etc.).
        :keyword propagate:         When set to `True`, the message will also be logged.
                                    When set to a string or Exception, it's value will be logged.
        """
        return self._show_box(QMessageBox.critical, title, message, **kwargs)

    def showWarningBox(self, title, message, **kwargs):
        """
        Show a warning message box and return a response class.

        :param title:               Header of the message box (set to "" if no header is required).
        :param message:             The message that should be displayed in the message box.
        :keyword buttons:           Optional override of the standard warning box buttons (use BUTTONS.YES/NO/etc.).
        :keyword defaultButton:     Optional override of the default button (use BUTTONS.YES/NO/etc.).
        :keyword propagate:         When set to `True`, the message will also be logged.
                                    When set to a string or Exception, it's value will be logged.
        """
        return self._show_box(QMessageBox.warning, title, message, **kwargs)

    def showQuestionBox(self, title, message, **kwargs):
        """
        Show a message box with a question and return a response class.

        :param title:               Header of the message box (set to "" if no header is required).
        :param message:             The message that should be displayed in the message box.
        :keyword buttons:           Optional override of the standard warning box buttons (use BUTTONS.YES/NO/etc.).
        :keyword defaultButton:     Optional override of the default button (use BUTTONS.YES/NO/etc.).
        """
        return self._show_box(QMessageBox.question, title, message, **kwargs)

    def showHtmlMessage(self, title, html):
        """ Show a message dialog with an HTML body. The title is automatically translated.

        :param title:   Header of the HTML dialog (set to "" if no header is required).
        :param html:    The HTML body to display.
        """
        dlg = QgsMessageOutput.createMessageOutput()  # noqa
        dlg.setTitle(self._translate(title))
        dlg.setMessage(html, QgsMessageOutput.MessageHtml)
        dlg.showMessage()
