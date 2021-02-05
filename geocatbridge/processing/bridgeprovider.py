from processing.core.ProcessingConfig import ProcessingConfig, Setting
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from geocatbridge.processing.publishtogeonetwork import PublishToGeonetworkAlgorithm
from geocatbridge.processing.publishtogeoserver import PublishToGeoserverAlgorithm
from geocatbridge.utils import meta
from geocatbridge.utils.files import getIconPath


class BridgeProvider(QgsProcessingProvider):

    BRIDGE_ACTIVE = 'BRIDGE_ACTIVE'

    def __init__(self):
        super().__init__()

    def id(self):
        return meta.PLUGIN_NAMESPACE

    def name(self):
        return self.tr(meta.getAppName())

    def icon(self):
        return QIcon(getIconPath("geocat"))

    def load(self):
        ProcessingConfig.settingIcons[self.name()] = self.icon()
        ProcessingConfig.addSetting(Setting(self.name(),
                                            self.BRIDGE_ACTIVE,
                                            self.tr('Activate'),
                                            False))
        ProcessingConfig.readSettings()
        self.refreshAlgorithms()
        return True

    def isActive(self):
        return ProcessingConfig.getSetting(self.BRIDGE_ACTIVE)

    def setActive(self, active):
        ProcessingConfig.setSettingValue(self.BRIDGE_ACTIVE, active)

    def supportsNonFileBasedOutput(self):
        return False

    def loadAlgorithms(self):
        for a in (PublishToGeonetworkAlgorithm(), PublishToGeoserverAlgorithm()):
            self.addAlgorithm(a)

    def tr(self, string, **kwargs):
        return QCoreApplication.translate(meta.getAppName(), string)
