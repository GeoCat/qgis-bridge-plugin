import json
from traceback import format_exc
from itertools import chain

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.Qsci import QsciScintilla, QsciLexerXML, QsciLexerJSON
from qgis.PyQt.QtWidgets import QApplication, QVBoxLayout, QDockWidget, QFrame
from qgis.utils import iface

from geocatbridge.publish.style import (
    layerStyleAsSld, layerStyleAsMapbox, layerStyleAsMapfile, convertStyle
)
from geocatbridge.utils.layers import isSupportedLayer
from geocatbridge.utils.feedback import FeedbackMixin
from geocatbridge.utils import gui

WIDGET, BASE = gui.loadUiType(__file__)


class StyleViewerWidget(FeedbackMixin, BASE, WIDGET):

    def __init__(self):
        super(StyleViewerWidget, self).__init__(iface.mainWindow())
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

    def setTitle(self, title: str):
        if not isinstance(self, QDockWidget):
            return
        self.setWindowTitle(title)

    def updateLayer(self, layer):
        active_layer = iface.activeLayer()
        if active_layer is None or layer.id() == iface.activeLayer().id():
            self.updateForCurrentLayer()

    def updateForCurrentLayer(self):
        layer = iface.activeLayer()        
        sld = ""
        geostyler = ""
        mapbox = ""
        mapserver = ""
        warnings = set()
        if isSupportedLayer(layer):
            # Try SLD conversion
            try:
                sld, _, sld_warnings = layerStyleAsSld(layer)
            except Exception as e:
                self.logError(format_exc())
                sld_warnings = [f"Failed to convert to SLD: {e}"]
            # Try GeoStyler conversion
            try:
                geostyler, _, _, geostyler_warnings = convertStyle(layer)
                geostyler = json.dumps(geostyler, indent=4)
            except Exception as e:
                self.logError(format_exc())
                geostyler_warnings = [f"Failed to convert to GeoStyler: {e}"]
            # Try MapBox GL conversion
            try:
                mapbox, _, mapbox_warnings = layerStyleAsMapbox(layer)
            except Exception as e:
                self.logError(format_exc())
                mapbox_warnings = [f"Failed to convert to MapBox GL: {e}"]
            # Try Mapfile conversion
            try:
                mapserver, _, _, mapserver_warnings = layerStyleAsMapfile(layer)
            except Exception as e:
                self.logError(format_exc())
                mapserver_warnings = [f"Failed to convert to Mapfile: {e}"]
            # Collect all warnings
            warnings.update(chain(sld_warnings, geostyler_warnings, mapbox_warnings, mapserver_warnings))
        self.txtSld.setText(sld)
        self.txtGeostyler.setText(geostyler)
        self.txtMapbox.setText(mapbox)
        self.txtMapserver.setText(mapserver)
        self.txtWarnings.setPlainText("\n".join(warnings))


class EditorWidget(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, lexer=None):
        super(EditorWidget, self).__init__()

        if isinstance(self, QFrame):
            self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)

        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setFolding(QsciScintilla.FoldStyle.CircledTreeFoldStyle)

        if lexer is not None:
            # Lexer foreground colors are not suitable for dark mode,
            # so we force a white background color as a workaround.
            lexer.setDefaultPaper(Qt.GlobalColor.white)
            self.setLexer(lexer)
        else:
            # Reflect lexers (for Mapfile): dark text against white background.
            self.setPaper(Qt.GlobalColor.white)
            self.setColor(Qt.GlobalColor.black)

        self.setReadOnly(True)
