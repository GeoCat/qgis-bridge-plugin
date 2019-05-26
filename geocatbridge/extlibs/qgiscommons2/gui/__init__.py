from qgiscommons2.utils import _callerName, _callerPath, pluginDetails
from qgiscommons2.settings import pluginSetting, setPluginSetting
from qgis.PyQt import QtGui, QtCore, uic, QtWidgets
from qgis.core import *
from qgis.gui import QgsMessageBar
from qgis.utils import iface
import inspect
import os
import webbrowser

_helpActions = {}
def addHelpMenu(menuName, parentMenuFunction=None):
    '''
    Adds a help menu to the plugin menu.
    This method should be called from the initGui() method of the plugin

    :param menuName: The name of the plugin menu in which the about menu is to be added.
    '''

    parentMenuFunction = parentMenuFunction or iface.addPluginToMenu
    namespace = _callerName().split(".")[0]
    path = "file://{}".format(os.path.join(os.path.dirname(_callerPath()), "docs",  "html", "index.html"))
    helpAction = QtWidgets.QAction(
        QgsApplication.getThemeIcon('/mActionHelpAPI.png'),
        "Plugin help...",
        iface.mainWindow())
    helpAction.setObjectName(namespace + "help")
    helpAction.triggered.connect(lambda: openHelp(path))
    parentMenuFunction(menuName, helpAction)
    global _helpActions
    _helpActions[menuName] = helpAction


def removeHelpMenu(menuName, parentMenuFunction=None):
    global _helpActions
    parentMenuFunction = parentMenuFunction or iface.removePluginMenu
    parentMenuFunction(menuName, _helpActions[menuName])
    action = _helpActions.pop(menuName, None)
    action.deleteLater()


def openHelp(helpPath=None):
    if helpPath is None:
        helpPath = "file://{}".format(os.path.join(os.path.dirname(_callerPath()), "docs", "html", "index.html"))

    webbrowser.open_new(helpPath)

_aboutActions = {}
def addAboutMenu(menuName, parentMenuFunction=None):
    '''
    Adds an 'about...' menu to the plugin menu.
    This method should be called from the initGui() method of the plugin

    :param menuName: The name of the plugin menu in which the about menu is to be added
    '''

    parentMenuFunction = parentMenuFunction or iface.addPluginToMenu
    namespace = _callerName().split(".")[0]
    aboutAction = QtWidgets.QAction(
        QgsApplication.getThemeIcon('/mActionHelpContents.svg'),
        "About...",
        iface.mainWindow())
    aboutAction.setObjectName(namespace + "about")
    aboutAction.triggered.connect(lambda: openAboutDialog(namespace))
    parentMenuFunction(menuName, aboutAction)
    global _aboutActions
    _aboutActions[menuName] = aboutAction


def removeAboutMenu(menuName, parentMenuFunction=None):
    global _aboutActions
    parentMenuFunction = parentMenuFunction or iface.removePluginMenu
    parentMenuFunction(menuName, _aboutActions[menuName])
    action = _aboutActions.pop(menuName, None)
    action.deleteLater()

def openAboutDialog(namespace):
    showMessageDialog("Plugin info", pluginDetails(namespace))

def showMessageDialog(title, text):
    '''
    Show a dialog containing a given text, with a given title.

    The text accepts HTML syntax
    '''
    dlg = QgsMessageOutput.createMessageOutput()
    dlg.setTitle(title)
    dlg.setMessage(text, QgsMessageOutput.MessageHtml)
    dlg.showMessage()


def loadUi(name):
    if os.path.exists(name):
        uifile = name
    else:
        frame = inspect.stack()[1]
        filename = inspect.getfile(frame[0])
        uifile = os.path.join(os.path.dirname(filename), name)
        if not os.path.exists(uifile):
            uifile = os.path.join(os.path.dirname(filename), "ui", name)

    widget, base = uic.loadUiType(uifile)
    return widget, base

LAST_PATH = "LAST_PATH"

def askForFiles(parent, msg = None, isSave = False, allowMultiple = False, exts = "*"):
    '''
    Asks for a file or files, opening the corresponding dialog with the last path that was selected
    when this same function was invoked from the calling method.

    :param parent: The parent window
    :param msg: The message to use for the dialog title
    :param isSave: true if we are asking for file to save
    :param allowMultiple: True if should allow multiple files to be selected. Ignored if isSave == True
    :param exts: Extensions to allow in the file dialog. Can be a single string or a list of them.
    Use "*" to add an option that allows all files to be selected

    :returns: A string with the selected filepath or an array of them, depending on whether allowMultiple is True of False
    '''
    msg = msg or 'Select file'
    caller = _callerName().split(".")
    name = "/".join([LAST_PATH, caller[-1]])
    namespace = caller[0]
    path = pluginSetting(name, namespace)
    f = None
    if not isinstance(exts, list):
        exts = [exts]
    extString = ";; ".join([" %s files (*.%s)" % (e.upper(), e) if e != "*" else "All files (*.*)" for e in exts])
    if allowMultiple:
        ret = QtWidgets.QFileDialog.getOpenFileNames(parent, msg, path, '*.' + extString)
        if ret:
            f = ret[0]
        else:
            f = ret = None
    else:
        if isSave:
            ret = QtWidgets.QFileDialog.getSaveFileName(parent, msg, path, '*.' + extString) or None
            if ret is not None and not ret.endswith(exts[0]):
                ret += "." + exts[0]
        else:
            ret = QtWidgets.QFileDialog.getOpenFileName(parent, msg , path, '*.' + extString) or None
        f = ret

    if f is not None:
        setPluginSetting(name, os.path.dirname(f), namespace)

    return ret

