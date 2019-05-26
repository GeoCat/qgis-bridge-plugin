import os
import json
from collections import defaultdict

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QAction,
                                 QDialog,
                                 QVBoxLayout,
                                 QHBoxLayout,
                                 QTreeWidget,
                                 QPushButton,
                                 QDialogButtonBox,
                                 QTreeWidgetItem,
                                 QTreeWidgetItemIterator,
                                 QTextEdit,
                                 QWidget,
                                 QLineEdit,
                                 QSizePolicy,
                                 QFileDialog,
                                 QComboBox,
                                 QLabel
                                )
from qgis.core import QgsApplication
from qgis.gui import QgsFilterLineEdit
try:
    from qgis.gui import QgsGenericProjectionSelector as QgsProjectionSelectionDialog
except:
    from qgis.gui import QgsProjectionSelectionDialog

from qgis.utils import iface

from qgiscommons2.settings import *
from qgiscommons2.utils import _callerName, _callerPath
from qgiscommons2.gui.authconfigselect import AuthConfigSelectDialog

_settingActions = {}
def addSettingsMenu(menuName, parentMenuFunction=None):
    '''
    Adds a 'open settings...' menu to the plugin menu.
    This method should be called from the initGui() method of the plugin

    :param menuName: The name of the plugin menu in which the settings menu is to be added
    :param parentMenuFunction: a function from QgisInterface to indicate where to put the container plugin menu.
    If not passed, it uses addPluginToMenu
    '''

    parentMenuFunction = parentMenuFunction or iface.addPluginToMenu
    namespace = _callerName().split(".")[0]
    settingsAction = QAction(
        QgsApplication.getThemeIcon('/mActionOptions.svg'),
        "Plugin Settings...",
        iface.mainWindow())
    settingsAction.setObjectName(namespace + "settings")
    settingsAction.triggered.connect(lambda: openSettingsDialog(namespace))
    parentMenuFunction(menuName, settingsAction)
    global _settingActions
    _settingActions[menuName] = settingsAction


def removeSettingsMenu(menuName, parentMenuFunction=None):
    global _settingActions
    parentMenuFunction = parentMenuFunction or iface.removePluginMenu
    parentMenuFunction(menuName, _settingActions[menuName])
    action = _settingActions.pop(menuName, None)
    action.deleteLater()


def openSettingsDialog(namespace):
    '''
    Opens the settings dialog for the passed namespace.
    Instead of calling this function directly, consider using addSettingsMenu()
    '''
    dlg = ConfigDialog(namespace)
    dlg.show()

#########################################

