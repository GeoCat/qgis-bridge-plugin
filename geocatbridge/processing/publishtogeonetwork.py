from qgis.core import (QgsProcessingParameterMapLayer,
                       QgsProcessingParameterString,
                       QgsProcessingParameterAuthConfig)

from geocatbridge.servers.models.geonetwork import GeonetworkServer
from geocatbridge.processing.bridgealgorithm import BridgeAlgorithm


class PublishToGeonetworkAlgorithm(BridgeAlgorithm):
    INPUT = 'INPUT'
    URL = 'URL'
    AUTHID = 'AUTHID'

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
        server.publishLayerMetadata(layer, None, None, None)

        return {}
