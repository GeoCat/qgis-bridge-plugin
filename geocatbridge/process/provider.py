from processing.core.ProcessingConfig import ProcessingConfig, Setting
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from geocatbridge.utils import meta, feedback
from geocatbridge.utils.files import getIconPath
from geocatbridge.process.algorithm import BridgeAlgorithm
from geocatbridge.servers.manager import getServerTypes


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
        try:
            ProcessingConfig.settingIcons[self.name()] = self.icon()
            ProcessingConfig.addSetting(Setting(self.name(),
                                                self.BRIDGE_ACTIVE,
                                                self.tr('Activate'),
                                                False))
            ProcessingConfig.readSettings()
            self.refreshAlgorithms()
        except Exception as err:
            feedback.logError(err)
            return False
        return True

    def isActive(self):
        return ProcessingConfig.getSetting(self.BRIDGE_ACTIVE)

    def setActive(self, active):
        ProcessingConfig.setSettingValue(self.BRIDGE_ACTIVE, active)

    def supportsNonFileBasedOutput(self):
        return False

    def loadAlgorithms(self):
        for server_type in getServerTypes():
            algorithm = server_type.getAlgorithmInstance()
            if not algorithm:
                # Server type does not provide processing algorithm
                continue
            if not isinstance(algorithm, BridgeAlgorithm):
                feedback.logError(f"Skipped algorithm returned by {server_type.__name__}: "
                                  f"instance does not inherit {BridgeAlgorithm.__name__}")
                continue
            self.addAlgorithm(algorithm)

    def tr(self, string, **kwargs):
        return QCoreApplication.translate(meta.getAppName(), string)
