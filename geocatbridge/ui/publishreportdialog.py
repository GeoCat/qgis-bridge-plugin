from functools import partial

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QWidget
)

from geocatbridge.utils import gui, files
from geocatbridge.utils.feedback import FeedbackMixin

WIDGET, BASE = gui.loadUiType(__file__)


class PublishReportDialog(FeedbackMixin, BASE, WIDGET):

    def __init__(self, results, only_symbology, geodata_server, metadata_server, parent):
        super(PublishReportDialog, self).__init__(parent)
        self.results = results
        self.setupUi(self)
        self.setWindowIcon(QIcon(files.getIconPath('geocat')))
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if geodata_server is not None:
            url = geodata_server.url
            self.labelUrlMapServer.setText(f'<a href="{url}">{url}</a>')
        else:
            self.labelUrlMapServer.setText("----")
        if metadata_server is not None:
            url = metadata_server.url
            self.labelUrlMetadataServer.setText(f'<a href="{url}">{url}</a>')
        else:
            self.labelUrlMetadataServer.setText("----")
        publish_data = geodata_server is not None
        self.labelPublishMapData.setText("ON" if publish_data and not only_symbology else "OFF")
        self.labelPublishSymbology.setText("ON" if publish_data or only_symbology else "OFF")
        self.labelPublishMetadata.setText("ON" if metadata_server is not None else "OFF")
        self.tableWidget.setRowCount(len(results))
        for i, name in enumerate(results.keys()):
            warnings, errors = results[name]
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 0, item)
            if geodata_server is not None:
                data_published = geodata_server.layerExists(name)
                style_published = geodata_server.styleExists(name)
            else:
                data_published = False
                style_published = False
            item = QTableWidgetItem("Yes" if data_published else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 1, item)
            item = QTableWidgetItem("Yes" if style_published else "No")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 2, item)            
            metadata_published = metadata_server is not None
            item = QTableWidgetItem(self.tr("Yes") if metadata_published else self.tr("No"))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableWidget.setItem(i, 3, item)
            txt = self.tr(f"warnings({len(warnings)}), errors({len(errors)})")
            widget = QWidget()
            button = QPushButton()
            button.setText(txt)
            button.clicked.connect(partial(self.openDetails, name))
            layout = QHBoxLayout(widget)
            layout.addWidget(button)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            self.tableWidget.setCellWidget(i, 4, widget)

    def openDetails(self, name):
        warnings, errors = self.results[name]
        w = "".join(f"<p>{w}</p>" for w in warnings).replace("\n", "\n<br>")
        e = "".join(f"<p>{e}</p>" for e in errors).replace("\n", "\n<br>")
        html = f"<p><b>{self.tr('Warnings:')}</b></p>\n{w}\n<p><b>{self.tr('Errors:')}</b></p>\n{e}"
        self.showHtmlMessage("Errors and warnings", html)
