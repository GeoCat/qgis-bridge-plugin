from qgis.PyQt.QtWidgets import QHBoxLayout

from geocatbridge.servers.bases import ServerWidgetBase
from geocatbridge.servers.models.gn_profile import GeoNetworkProfiles
from geocatbridge.utils import gui
from PyQt5.QtWidgets import *

WIDGET, BASE = gui.loadUiType(__file__)


class GeoNetworkWidget(ServerWidgetBase, BASE, WIDGET):

    def __init__(self, parent, server_type):
        super().__init__(parent, server_type)
        self.setupUi(self)

        self.geonetworkAuth = gui.getBasicAuthSelectWidget(self)
        self.geonetworkAuth.selectedConfigIdChanged.connect(self.setDirty)
        self.addAuthWidget()

        self.txtGeonetworkName.textChanged.connect(self.setDirty)
        self.txtGeonetworkNode.textChanged.connect(self.setDirty)
        self.txtGeonetworkUrl.textChanged.connect(self.setDirty)
        self.txtGeonetworkGroup.textChanged.connect(self.setDirty)
        self.txtGeonetworkAssignToCat.textChanged.connect(self.setDirty)
        self.txtGeonetworkTransformWith.textChanged.connect(self.setDirty)

        self.populateProfileCombo()
        self.comboMetadataProfile.currentIndexChanged.connect(self.setDirty)

        # TODO: implement profile stuff
        self.comboMetadataProfile.setVisible(False)
        self.labelMetadataProfile.setVisible(False)

    def createServerInstance(self):
        """ Reads the settings form fields and returns a new server instance with these settings. """
        try:
            name = self.txtGeonetworkName.text().strip()
            url = self.txtGeonetworkUrl.text().strip()
            if not name:
                raise RuntimeError(f'missing {self.serverType.getLabel()} name')
            if not url:
                raise RuntimeError(f'missing {self.serverType.getLabel()} URL')
            return self.serverType(
                name=name,
                authid=self.geonetworkAuth.configId() or None,
                url=url,
                # profile=self.comboMetadataProfile.currentIndex(),
                node=self.txtGeonetworkNode.text().strip() or 'srv',
                group=self.txtGeonetworkGroup.text().strip(),
                assignCat=self.txtGeonetworkAssignToCat.text().strip(),
                transform=self.txtGeonetworkTransformWith.text().strip()
            )
        except Exception as e:
            self.parent.logError(f"Failed to create {self.serverType.getLabel()} instance: {e}")
            return None

    def newFromName(self, name: str):
        """ Sets the name field and keeps all others empty. """
        self.txtGeonetworkName.setText(name)
        self.txtGeonetworkUrl.clear()
        self.txtGeonetworkNode.clear()
        self.txtGeonetworkGroup.clear()
        self.txtGeonetworkAssignToCat.clear()
        self.txtGeonetworkTransformWith.clear()
        self.geonetworkAuth.setConfigId(None)

        # Reset profile combobox
        self.comboMetadataProfile.blockSignals(True)
        self.comboMetadataProfile.setCurrentIndex(GeoNetworkProfiles.DEFAULT)
        self.comboMetadataProfile.blockSignals(False)

    def loadFromInstance(self, server):
        """ Populates the form fields with the values from the given server instance. """
        self.txtGeonetworkName.setText(server.serverName)
        self.txtGeonetworkUrl.setText(server.baseUrl)
        self.txtGeonetworkNode.setText(server.node)
        self.txtGeonetworkGroup.setText(server.group)
        self.txtGeonetworkAssignToCat.setText(server.assignCat)
        self.txtGeonetworkTransformWith.setText(server.transform)
        self.geonetworkAuth.setConfigId(server.authId)

        # Reset profile combobox
        self.comboMetadataProfile.blockSignals(True)
        self.comboMetadataProfile.setCurrentIndex(server.profile)
        self.comboMetadataProfile.blockSignals(False)

        # After the data has loaded, the form is "clean"
        self.setClean()

    def addAuthWidget(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)
        layout.addWidget(self.geonetworkAuth)
        self.geonetworkAuthWidget.setLayout(layout)
        self.geonetworkAuthWidget.setFixedHeight(self.txtGeonetworkUrl.height())

    def populateProfileCombo(self):
        self.comboMetadataProfile.clear()
        self.comboMetadataProfile.addItems(GeoNetworkProfiles.values())
