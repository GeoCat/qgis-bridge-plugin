import os
import sys
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
    QgsCoordinateReferenceSystem,    
    QgsMessageLog,
    Qgis
)

from qgis.PyQt.QtCore import pyqtSignal

from geocatbridge.ui.publishreportdialog import PublishReportDialog
from geocatbridge.ui.progressdialog import DATA, METADATA, SYMBOLOGY, GROUPS

from bridgestyle.qgis import saveLayerStyleAsZippedSld

from .exporter import exportLayer

from .metadata import uuidForLayer, saveMetadata
from ..utils import layers as layerUtils


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
                    in_name, out_name = layerUtils.getLayerTitleAndName(child.layer())
                    if in_name in toPublish:
                        layers.append(out_name)
                elif isinstance(child, QgsLayerTreeGroup):
                    subgroup = _addGroup(child)
                    if subgroup is not None:
                        layers.append(subgroup)
            if layers:
                title, name = layerUtils.getLayerTitleAndName(layerTreeGroup)
                return {"name": name,
                        "title": layerTreeGroup.customProperty("wmsTitle", title),
                        "abstract": layerTreeGroup.customProperty("wmsAbstract", title),
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

            allowWithoutMetadata = ALLOW  # pluginSetting("allowWithoutMetadata")

            if self.geodataServer is not None:
                self.geodataServer.prepareForPublishing(self.onlySymbology)

            self.results = {}
            qgs_layers = {}
            for i, name in enumerate(self.layers):
                if self.isCanceled():
                    return False
                warnings, errors = [], []
                self.setProgress(i * 100 / len(self.layers))
                layer = self.layerFromName(name)
                qgs_layers[name] = layer
                _, safe_name = layerUtils.getLayerTitleAndName(layer)
                if not layerUtils.hasValidLayerName(layer):
                    try:
                        warnings.append("Layer name '%s' contains characters that might cause issues" % name)
                    except UnicodeError:
                        warnings.append("Layer name contains characters that might cause issues")
                validates, _ = validator.validate(layer.metadata())
                validates = True
                if self.geodataServer is not None:
                    self.geodataServer.resetLog()

                    # Publish style
                    self.stepStarted.emit(name, SYMBOLOGY)
                    try:
                        self.geodataServer.publishStyle(layer)
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(name, SYMBOLOGY)

                    if self.onlySymbology:
                        self.stepSkipped.emit(name, DATA)
                        continue

                    # Publish data
                    self.stepStarted.emit(name, DATA)
                    try:
                        if validates or allowWithoutMetadata in [ALLOW, ALLOWONLYDATA]:
                            fields = None
                            if layer.type() == layer.VectorLayer:
                                fields = [fname for fname, publish in self.fields[layer].items() if publish]
                            self.geodataServer.publishLayer(layer, fields)
                            if self.metadataServer is not None:
                                metadataUuid = uuidForLayer(layer)
                                url = self.metadataServer.metadataUrl(metadataUuid)
                                self.geodataServer.setLayerMetadataLink(safe_name, url)
                        else:
                            self.stepStarted.emit(name, DATA)
                            if validates or allowWithoutMetadata in [ALLOW, ALLOWONLYDATA]:
                                fields = None
                                if layer.type() == layer.VectorLayer:
                                    fields = [fname for fname, publish in self.fields[layer].items() if publish]
                                self.geodataServer.publishLayer(layer, fields)
                                if self.metadataServer is not None:
                                    metadataUuid = uuidForLayer(layer)
                                    url = self.metadataServer.metadataUrl(metadataUuid)
                                    self.geodataServer.setLayerMetadataLink(safe_name, url)
                            else:
                                self.geodataServer.logError(
                                    self.tr("Layer '%s' has invalid metadata. Layer was not published") % name)
                            self.stepFinished.emit(name, DATA)
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(name, DATA)
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                    self.stepSkipped.emit(name, DATA)

                if self.metadataServer is not None:
                    try:
                        self.metadataServer.resetLog()
                        if validates or allowWithoutMetadata == ALLOW:
                            wms = None
                            wfs = None
                            full_name = None
                            if self.geodataServer is not None:
                                full_name = self.geodataServer.fullLayerName(safe_name)
                                wms = self.geodataServer.layerWmsUrl()
                                if layer.type() == layer.VectorLayer:
                                    wfs = self.geodataServer.layerWfsUrl()
                            self.autofillMetadata(layer)
                            self.stepStarted.emit(name, METADATA)
                            self.metadataServer.publishLayerMetadata(layer, wms, wfs, full_name)
                            self.stepFinished.emit(name, METADATA)
                        else:
                            self.metadataServer.logError(
                                self.tr("Layer '%s' has invalid metadata. Metadata was not published") % name)
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
                    self.geodataServer.createGroups(groups, qgs_layers)
                except:
                    # TODO: figure out where to put a warning or error message for this
                    pass
                finally:
                    self.stepFinished.emit(None, GROUPS)
            else:
                self.stepSkipped.emit(None, GROUPS)

            return True
        except Exception:
            self.exceptiontype, _, _ = sys.exc_info()
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
                _, safe_name = layerUtils.getLayerTitleAndName(layer)
                if self.exportSymbology:
                    styleFilename = os.path.join(self.folder, safe_name + "_style.zip")
                    self.stepStarted.emit(name, SYMBOLOGY)
                    saveLayerStyleAsZippedSld(layer, styleFilename)
                    self.stepFinished.emit(name, SYMBOLOGY)
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                if self.exportData:
                    ext = ".gpkg" if layer.type() == layer.VectorLayer else ".tif"
                    layerFilename = os.path.join(self.folder, safe_name + ext)
                    self.stepStarted.emit(name, DATA)
                    exportLayer(layer, self.fields, log=self, force=True, path=layerFilename)
                    self.stepFinished.emit(name, DATA)
                else:
                    self.stepSkipped.emit(name, DATA)
                if self.exportMetadata:
                    metadataFilename = os.path.join(self.folder, safe_name + "_metadata.zip")
                    self.stepStarted.emit(name, METADATA)
                    saveMetadata(layer, metadataFilename)
                    self.stepFinished.emit(name, METADATA)
                else:
                    self.stepSkipped.emit(name, METADATA)

            return True
        except Exception:
            self.exception = traceback.format_exc()
            return False

    def logInfo(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)

    def logWarning(self, text):
        QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
