from qgis.PyQt.QtWidgets import (QDialog,
                                 QVBoxLayout,
                                 QDialogButtonBox
                                )
from qgis.gui import QgsMetadataWidget

class MetadataDialog(QDialog):

    def __init__(self, metadata, tab, parent = None):
        super(MetadataDialog, self).__init__(parent)
        self.metadata = metadata
        
        self.setWindowTitle('Metadata')
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
