import os
import json
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.utils import iface
from multistyler.qgis.geostyler import layerAsGeostyler
from multistyler.qgis import layerStyleAsSld
from qgis.PyQt.Qsci import QsciScintilla, QsciLexerXML, QsciLexerJSON
from qgis.PyQt import uic

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'multistyler.ui'))

class MultistylerDialog(BASE, WIDGET):

    def __init__(self, ):
        super(MultistylerDialog, self).__init__(iface.mainWindow())
        self.setupUi(self)

        self.txtSld = EditorWidget(QsciLexerXML())
        layout = QVBoxLayout()
        layout.addWidget(self.txtSld)
        self.widgetSld.setLayout(layout)

        self.txtGeostyler = EditorWidget(QsciLexerJSON())
        layout = QVBoxLayout()
        layout.addWidget(self.txtGeostyler)
        self.widgetGeostyler.setLayout(layout)

        self.updateForCurrentLayer()

    def updateForCurrentLayer(self):
        layer = iface.activeLayer()
        if layer is None:
            sld = ""
            geostyler = ""
        else:
            sld = layerStyleAsSld(layer)[0]
            geostyler = json.dumps(layerAsGeostyler(layer)[0], indent=4)
        self.txtSld.setText(sld)
        self.txtGeostyler.setText(geostyler)

class EditorWidget(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, lexer):
        super(EditorWidget, self).__init__()

        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        self.setMarginsFont(font)

        fontmetrics = QFontMetrics(font)
        self.setMarginsFont(font)
        self.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#cccccc"))

        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)

        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#ffe4e4"))


        lexer.setDefaultFont(font)
        self.setLexer(lexer)
        self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, 1, 'Courier'.encode())       