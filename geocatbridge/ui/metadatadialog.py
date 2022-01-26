from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QDialogButtonBox
                                 )
from qgis.gui import QgsMetadataWidget

from geocatbridge.utils.files import getIconPath
from geocatbridge.utils.feedback import FeedbackMixin


class MetadataDialog(FeedbackMixin, QDialog):

    def __init__(self, layer, tab, parent=None):
        super(MetadataDialog, self).__init__(parent)
        self.setModal(True)
        self.setWindowIcon(QIcon(getIconPath('geocat')))
        self.setWindowTitle(self.translate('Metadata'))
        layout = QVBoxLayout()
        self.metadataWidget = QgsMetadataWidget(parent, layer)
        layout.addWidget(self.metadataWidget)  # noqa
        self.metadataWidget.layout().itemAt(0).widget().setCurrentIndex(tab)

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
