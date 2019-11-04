import traceback

from qgis.core import (
    QgsTask, 
    QgsLayerTreeLayer, 
    QgsLayerTreeGroup, 
    QgsNativeMetadataValidator, 
    QgsProject, 
    QgsMapLayer,
    QgsLayerMetadata,
    QgsBox3d,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem
)

from geocatbridge.ui.publishreportdialog import PublishReportDialog

from .metadata import uuidForLayer

class PublishTask(QgsTask):

    def __init__(self, layers, fields, onlySymbology, geodataServer, metadataServer, parent):
        super().__init__("Publish from GeoCat Bridge", QgsTask.CanCancel)
        self.exception = None
        self.layers = layers
        self.geodataServer = geodataServer
        self.metadataServer = metadataServer
        self.onlySymbology = onlySymbology
        self.fields = fields
        self.parent = parent

    def _layerGroups(self, toPublish):
        def _addGroup(layerTreeGroup):
            layers = []
            for child in layerTreeGroup.children():                    
                if isinstance(child, QgsLayerTreeLayer):
                    name = child.layer().name() 
                    if name in toPublish:
                        layers.append(name)
                elif isinstance(child, QgsLayerTreeGroup):
                    subgroup = _addGroup(child)
                    if subgroup is not None:
                        layers.append(subgroup)
            if layers:
                return {"name": layerTreeGroup.name(), "layers": layers}
            else:
                return None
        
        groups = []
        root = QgsProject.instance().layerTreeRoot()
        for element in root.children():
            if isinstance(element, QgsLayerTreeGroup):
                group = _addGroup(element)
                if group is not None:
                    groups.append(group)
                

        return groups

    def layerFromName(self, name):
        layers = self.publishableLayers()
        for layer in layers:
            if layer.name() == name:
                return layer

    def publishableLayers(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() 
                if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]]
        return layers

    def run(self):
        try:
            validator = QgsNativeMetadataValidator()        
            
            DONOTALLOW = 0
            ALLOW = 1
            ALLOWONLYDATA = 2
            
            allowWithoutMetadata = ALLOW #pluginSetting("allowWithoutMetadata")

            if self.geodataServer is not None:
                self.geodataServer.prepareForPublishing(self.onlySymbology)

            self.results = {}
            warnings, errors = [], []
            for i, name in enumerate(self.layers):
                if self.isCanceled():
                    return False
                self.setProgress(i * 100 / len(self.layers))
                try:                       
                    layer = self.layerFromName(name)
                    validates, _ = validator.validate(layer.metadata())
                    validates = True
                    if self.geodataServer is not None:
                        self.geodataServer.resetLog()
                        if self.onlySymbology:
                            self.geodataServer.publishStyle(layer)
                        else:
                            if validates or allowWithoutMetadata in [ALLOW, ALLOWONLYDATA]:
                                fields = None
                                if layer.type() == layer.VectorLayer:
                                    fields = [name for name, publish in self.fields[layer].items() if publish]                            
                                self.geodataServer.publishLayer(layer, fields)
                                if self.metadataServer is not None:
                                    metadataUuid = uuidForLayer(layer)
                                    url = self.metadataServer.metadataUrl(metadataUuid)
                                    self.geodataServer.setLayerMetadataLink(name, url)
                            else:
                                self.geodataServer.logError(self.tr("Layer '%s' has invalid metadata. Layer was not published") % layer.name())
                    if self.metadataServer is not None:
                        self.metadataServer.resetLog()
                        if validates or allowWithoutMetadata == ALLOW:
                            if self.geodataServer is not None:
                                wms = self.geodataServer.layerWmsUrl(layer.name())
                            else:
                                wms = None
                            self.autofillMetadata(layer)
                            self.metadataServer.publishLayerMetadata(layer, wms)
                        else:
                            self.metadataServer.logError(self.tr("Layer '%s' has invalid metadata. Metadata was not published") % layer.name())
                except:
                    errors.append(traceback.format_exc())
                if self.geodataServer is not None:
                    w, e = self.geodataServer.loggedInfo()
                    warnings.extend(w)
                    errors.extend(e)
                if self.metadataServer is not None:
                    w, e = self.metadataServer.loggedInfo()
                    warnings.extend(w)
                    errors.extend(e)
                self.results[name] = (set(warnings), set(errors))

            if self.geodataServer is not None:            
                groups = self._layerGroups(self.layers)                            
                self.geodataServer.createGroups(groups)
                self.geodataServer.closePublishing()

            return True
        except Exception as e:
            self.exception = traceback.format_exc()
            return False

    def autofillMetadata(self, layer):
        metadata = layer.metadata()
        if not (bool(metadata.title())):
            metadata.setTitle(layer.name())
        extents = metadata.extent().spatialExtents()        
        if not metadata.crs().isValid() or len(extents) == 0 or extents[0].bounds.width() == 0:
            epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
            metadata.setCrs(epsg4326)
            trans = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            layerExtent = trans.transform(layer.extent())
            box = QgsBox3d(layerExtent.xMinimum(), layerExtent.yMinimum(), 0, 
                            layerExtent.xMaximum(), layerExtent.yMaximum(), 0)
            extent = QgsLayerMetadata.SpatialExtent()
            extent.bounds = box
            extent.extentCrs = epsg4326
            metadata.extent().setSpatialExtents([extent])
        layer.setMetadata(metadata)

    def finished(self, result):      
        if result:
            dialog = PublishReportDialog(self.results, self.onlySymbology, 
                                        self.geodataServer, self.metadataServer,
                                        self.parent)
            dialog.exec_()



