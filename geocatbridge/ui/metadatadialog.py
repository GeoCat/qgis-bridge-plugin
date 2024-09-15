from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QDialogButtonBox
                                 )
from qgis.gui import QgsMetadataWidget
from qgis.core import QgsApplication

from geocatbridge.utils.feedback import FeedbackMixin


class MetadataDialog(FeedbackMixin, QDialog):

    def __init__(self, layer, tab, parent=None):
        super(MetadataDialog, self).__init__(parent)
        self.setModal(True)
        self.setWindowIcon(QgsApplication.getThemeIcon("../../icons/qgis_icon.svg"))  # noqa
        self.setWindowTitle(self.translate('QGIS Metadata Editor'))
        layout = QVBoxLayout()
        self.metadataWidget = QgsMetadataWidget(parent, layer)
        layout.addWidget(self.metadataWidget)  # noqa
        self.metadataWidget.layout().itemAt(0).widget().setCurrentIndex(tab)  # noqa

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)  # noqa
        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)  # noqa
        self.buttonBox.rejected.connect(self.cancelPressed)  # noqa

    def okPressed(self):
        self.metadataWidget.acceptMetadata()
        self.accept()

    def cancelPressed(self):
        self.reject()
