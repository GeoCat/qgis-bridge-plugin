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

    def __init__(self, geocatdialog):
        super(PublishReportDialog, self).__init__(geocatdialog)
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
        for i in range(geocatdialog.tableLayers.rowCount()):
            item = geocatdialog.tableLayers.item(i, 0)
            if item.checkState() == Qt.Checked:
                name = geocatdialog.tableLayers.item(i, 1).text()
