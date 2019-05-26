"""
***************************************************************************
    authconfigselect.py
    ---------------------
    Date                 : March 2017
    Copyright            : (C) 2017 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
__author__ = 'Luigi Pirelli'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


try:
    from qgis.PyQt.QtGui import (
        QDialog,
        QVBoxLayout,
        QDialogButtonBox,
        QPushButton,
        QLineEdit,
        QWidget,
    )
except ImportError:
    from qgis.PyQt.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QDialogButtonBox,
        QPushButton,
        QLineEdit,
        QWidget,
    )
    
from qgis.PyQt.QtCore import Qt

from qgis.gui import QgsAuthConfigSelect

class AuthConfigSelectDialog(QDialog):
    """Dialog to select a Authentication config ID from that available in the
    QGIS Authentication DB. Select can be restricted to that supported by a
    specified and supported provider.
    """
    def __init__(self, parent=None, authcfg=None, provider=None):
        super(AuthConfigSelectDialog, self).__init__(parent)

        self.authcfg = authcfg

        #self.resize(600, 350)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint |
                                                Qt.WindowMinMaxButtonsHint)
        self.setWindowTitle("Authentication config ID selector")

        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.editor = QgsAuthConfigSelect(self, dataprovider=provider)
        self.editor.setConfigId(authcfg)
        layout.addWidget(self.editor)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)

    def okPressed(self):
        self.authcfg = self.editor.configId()
        self.accept()

    def cancelPressed(self):
        self.reject()

class AuthConfigLineEdit(QWidget):
    """Simple widget composed of a QLineEdit and a QButton to start
    AuthConfigSelectDialog.
    This widget is proposed to have a simaple embeddable widget to edit and
    select a AuthCfg ID.
    """
    def __init__(self, parent=None, authcfg=None, provider=None):
        super(AuthConfigLineEdit, self).__init__(parent)

        self.authcfg = authcfg

        layout = QHBoxLayout()
        self.authCfgLineEdit = QLineEdit()
        self.authCfgLineEdit.setObjectName("authCfgLineEdit")
        self.authCfgLineEdit.setText(self.authcfg)
        self.authSelectButton = QPushButton()
        self.authSelectButton.setObjectName("authSelectButton")
        self.authSelectButton.setText("Select")
        layout.addWidget(self.authCfgLineEdit)
        layout.addWidget(self.authSelectButton)
        self.setLayout(layout)
        self.authSelectButton.clicked.connect(self.selectAuthCfg)

    def selectAuthCfg():
        dlg = AuthConfigSelectDialog(self, self.authcfg)
        if dlg.exec_():
            self.authcfg = dlg.authcfg
            self.authCfgLineEdit.setText(self.authcfg)
