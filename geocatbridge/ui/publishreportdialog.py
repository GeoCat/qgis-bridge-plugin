import os
from functools import partial

from qgis.PyQt import uic
from qgis.core import QgsMessageOutput
from qgis.utils import iface

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QWidget
)

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'publishreportdialog.ui'))

class PublishReportDialog(BASE, WIDGET):

    def __init__(self, results, onlySymbology, geodataServer, metadataServer, parent):
        super(PublishReportDialog, self).__init__(parent)
        self.results = results
        self.setupUi(self)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if geodataServer is not None:
            url = geodataServer.url
            self.labelUrlMapServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMapServer.setText("----")
        if metadataServer is not None:            
            url = metadataServer.url
            self.labelUrlMetadataServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMetadataServer.setText("----")
        publishData = geodataServer is not None
        self.labelPublishMapData.setText("ON" if publishData and not onlySymbology else "OFF")
        self.labelPublishSymbology.setText("ON" if publishData else "OFF")
        self.labelPublishMetadata.setText("ON" if metadataServer is not None else "OFF")
        self.tableWidget.setRowCount(len(results))
        for i, name in enumerate(results.keys()):
            warnings, errors = results[name]
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 0, item)
            if geodataServer is not None:                
                dataPublished = geodataServer.layerExists(name)
                stylePublished = geodataServer.styleExists(name)
            else:
                dataPublished = False
                stylePublished = False
            item = QTableWidgetItem("Yes" if dataPublished else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 1, item)
            item = QTableWidgetItem("Yes" if stylePublished else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 2, item)            
            metadataPublished = metadataServer is not None            
            item = QTableWidgetItem(self.tr("Yes") if metadataPublished else self.tr("No"))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 3, item)
            txt = self.tr("warnings(%i), errors(%i)") % (len(warnings), len(errors))
            widget = QWidget()
            button = QPushButton()
            button.setText(txt)
            button.clicked.connect(partial(self.openDetails, name))
            layout = QHBoxLayout(widget)
            layout.addWidget(button)
            layout.setAlignment(Qt.AlignCenter);
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            self.tableWidget.setCellWidget(i, 4, widget)

    def openDetails(self, name):
        warnings, errors = self.results[name]
        w = "<br><br>".join(warnings)
        e = "<br><br>".join(errors)
        txt = "<p><b>%s</b></p>%s<p><b>%s</b></p>%s" % (self.tr("Warnings:"), w, self.tr("Errors:"), e)
        txt = txt.replace("\n","<br>") # make output easier to read
        dlg = QgsMessageOutput.createMessageOutput()
        dlg.setTitle(self.tr("Warnings / Errors"))
        dlg.setMessage(txt, QgsMessageOutput.MessageHtml)
        dlg.showMessage()