def askForFolder(parent, msg = None):
    '''
    Asks for a folder, opening the corresponding dialog with the last path that was selected
    when this same function was invoked from the calling method

    :param parent: The parent window
    :param msg: The message to use for the dialog title
    '''
    msg = msg or 'Select folder'
    caller = _callerName().split(".")
    name = "/".join([LAST_PATH, caller[-1]])
    namespace = caller[0]
    path = pluginSetting(name, namespace)
    folder =  QtWidgets.QFileDialog.getExistingDirectory(parent, msg, path)
    if folder:
        setPluginSetting(name, folder, namespace)
    return folder

#=============

_dialog = None

class ExecutorThread(QtCore.QThread):

    finished = QtCore.pyqtSignal()

    def __init__(self, func):
        QtCore.QThread.__init__(self, iface.mainWindow())
        self.func = func
        self.returnValue = None
        self.exception = None

    def run (self):
        try:
            self.returnValue = self.func()
        except Exception as e:
            self.exception = e
        finally:
            self.finished.emit()

def execute(func, message = None):
    '''
    Executes a lengthy tasks in a separate thread and displays a waiting dialog if needed.
    Sets the cursor to wait cursor while the task is running.

    This function does not provide any support for progress indication

    :param func: The function to execute.

    :param message: The message to display in the wait dialog. If not passed, the dialog won't be shown
    '''
    global _dialog
    cursor = QtWidgets.QApplication.overrideCursor()
    waitCursor = (cursor is not None and cursor.shape() == QtCore.Qt.WaitCursor)
    dialogCreated = False
    try:
        QtCore.QCoreApplication.processEvents()
        if not waitCursor:
            QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        if message is not None:
            t = ExecutorThread(func)
            loop = QtCore.QEventLoop()
            t.finished.connect(loop.exit, QtCore.Qt.QueuedConnection)
            if _dialog is None:
                dialogCreated = True
                _dialog = QtGui.QProgressDialog(message, "Running", 0, 0, iface.mainWindow())
                _dialog.setWindowTitle("Running")
                _dialog.setWindowModality(QtCore.Qt.WindowModal);
                _dialog.setMinimumDuration(1000)
                _dialog.setMaximum(100)
                _dialog.setValue(0)
                _dialog.setMaximum(0)
                _dialog.setCancelButton(None)
            else:
                oldText = _dialog.labelText()
                _dialog.setLabelText(message)
            QtWidgets.QApplication.processEvents()
            t.start()
            loop.exec_(flags = QtCore.QEventLoop.ExcludeUserInputEvents)
            if t.exception is not None:
                raise t.exception
            return t.returnValue
        else:
            return func()
    finally:
        if message is not None:
            if dialogCreated:
                _dialog.reset()
                _dialog = None
            else:
                _dialog.setLabelText(oldText)
        if not waitCursor:
            QtWidgets.QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()

#=====

_messageBar = None
_progress = None
_progressMessageBar = None
_progressTextLabel = None
_progressActive = False

def startProgressBar(title, totalSteps, messageBar = None):
    global _progress
    global _progressMessageBar
    global _messageBar
    global _progressActive
    closeProgressBar()
    _progressActive = True
    _messageBar = messageBar or iface.messageBar()
    _progressMessageBar = _messageBar.createMessage(title)
    _progress = QtWidgets.QProgressBar()
    _progress.setRange(0,totalSteps)
    #_progress.setValue(0)
    _progress.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
    _progressMessageBar.layout().addWidget(_progress)
    cancelButton = QtWidgets.QPushButton("Cancel")
    cancelButton.clicked.connect(closeProgressBar)
    _progressMessageBar.layout().addWidget(cancelButton)
    _messageBar.pushWidget(_progressMessageBar, Qgis.Info)
    QtCore.QCoreApplication.processEvents()

def setProgressText(text):
    if _progressMessageBar is not None:
        _progressMessageBar.setText(text)
        QtCore.QCoreApplication.processEvents()

def setProgressValue(value):
    if _progress is not None:
        _progress.setValue(value)
        QtCore.QCoreApplication.processEvents()

def isProgressCanceled():
    return not _progressActive

def closeProgressBar():
    global _progress
    global _progressMessageBar
    global _messageBar
    global _progressActive
    try:
        if _messageBar is not None:
            _messageBar.clearWidgets()
    except:
        pass # this can happen if _messageBar is no longer valid (i.e. window closed)
    _progressActive = False
    _progress = None
    _progressMessageBar = None
    _messageBar = None