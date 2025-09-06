import inspect

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


def translate(message, *args, **kwargs):
    """ Tries to translate the given message within the GeoCat Bridge context. """
    return QtCore.QCoreApplication.translate(getAppName(), str(message), *args, **kwargs)  # noqa


def logInfo(message):
    """ Logs a basic information message. """
    _log(translate(message), Qgis.MessageLevel.Info)


def logWarning(message):
    """ Logs a basic warning message. """
    _log(translate(message), Qgis.MessageLevel.Warning)


def logError(message):
    """ Logs a basic error message. """
    _log(translate(message), Qgis.MessageLevel.Critical)


def inject(f, kwarg_name: str = 'feedback'):
    """ Decorator that can be used to inject a FeedbackMixin instance into the 'feedback' keyword argument
    of a wrapped function, if that function has **kwargs and the caller has/is a FeedbackMixin.
    If the wrapped function already has a 'feedback' keyword argument or the caller does not have a FeedbackMixin,
    this decorator does nothing. The wrapped function is responsible for handling the 'feedback' argument correctly.
    """
    def wrapper(*args, **kwargs):
        try:
            has_kwargs = inspect.getfullargspec(f).varkw is not None
            caller = inspect.stack()[1][0].f_locals['self']
        except (KeyError, IndexError, AttributeError):
            has_kwargs = False
            caller = None
        if isinstance(caller, FeedbackMixin) and has_kwargs and kwarg_name not in kwargs:
            kwargs[kwarg_name] = caller
        return f(*args, **kwargs)
    return wrapper


class Buttons:
    OK = QMessageBox.StandardButton.Ok
    NO = QMessageBox.StandardButton.No
    YES = QMessageBox.StandardButton.Yes
    CANCEL = QMessageBox.StandardButton.Cancel


class FeedbackMixin:

    BUTTONS = Buttons()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._errors = []
        self._warnings = []
        self._main_bar = iface.messageBar()
        self._widget_bar = self._main_bar
        self.translate = translate

    def _updateWidgetBar(self):
        """ Updates the _widget_bar property if the widget layout has been initialized. """
        if hasattr(self, 'layout') and self.layout():
            self._widget_bar = QgsMessageBar(self if isinstance(self, QWidget) else None)
            self._widget_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            self.layout().insertWidget(0, self._widget_bar)

    def _log(self, message, level):
        if isinstance(message, Exception):
            message = str(message)
        text = self.translate(message)
        _log(text, level)
        if level == Qgis.MessageLevel.Warning:
            self._warnings.append(text)
        elif level == Qgis.MessageLevel.Critical:
            self._errors.append(text)

    def _propagate(self, message, level, **kwargs):
        value = kwargs.get("propagate")
        if not value or level not in (Qgis.MessageLevel.Critical, Qgis.MessageLevel.Warning):
            return
        self._log(message if value is True else value, level)

    def _show_bar(self, title, message, level, **kwargs):
        title = self.translate(title)
        message = self.translate(message)
        self._updateWidgetBar()
        bar = self._main_bar if kwargs.get('main') else self._widget_bar
        bar.pushMessage(title, message, level=level, duration=5)
        self._propagate(message, level, **kwargs)

    def _show_box(self, f, title, message, **kwargs):
        parent = self
        if not isinstance(parent, QWidget):
            parent = None
        self._propagate(message, getattr(Qgis, f.__name__.title(), None), **kwargs)
        return f(parent, self.translate(title), self.translate(message), **kwargs)

    def logInfo(self, message):
        """ Logs an information message. """
        self._log(message, Qgis.MessageLevel.Info)

    def logWarning(self, message):
        """ Logs a warning message. """
        self._log(message, Qgis.MessageLevel.Warning)

    def logError(self, message):
        """ Logs an error message. """
        self._log(message, Qgis.MessageLevel.Critical)

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
        self._show_bar(title, message, Qgis.MessageLevel.Success, **kwargs)

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
        self._show_bar(title, message, Qgis.MessageLevel.Warning, **kwargs)

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
        self._show_bar(title, message, Qgis.MessageLevel.Critical, **kwargs)

    def getProgressDialog(self, label, max_length, callback=None) -> QProgressDialog:
        """
        Sets up a modal progress dialog, shows it and returns the dialog instance for control.

        :param label:           Message to show above the progress bar.
        :param max_length:      Maximum number of steps of the progress bar (at 100%).
        :param callback:        Callback function to be executed when the user presses "Cancel".
        :return:                A QProgressDialog instance.
        """
        if not isinstance(self, QWidget):
            raise ValueError("A QWidget parent instance is required to show a progress dialog.")
        pg_dialog = QProgressDialog(self, QtCore.Qt.WindowType.Popup)
        pg_dialog.setLabelText(label)
        pg_dialog.setAutoReset(False)
        pg_dialog.setAutoClose(False)
        pg_dialog.setCancelButtonText(self.tr("Cancel"))
        pg_dialog.setRange(0, max_length)
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
        :keyword buttons:           Optional override of the standard error box buttons (use BUTTONS.YES/NO/etc.).
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
        :keyword buttons:           Optional override of the standard question box buttons (use BUTTONS.YES/NO/etc.).
        :keyword defaultButton:     Optional override of the default button (use BUTTONS.YES/NO/etc.).
        """
        return self._show_box(QMessageBox.question, title, message, **kwargs)

    def showHtmlMessage(self, title, html):
        """ Show a message dialog with an HTML body. The title is automatically translated.

        :param title:   Header of the HTML dialog (set to "" if no header is required).
        :param html:    The HTML body to display.
        """
        dlg = QgsMessageOutput.createMessageOutput()  # noqa
        dlg.setTitle(self.translate(title))
        dlg.setMessage(html, QgsMessageOutput.MessageType.MessageHtml)
        dlg.showMessage()
