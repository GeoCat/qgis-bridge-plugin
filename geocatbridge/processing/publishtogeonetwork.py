import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsSettings,                       
                       QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterString,
                       QgsProcessingParameterAuthConfig)

from .bridgealgorithm import BridgeAlgorithm

from geocatbridge.publish.geonetwork import GeonetworkServer

class PublishToGeonetworkAlgorithm(BridgeAlgorithm):

    INPUT = 'INPUT'
    URL = 'URL'
    AUTHID = 'AUTHID'

    def group(self):
        return self.tr('Bridge')

    def groupId(self):
        return 'bridge'     

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer(self.INPUT,
                                                              self.tr('Layer')))

        self.addParameter(QgsProcessingParameterString(self.URL,
                                                       self.tr('Server_URL'), ''))
        self.addParameter(QgsProcessingParameterAuthConfig(self.AUTHID,
                                                       self.tr('Auth credentials')))
        
    def name(self):
        return 'publishtogeonetwork'

    def displayName(self):
        return self.tr('Publish layer metadata to GeoNetwork')

    def shortDescription(self):
        return self.tr('Publishes metadata to a GeoNetwork instance')

    def tags(self):
        return []

    def processAlgorithm(self, parameters, context, feedback):
        url = self.parameterAsString(parameters, self.URL, context)
        authid = self.parameterAsString(parameters, self.AUTHID, context)        
        layer = self.parameterAsLayer(parameters, self.INPUT, context)
        
        server = GeonetworkServer("server", url=url, authid=authid)
        server.publishLayerMetadata(layer, None)
        
        return {}

