from qgiscommons2.utils import _callerName, _callerPath
from qgiscommons2.gui.authconfigselect import AuthConfigSelectDialog
from qgis.PyQt.QtCore import *
import os
import json
from collections import defaultdict
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface

#Types to use for defining parameters

BOOL = "bool"
STRING = "string"
PASSWORD = "password"
TEXT = "text" # a multiline string
NUMBER = "number"
FILES = "files"
FOLDER = "folder"
CHOICE  ="choice"
CRS = "crs"
AUTHCFG = "authcfg"
VECTOR = "vector"
RASTER = "raster"



class Parameter():

    def __init__(self, name, label, description, paramtype, default, options={}):
        self.name = name
        self.label = label
        self.description = description
        self.paramtype = paramtype
        self.default = default
        self.options = options

def parameterFromName(params, name):
    for p in params:
        if p.name == name:
            return p

def openParametersDialog(params, title=None):
    '''
    Opens a dialog to enter parameters.
    Parameters are passed as a list of Parameter objects
    Returns a dict with param names as keys and param values as values
    Returns None if the dialog was cancelled
    '''
    QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
    dlg = ParametersDialog(params, title)
    dlg.exec_()
    QApplication.restoreOverrideCursor()
    return dlg.values

#########################################

class ParametersDialog(QDialog):

    def __init__(self, params, title=None):
        self.params = params
        self.widgets = {}
        QDialog.__init__(self)
        title = title or "Parameters dialog"
        self.setWindowTitle(title)
        self.setupUi()

    def setupUi(self):
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(640, 450)
        self.verticalLayout = QVBoxLayout(self)

        for param in self.params:
            self.verticalLayout.addWidget(QLabel(param.name))
            self.widgets[param.name] = self.widgetFromParameter(param)
            self.verticalLayout.addWidget(self.widgets[param.name])

        self.horizontalLayout = QHBoxLayout(self)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.horizontalLayout.addWidget(self.buttonBox)
        self.verticalLayout.addStretch()
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    class TextBoxWithLink(QWidget):
        def __init__(text, func, value, editable=True):
            self.value = value
            QWidget.__init__(self)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            self.lineEdit = QLineEdit()
            if not editable:
                self.lineEdit.setReadOnly(True)
            self.lineEdit.setText(value)
            layout.addWidget(lineEdit)
            if text:
                linkLabel = QLabel()
                linkLabel.setText("<a href='#'> %s</a>" % text)
                linkLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout.addWidget(linkLabel)
                linkLabel.linkActivated.connect(lambda: func(lineEdit))      
            self.setLayout(layout)

    def widgetFromParameter(self, param):
        if param.paramtype == CRS:
            def edit(textbox):
                selector = QgsGenericProjectionSelector()
                selector.setSelectedAuthId()
                if selector.exec_():
                    authId = selector.selectedAuthId()
                    if authId.upper().startswith("EPSG:"):
                        textbox.value = authId
                        textbox.lineEdit.setText(authId)
            return TextBoxWithLink("Edit", edit, param.default, False)

        elif param.paramtype== FILES:
            def edit(textbox):
                f = QFileDialog.getOpenFileNames(self, "Select file", "", "*.*")
                if f:
                    textbox.value = ",".join(f)
                    textbox.lineEdit.setText(",".join(f))
            return TextBoxWithLink("Browse", edit, None, True)
        elif param.paramtype== FOLDER:
            def edit(textbox):
                f = QFileDialog.getExistingDirectory(self, "Select folder", "")
                if f:
                    textbox.value = f
                    textbox.lineEdit.setText(f)
            return TextBoxWithLink("Browse", edit, None, True)
        elif param.paramtype== BOOL:
            check = QCheckBox(param.label)
            if param.default:
                check.setCheckState(Qt.Checked)
            else:
                check.setCheckState(Qt.Unchecked)
            return check
        elif param.paramtype== CHOICE:
            combo = QComboBox()
            for option in param.options:
                combo.addItem(option)
            idx = combo.findText(str(param.default))
            combo.setCurrentIndex(idx)
            return combo
        elif param.paramtype== TEXT:
            textEdit = QTextEdit()
            textEdit.setPlainText(param.default)
            return textEdit
        elif param.paramtype== AUTHCFG:
            def edit(textbox):
                dlg = AuthConfigSelectDialog(self, authcfg=textbox.value)
                ret = dlg.exec_()
                if ret:
                    self.value = dlg.authcfg
                    lineEdit.setText(str(dlg.authcfg))
            return TextBoxWithLink("Select", edit, param.default, True)
        elif param.paramtype==VECTOR:
            combo = QgsMapLayerComboBox()
            combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
            return combo
        elif param.paramtype==RASTER:
            combo = QgsMapLayerComboBox()
            combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
            return combo        
        elif param.paramtype==PASSWORD:
            lineEdit = QLineEdit()
            lineEdit.setEchoMode(QLineEdit.Password)
            return lineEdit            
        else:
            lineEdit = QLineEdit()
            lineEdit.setText(str(param.default))
            return lineEdit

    def valueFromWidget(self, widget, paramtype):
        try:
            if paramtype == BOOL:
                return widget.checkState(1) == Qt.Checked
            elif paramtype == NUMBER:
                v = float(widget.text())
                return
            elif paramtype == CHOICE:
                return widget.currentText()
            elif paramtype == TEXT:
                return widget.toPlainText()
            elif paramtype == STRING:                
                return widget.text()
            elif paramtype in [CRS, FILES, FOLDER, AUTHCFG]:
                return widget.value
            elif paramtype in [RASTER, VECTOR]:
                return widget.currentLayer()
            else:
                return widget.text()
        except:
            raise #WrongValueException()
            
    def accept(self):
        values = {}
        for name, widget in self.widgets.items():
            try:
                values[name] = self.valueFromWidget(widget, parameterFromName(self.params, name).paramtype)
            except WrongValueException:
                #show warning
                return
        self.values = values
        QDialog.accept(self)


    def reject(self):
        self.values = None
        QDialog.accept(self)

class WrongValueException(Exception):
    pass
