import os
from qgis.PyQt import uic
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from geocatbridge.publish.servers import geodataServers, metadataServers

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'publishreportdialog.ui'))

class PublishReportDialog(BASE, WIDGET):

    def __init__(self, geocatdialog, results):
        super(PublishReportDialog, self).__init__(geocatdialog)
        self.results = results
        self.setupUi(self)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if geocatdialog.chkPublishToGeodataServer.checkState() == Qt.Checked:
            url = geodataServers()[geocatdialog.comboGeodataServer.currentText()].catalog().service_url
            self.labelUrlMapServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMapServer.setText("----")
        if geocatdialog.chkPublishToMetadataServer.checkState() == Qt.Checked:            
            url = metadataServers()[geocatdialog.comboMetadataServer.currentText()].catalog().service_url
            self.labelUrlMetadataServer.setText('<a href="%s">%s</a>' % (url, url))
        else:
            self.labelUrlMetadataServer.setText("----")
        self.labelPublishMapData.setText("ON" if geocatdialog.chkPublishToGeodataServer.checkState() == Qt.Checked else "OFF")
        self.labelPublishMetadata.setText("ON" if geocatdialog.chkPublishToMetadataServer.checkState() == Qt.Checked else "OFF")
        self.tableWidget.setRowCount(len(results))
        for i, name in enumerate(results.keys()):
            warnings, errors = results[name]
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 0, item)
            item = QTableWidgetItem("Yes") #TODO
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 1, item)
            item = QTableWidgetItem("Yes") #TODO
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 2, item)
            item = QTableWidgetItem("Yes") #TODO
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 3, item)
            txt = "warnings(%i), errors(%i)" % (len(warnings), len(errors))
            widget = QWidget()
            button = QPushButton()
            button.setText(txt)
            button.clicked.connect(lambda: self.openDetails(name))
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
        txt = "<b>Warnings:</b><br>%s<br><b>Errors:</b><br>%s" % (w, e)
        dlg = QgsMessageOutput.createMessageOutput()
        dlg.setTitle("Layer details")
        dlg.setMessage(txt, QgsMessageOutput.MessageHtml)
        dlg.showMessage()