class ConfigDialog(QDialog):

    def __init__(self, namespace):
        self.settings = pluginSettings(namespace)
        self.namespace = namespace
        QDialog.__init__(self, iface.mainWindow())
        self.setupUi()
        if hasattr(self.searchBox, 'setPlaceholderText'):
            self.searchBox.setPlaceholderText(self.tr("Search..."))
        self.searchBox.textChanged.connect(self.filterTree)
        self.fillTree()
        self.tree.expandAll()

    def setupUi(self):
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(640, 450)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)
        self.searchBox = QgsFilterLineEdit(self)
        self.verticalLayout.addWidget(self.searchBox)
        self.tree = QTreeWidget(self)
        self.tree.setAlternatingRowColors(True)
        self.verticalLayout.addWidget(self.tree)
        self.horizontalLayout = QHBoxLayout(self)
        self.resetButton = QPushButton("Reset default values")
        self.resetButton.clicked.connect(self.resetDefault)
        self.horizontalLayout.addWidget(self.resetButton)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.horizontalLayout.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.setWindowTitle("Configuration options")
        self.searchBox.setToolTip("Enter setting name to filter list")
        self.tree.headerItem().setText(0, "Setting")
        self.tree.headerItem().setText(1, "Value")

        def saveValues():
            iterator = QTreeWidgetItemIterator(self.tree)
            value = iterator.value()
            while value:
                if hasattr(value, 'saveValue'):
                    try:
                        value.saveValue()
                    except WrongValueException:
                        return
                iterator += 1
                value = iterator.value()
            QDialog.accept(self)
            self.close()

        self.buttonBox.accepted.connect(saveValues)
        self.buttonBox.rejected.connect(self.reject)

    def resetDefault(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            for j in range(item.childCount()):
                subitem = item.child(j)
                subitem.resetDefault()

    def filterTree(self):
        text = unicode(self.searchBox.text())
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            visible = False
            for j in range(item.childCount()):
                subitem = item.child(j)
                itemText = subitem.text(0)
            if (text.strip() == ""):
                subitem.setHidden(False)
                visible = True
            else:
                hidden = text not in itemText
                item.setHidden(hidden)
                visible = visible or not hidden
            item.setHidden(not visible)
            item.setExpanded(visible and text.strip() != "")

    def fillTree(self):
        self.items = {}
        self.tree.clear()

        grouped = defaultdict(list)
        for setting in self.settings:
            grouped[setting["group"]].append(setting)
        for groupName, group in grouped.items():
            item = self._getGroupItem(groupName, group)
            self.tree.addTopLevelItem(item)

        self.tree.setColumnWidth(0, 400)

    def _getGroupItem(self, groupName, params):
        item = QTreeWidgetItem()
        item.setText(0, groupName)
        icon = QIcon(os.path.join(os.path.dirname(__file__), "setting.png"))
        item.setIcon(0, icon)
        for param in params:
            value = pluginSetting(param["name"], self.namespace)
            subItem = TreeSettingItem(item, self.tree, param, self.namespace, value)
            item.addChild(subItem)
        return item




class WrongValueException(Exception):
    pass


class TreeSettingItem(QTreeWidgetItem):

    comboStyle = '''QComboBox {
                 border: 1px solid gray;
                 border-radius: 3px;
                 padding: 1px 18px 1px 3px;
                 min-width: 6em;
             }

             QComboBox::drop-down {
                 subcontrol-origin: padding;
                 subcontrol-position: top right;
                 width: 15px;
                 border-left-width: 1px;
                 border-left-color: darkgray;
                 border-left-style: solid;
                 border-top-right-radius: 3px;
                 border-bottom-right-radius: 3px;
             }
            '''

    def _addTextEdit(self, editable=True):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.textEdit = QTextEdit()
        if not editable:
            self.textEdit.setReadOnly(True)
        self.textEdit.setPlainText(self._value)
        layout.addWidget(self.textEdit)
        w = QWidget()
        w.setLayout(layout)
        self.tree.setItemWidget(self, 1, w)

    def _addTextBoxWithLink(self, text, func, editable=True):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.lineEdit = QLineEdit()
        if not editable:
            self.lineEdit.setReadOnly(True)
        self.lineEdit.setText(self._value)
        layout.addWidget(self.lineEdit)
        if text:
            self.linkLabel = QLabel()
            self.linkLabel.setText("<a href='#'> %s</a>" % text)
            self.linkLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(self.linkLabel)
            self.linkLabel.linkActivated.connect(func)
        w = QWidget()
        w.setLayout(layout)
        self.tree.setItemWidget(self, 1, w)

    def __init__(self, parent, tree, setting, namespace, value):
        QTreeWidgetItem.__init__(self, parent)
        self.parent = parent
        self.namespace = namespace
        self.tree = tree
        self._value = value
        self.setting = setting
        self.name = setting["name"]
        self.labelText = setting["label"]
        self.settingType = setting["type"]
        self.setText(0, self.labelText)
        if self.settingType == CRS:
            def edit():
                selector = QgsProjectionSelectionDialog()
                selector.setCrs(value);
                if selector.exec_():
                    crs = selector.crs()
                    if crs.upper().startswith("EPSG:"):
                        self.lineEdit.setText(crs)
            self._addTextBoxWithLink("Edit", edit, False)
        elif self.settingType == FILES:
            def edit():
                f = QFileDialog.getOpenFileNames(parent.treeWidget(), "Select file", "", "*.*")
                if f:
                    self.lineEdit.setText(",".join(f))
            self._addTextBoxWithLink("Browse", edit, True)
        elif self.settingType == FILE:
            def edit():
                f = QFileDialog.getOpenFileName(parent.treeWidget(), "Select file", "", "*.*")
                if f:
                    self.lineEdit.setText(f)
            self._addTextBoxWithLink("Browse", edit, True)
        elif self.settingType == FOLDER:
            def edit():
                f = QFileDialog.getExistingDirectory(parent.treeWidget(), "Select folder", "")
                if f:
                    self.lineEdit.setText(f)
            self._addTextBoxWithLink("Browse", edit, True)
        elif self.settingType == BOOL:
            if value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        elif self.settingType == CHOICE:
            self.combo = QComboBox()
            self.combo.setStyleSheet(self.comboStyle)
            for option in setting["options"]:
                self.combo.addItem(option)
            self.tree.setItemWidget(self, 1, self.combo)
            idx = self.combo.findText(str(value))
            self.combo.setCurrentIndex(idx)
        elif self.settingType == TEXT:
            self._addTextEdit()
        elif self.settingType == STRING:
            self._addTextBoxWithLink(None, None)
        elif self.settingType == AUTHCFG:
            def edit():
                currentAuthCfg = self.value()
                dlg = AuthConfigSelectDialog(parent.treeWidget(), authcfg=currentAuthCfg)
                ret = dlg.exec_()
                if ret:
                    self.lineEdit.setText(dlg.authcfg)
            self._addTextBoxWithLink("Select", edit, True)
        else:
            self.setFlags(self.flags() | Qt.ItemIsEditable)
            self.setText(1, unicode(value))

    def saveValue(self):
        value = self.value()
        setPluginSetting(self.name, value, self.namespace)

    def value(self):
        self.setBackground(0, Qt.white)
        self.setBackground(1, Qt.white)
        try:
            if self.settingType == BOOL:
                return self.checkState(1) == Qt.Checked
            elif self.settingType == NUMBER:
                v = float(self.text(1))
                return v
            elif self.settingType == CHOICE:
                return self.combo.currentText()
            elif self.settingType in [TEXT]:
                return self.textEdit.toPlainText()
            elif self.settingType in [CRS, STRING, FILES, FOLDER, AUTHCFG]:
                return self.lineEdit.text()
            else:
                return self.text(1)
        except:
            self.setBackground(0, Qt.yellow)
            self.setBackground(1, Qt.yellow)
            raise WrongValueException()

    def setValue(self, value):
        if self.settingType == BOOL:
            if value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        elif self.settingType == CHOICE:
            idx = self.combo.findText(str(value))
            self.combo.setCurrentIndex(idx)
        elif self.settingType in [TEXT, CRS, STRING, FILES, FOLDER, AUTHCFG]:
            self.lineEdit.setText(value)
        else:
            self.setText(1, unicode(value))

    def resetDefault(self):
        self.setValue(self.setting["default"])


class TextEditorDialog(QDialog):

    def __init__(self, text):
        super(TextEditorDialog, self).__init__()

        self.text = text

        self.resize(600, 350)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint |
                                                 Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Editor")

        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.editor = QTextEdit()
        self.editor.setPlainText(text)
        layout.addWidget(self.editor)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)

    def okPressed(self):
        self.text = self.editor.toPlainText()
        self.accept()

    def cancelPressed(self):
        self.reject()
