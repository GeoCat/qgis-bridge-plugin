from qgis.core import (QgsProcessingParameterMapLayer,
                       QgsProcessingParameterString,
                       QgsProcessingParameterAuthConfig)

from geocatbridge.processing.bridgealgorithm import BridgeAlgorithm
from geocatbridge.servers.models.geoserver import GeoserverServer


class PublishToGeoserverAlgorithm(BridgeAlgorithm):

    INPUT = 'INPUT'
    URL = 'URL'
    WORKSPACE = 'WORKSPACE'
    AUTHID = 'AUTHID' 

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer(self.INPUT,
                                                              self.tr('Layer')))

        self.addParameter(QgsProcessingParameterString(self.URL,
                                                       self.tr('Server URL'), ''))
        self.addParameter(QgsProcessingParameterString(self.WORKSPACE,
                                                       self.tr('Workspace'), ''))
        self.addParameter(QgsProcessingParameterAuthConfig(self.AUTHID,
                                                       self.tr('Auth credentials')))
        
    def name(self):
        return 'publishtogeoserver'

    def displayName(self):
        return self.tr('Publish layer to GeoServer')

    def shortDescription(self):
        return self.tr('Publishes a layer and its style to a GeoServer instance')

    def tags(self):
        return []

    def processAlgorithm(self, parameters, context, feedback):
        url = self.parameterAsString(parameters, self.URL, context)
        authid = self.parameterAsString(parameters, self.AUTHID, context)
        workspace = self.parameterAsString(parameters, self.WORKSPACE, context)
        layer = self.parameterAsLayer(parameters, self.INPUT, context)
        
        server = GeoserverServer("server", url=url, authid=authid)
        server.forceWorkspace(workspace)
        server.publishStyle(layer)
        server.publishLayer(layer)
        
        return {}
