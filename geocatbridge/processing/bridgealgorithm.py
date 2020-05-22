import os

from qgis.PyQt.QtGui import QIcon

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm

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

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons', 'geocat.png'))   

    def group(self):
        return self.tr('Bridge')

    def groupId(self):
        return 'bridge'  