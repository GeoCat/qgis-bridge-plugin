from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.PyQt.QtGui import QIcon

from geocatbridge.utils.files import getIconPath
from geocatbridge.utils import meta


class ProcessingLogger:
    def __init__(self, fb):
        self.fb = fb

    def logInfo(self, text):
        self.fb.pushInfo(text)

    def logWarning(self, text):
        self.fb.pushError(text)

    def logError(self, text):
        self.fb.pushError(text, fatalError=True)


class BridgeAlgorithm(QgisAlgorithm):

    def icon(self):
        return QIcon(getIconPath("geocat"))

    def group(self):
        return self.tr(meta.getAppName())

    def groupId(self):
        return meta.PLUGIN_NAMESPACE
