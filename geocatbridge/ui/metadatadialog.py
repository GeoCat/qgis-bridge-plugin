from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QDialogButtonBox
                                 )
from qgis.gui import QgsMetadataWidget

from geocatbridge.utils.files import getIconPath


class MetadataDialog(QDialog):

    def __init__(self, metadata, tab, parent=None):
        super(MetadataDialog, self).__init__(parent)
        self.setModal(True)
        self.setWindowIcon(QIcon(getIconPath('geocat')))

        self.metadata = metadata
        self.setWindowTitle(self.tr('Metadata'))
        layout = QVBoxLayout()
        self.metadataWidget = QgsMetadataWidget()
        self.metadataWidget.setMetadata(metadata)
        layout.addWidget(self.metadataWidget)
        self.metadataWidget.layout().itemAt(0).widget().setCurrentIndex(tab)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)

    def okPressed(self):
        self.metadataWidget.saveMetadata(self.metadata)
        self.close()

    def cancelPressed(self):
        self.metadata = None
        self.close()
