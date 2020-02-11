import os
import traceback
import string

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
    QgsCoordinateReferenceSystem,    
    QgsMessageLog,
    Qgis, 
)

from qgis.PyQt.QtCore import pyqtSignal

from geocatbridge.ui.publishreportdialog import PublishReportDialog
from geocatbridge.ui.progressdialog import DATA, METADATA, SYMBOLOGY, GROUPS

from bridgestyle.qgis import saveLayerStyleAsZippedSld

from .exporter import exportLayer

from .metadata import uuidForLayer, saveMetadata

class PublishTask(QgsTask):

    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

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
            children = layerTreeGroup.children()
            children.reverse()  # GS and QGIS have opposite ordering
            for child in children:
                if isinstance(child, QgsLayerTreeLayer):
                    name = child.layer().name() 
                    if name in toPublish:
                        layers.append(name)
                elif isinstance(child, QgsLayerTreeGroup):
                    subgroup = _addGroup(child)
                    if subgroup is not None:
                        layers.append(subgroup)
            if layers:
                return {"name": layerTreeGroup.name(),
                        "title": layerTreeGroup.customProperty("wmsTitle", layerTreeGroup.name()),
                        "abstract": layerTreeGroup.customProperty("wmsAbstract", layerTreeGroup.name()),
                        "layers": layers}
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
            for i, name in enumerate(self.layers):
                if self.isCanceled():
                    return False
                warnings, errors = [], []
                self.setProgress(i * 100 / len(self.layers))                
                layer = self.layerFromName(name)
                warnings.extend(self.validateLayer(layer))
                validates, _ = validator.validate(layer.metadata())
                validates = True
                if self.geodataServer is not None:
                    try:
                        self.geodataServer.resetLog()
                        self.stepStarted.emit(name, SYMBOLOGY)
                        self.geodataServer.publishStyle(layer)
                        self.stepFinished.emit(name, SYMBOLOGY)
                    except:
                        self.stepFinished.emit(name, SYMBOLOGY)
                        errors.append(traceback.format_exc())
                    try:
                        if self.onlySymbology:
                            self.stepSkipped.emit(name, DATA)
                        else:
                            self.stepStarted.emit(name, DATA)
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
                            self.stepFinished.emit(name, DATA)
                    except:
                        self.stepFinished.emit(name, DATA)
                        errors.append(traceback.format_exc())
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                    self.stepSkipped.emit(name, DATA)

                if self.metadataServer is not None:
                    try:
                        self.metadataServer.resetLog()
                        if validates or allowWithoutMetadata == ALLOW:
                            if self.geodataServer is not None:
                                wms = self.geodataServer.layerWmsUrl(layer.name())
                            else:
                                wms = None
                            self.autofillMetadata(layer)
                            self.stepStarted.emit(name, METADATA)
                            self.metadataServer.publishLayerMetadata(layer, wms)
                            self.stepFinished.emit(name, METADATA)
                        else:
                            self.metadataServer.logError(self.tr("Layer '%s' has invalid metadata. Metadata was not published") % layer.name())
                    except:                    
                        errors.append(traceback.format_exc())
                else:
                    self.stepSkipped.emit(name, METADATA)

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
                self.stepStarted.emit(None, GROUPS)
                groups = self._layerGroups(self.layers)                            
                try:
                    self.geodataServer.createGroups(groups)
                except:
                    #TODO: figure out where to put a warning or error message for this
                    pass
                finally:
                    self.geodataServer.closePublishing()
                    self.stepFinished.emit(None, GROUPS)
            else:
                self.stepSkipped.emit(None, GROUPS)

            return True
        except Exception as e:
            self.exception = traceback.format_exc()
            return False

    def validateLayer(self, layer):
        warnings = []
        name = layer.name()        
        correct = {c for c in string.ascii_letters + string.digits + "-_."}
        if not {c for c in name}.issubset(correct):                
            warnings.append("Layer name contain non-ascii characters that might cause issues")
        return warnings

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



class ExportTask(QgsTask):

    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

    def __init__(self, folder, layers, fields, exportData, exportMetadata, exportSymbology):
        super().__init__("Export from GeoCat Bridge", QgsTask.CanCancel)
        self.exception = None
        self.folder = folder
        self.layers = layers
        self.exportData = exportData
        self.exportMetadata = exportMetadata
        self.exportSymbology = exportSymbology
        self.fields = fields

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
            os.makedirs(self.folder, exist_ok=True)
            for i, name in enumerate(self.layers):
                if self.isCanceled():
                    return False
                self.setProgress(i * 100 / len(self.layers))                      
                layer = self.layerFromName(name)
                if self.exportSymbology:
                    styleFilename = os.path.join(self.folder, layer.name() + "_style.zip")                    
                    self.stepStarted.emit(name, SYMBOLOGY)
                    saveLayerStyleAsZippedSld(layer, styleFilename)                    
                    self.stepFinished.emit(name, SYMBOLOGY)
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                if self.exportData:
                    ext = ".gpkg" if layer.type() == layer.VectorLayer else ".tif"
                    layerFilename = os.path.join(self.folder, layer.name() + ext)
                    self.stepStarted.emit(name, DATA)
                    exportLayer(layer, self.fields, log=self, force=True, path=layerFilename)
                    self.stepFinished.emit(name, DATA)
                else:
                    self.stepSkipped.emit(name, DATA)
                if self.exportMetadata:
                    metadataFilename = os.path.join(self.folder, layer.name() + "_metadata.zip")
                    self.stepStarted.emit(name, METADATA)
                    saveMetadata(layer, metadataFilename)
                    self.stepFinished.emit(name, METADATA)
                else:
                    self.stepSkipped.emit(name, METADATA)

            return True
        except Exception as e:
            self.exception = traceback.format_exc()
            return False

    def logInfo(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)

    def logWarning(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
