import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingProvider
from processing.core.ProcessingConfig import ProcessingConfig, Setting

from . publishtogeonetwork import PublishToGeonetworkAlgorithm
from . publishtogeoserver import PublishToGeoserverAlgorithm

class BridgeProvider(QgsProcessingProvider):

    BRIDGE_ACTIVE = 'BRIDGE_ACTIVE'

    def __init__(self):
        super().__init__()
        self.algs = []

    def id(self):
        return 'geocatbridge'

    def name(self):
        return self.tr('GeoCat Bridge')

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons', 'geocat.png'))

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

    def getAlgs(self):
        algs = [PublishToGeonetworkAlgorithm(),
                PublishToGeoserverAlgorithm()
               ]

        return algs

    def loadAlgorithms(self):
        self.algs = self.getAlgs()
        for a in self.algs:
            self.addAlgorithm(a)

    def tr(self, string, context=''):
        if context == '':
            context = 'GeoCat Bridge'
        return QCoreApplication.translate(context, string)
