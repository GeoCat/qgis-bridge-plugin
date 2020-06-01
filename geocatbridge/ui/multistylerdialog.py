import os
import json

from qgis.PyQt.QtWidgets import QVBoxLayout
from qgis.PyQt.QtGui import QFont, QColor, QFontMetrics
from qgis.PyQt.Qsci import QsciScintilla, QsciLexerXML, QsciLexerJSON
from qgis.PyQt import uic

from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsRasterLayer

from bridgestyle.qgis import layerStyleAsSld, layerStyleAsMapbox, layerStyleAsMapfile
from bridgestyle.qgis.togeostyler import convert


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

        self.txtMapbox = EditorWidget(QsciLexerJSON())
        layout = QVBoxLayout()
        layout.addWidget(self.txtMapbox)
        self.widgetMapbox.setLayout(layout)

        self.txtMapserver = EditorWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.txtMapserver)
        self.widgetMapserver.setLayout(layout)        

        self.updateForCurrentLayer()

    def updateLayer(self, layer):
        activeLayer = iface.activeLayer()
        if activeLayer is None or layer.id() == iface.activeLayer().id():
            self.updateForCurrentLayer()

    def updateForCurrentLayer(self):
        layer = iface.activeLayer()        
        sld = ""
        geostyler = ""
        mapbox = ""
        mapserver = ""
        warnings = []
        if layer is not None:
            if (isinstance(layer, QgsRasterLayer) or
                    (isinstance(layer, QgsVectorLayer) and layer.isSpatial())):
                sld, _, sldWarnings = layerStyleAsSld(layer)
                geostyler, _, _, geostylerWarnings = convert(layer)
                geostyler = json.dumps(geostyler, indent=4)
                mapbox, _, mapboxWarnings = layerStyleAsMapbox(layer)
                mapserver, _, _, mapserverWarnings = layerStyleAsMapfile(layer)
                warnings = set()
                warnings.update(sldWarnings)
                warnings.update(geostylerWarnings)
                warnings.update(mapboxWarnings)
                warnings.update(mapserverWarnings)
        self.txtSld.setText(sld)
        self.txtGeostyler.setText(geostyler)
        self.txtMapbox.setText(mapbox)
        self.txtMapserver.setText(mapserver)
        self.txtWarnings.setPlainText("\n".join(warnings))

class EditorWidget(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, lexer=None):
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

        if lexer is not None:
            lexer.setDefaultFont(font)        
            self.setLexer(lexer)

        self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, 1, 'Courier'.encode())