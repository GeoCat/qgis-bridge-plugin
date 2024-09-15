from qgis.core import QgsProcessingAlgorithm

from geocatbridge.utils import meta
from geocatbridge.utils.gui import getSvgIcon
from geocatbridge.utils.feedback import translate


class BridgeAlgorithm(QgsProcessingAlgorithm):

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()
        self.tr = translate

    def initAlgorithm(self, config=None):  # noqa
        super().initAlgorithm(config)

    def createInstance(self):
        return type(self)()

    def icon(self):
        return getSvgIcon("geocat_icon")

    def group(self):
        return self.tr("Publish tools")

    def groupId(self):
        return meta.PLUGIN_NAMESPACE

    def tags(self):
        return []
