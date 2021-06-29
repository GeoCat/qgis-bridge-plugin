from functools import partial

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QWidget, QLabel, QToolButton
)

from geocatbridge.servers import bases
from geocatbridge.utils import gui, files
from geocatbridge.utils.feedback import FeedbackMixin

WIDGET, BASE = gui.loadUiType(__file__)


class PublishReportDialog(FeedbackMixin, BASE, WIDGET):

    def __init__(self, results, only_symbology, geodata_server, metadata_server, parent):
        super(PublishReportDialog, self).__init__(parent)
        self.results = results
        self.setupUi(self)

        txt_on = self.tr('on').upper()
        txt_off = self.tr('off').upper()

        self.setWindowIcon(QIcon(files.getIconPath('geocat')))
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if isinstance(geodata_server, bases.DataCatalogServerBase):
            url = geodata_server.baseUrl
            self.labelUrlMapServer.setText(f'<a href="{url}">{url}</a>')
        else:
            self.labelUrlMapServer.setText("----")
        if isinstance(metadata_server, bases.MetaCatalogServerBase):
            url = metadata_server.baseUrl
            self.labelUrlMetadataServer.setText(f'<a href="{url}">{url}</a>')
        else:
            self.labelUrlMetadataServer.setText("----")
        publish_data = geodata_server is not None
        self.labelPublishMapData.setText(txt_on if publish_data and not only_symbology else txt_off)
        self.labelPublishSymbology.setText(txt_on if publish_data or only_symbology else txt_off)
        self.labelPublishMetadata.setText(txt_on if metadata_server is not None else txt_off)
        self.tableWidget.setRowCount(len(results))

        # Populate report table
        for i, name in enumerate(results.keys()):
            # Add layer name item
            self.tableWidget.setItem(i, 0, QTableWidgetItem(name))

            # Just show "success" in the last column if there are no errors and warnings
            warnings, errors = results[name]
            if not (warnings or errors):
                self.tableWidget.setItem(i, 1, QTableWidgetItem('OK'))
                continue

            # Show error and warning count and dialog button (for details) in the last column if there are issues
            status_widget = QWidget()
            layout = QHBoxLayout(status_widget)
            button = QToolButton()
            button.setIcon(QIcon(files.getIconPath("attention")))
            button.clicked.connect(partial(self.openDetails, name))
            layout.addWidget(button)
            status_lbl = QLabel()
            status_lbl.setText(self.tr(f"{len(warnings)} warnings, {len(errors)} errors"))
            if errors:
                # Also render text in red if there are any errors
                status_lbl.setStyleSheet("QLabel { color: red; }")
            layout.addWidget(status_lbl)
            layout.setAlignment(Qt.AlignLeft)
            layout.setContentsMargins(0, 0, 0, 0)
            status_widget.setLayout(layout)
            self.tableWidget.setCellWidget(i, 1, status_widget)

    def openDetails(self, name):
        """ Populates and shows a HTML dialog with errors and warnings. """
        warnings, errors = self.results[name]
        w = "".join(f"<p>{w}</p>" for w in warnings).replace("\n", "\n<br>")
        e = "".join(f"<p>{e}</p>" for e in errors).replace("\n", "\n<br>")
        html = f"<p><b>{self.tr('Warnings:')}</b></p>\n{w}\n<p><b>{self.tr('Errors:')}</b></p>\n{e}"
        self.showHtmlMessage(f"Issues for layer {name}", html)
