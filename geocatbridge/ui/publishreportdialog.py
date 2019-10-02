import os
from functools import partial
from qgis.PyQt import uic
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from geocatbridge.publish.servers import geodataServers, metadataServers

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'publishreportdialog.ui'))

class PublishReportDialog(BASE, WIDGET):

    def __init__(self, publishWidget, results):
        super(PublishReportDialog, self).__init__(publishWidget)
        self.results = results
        self.setupUi(self)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if publishWidget.comboGeodataServer.currentIndex() != 0:
            url = geodataServers()[publishWidget.comboGeodataServer.currentText()].url
            self.labelUrlMapServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMapServer.setText("----")
        if publishWidget.comboMetadataServer.currentIndex() != 0:            
            url = metadataServers()[publishWidget.comboMetadataServer.currentText()].url
            self.labelUrlMetadataServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMetadataServer.setText("----")
        publishData = publishWidget.comboGeodataServer.currentIndex() != 0 
        onlySymbology = publishWidget.chkOnlySymbology.checkState() == Qt.Checked
        self.labelPublishMapData.setText("ON" if publishData and not onlySymbology else "OFF")
        self.labelPublishSymbology.setText("ON" if publishData else "OFF")
        self.labelPublishMetadata.setText("ON" if publishWidget.comboMetadataServer.currentIndex() != 0 else "OFF")
        self.tableWidget.setRowCount(len(results))
        for i, name in enumerate(results.keys()):
            warnings, errors = results[name]
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 0, item)
            if publishWidget.comboGeodataServer.currentIndex() != 0:
                server = geodataServers()[publishWidget.comboGeodataServer.currentText()]
                dataPublished = server.layerExists(name)
                stylePublished = server.styleExists(name)
            else:
                dataPublished = False
                stylePublished = False
            item = QTableWidgetItem("Yes" if dataPublished else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 1, item)
            item = QTableWidgetItem("Yes" if stylePublished else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 2, item)
            if publishWidget.comboMetadataServer.currentIndex() != 0:          
                metadataPublished = True
            else:
                metadataPublished = False
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
        w = "<br>".join(warnings)
        e = "<br>".join(errors)
        txt = "<b>%s</b><br>%s<br><b>%s</b><br>%s" % (self.tr("Warnings:"), w, self.tr("Errors:"), e)
        dlg = QgsMessageOutput.createMessageOutput()
        dlg.setTitle(self.tr("Layer details"))
        dlg.setMessage(txt, QgsMessageOutput.MessageHtml)
        dlg.showMessage()


