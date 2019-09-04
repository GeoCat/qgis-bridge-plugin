import os

from qgis.PyQt.QtGui import QIcon

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm

from bridgecommon import log
from bridgecommon import feedback as bridgefeedback

class ProcessingLogger():
    def __init__(self, fb):
        self.fb = fb    

    def logInfo(self, text):
        self.fb.pushInfo(text)

    def logWarning(self, text):
        self.fb.pushError(text)

    def logError(self, text):
        self.fb.pushError(text, fatalError=True)
        

class BridgeAlgorithm(QgisAlgorithm):

    def __init__(self):
        super().__init__()
        self.fb = bridgefeedback.SilentFeedbackReporter()
        bridgefeedback.setFeedbackIndicator(self.fb)

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons', 'geocat.png'))   

    def group(self):
        return self.tr('Bridge')

    def groupId(self):
        return 'bridge'  

    def processAlgorithm(self, parameters, context, feedback):
        self.log = ProcessingLogger(feedback)
        log.setLogger(self.log) 