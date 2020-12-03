import os
import string
import sys
import traceback

from qgis.PyQt.QtCore import pyqtSignal
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

from bridgestyle.qgis import saveLayerStyleAsZippedSld
from geocatbridge.publish.exporter import exportLayer
from geocatbridge.publish.metadata import uuidForLayer, saveMetadata
from geocatbridge.ui.progressdialog import DATA, METADATA, SYMBOLOGY, GROUPS
from geocatbridge.ui.publishreportdialog import PublishReportDialog
from geocatbridge.utils.feedback import FeedbackMixin


class PublishTask(QgsTask):
    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

    def __init__(self, layers, fields, only_symbology, geodata_server, metadata_server, parent):
        super().__init__("Publish from GeoCat Bridge", QgsTask.CanCancel)
        self.results = {}
        self.exception = None
        self.exc_type = None
        self.layers = layers
        self.geodata_server = geodata_server
        self.metadata_server = metadata_server
        self.only_symbology = only_symbology
        self.fields = fields
        self.parent = parent

    @staticmethod
    def _layerGroups(to_publish):

        def _addGroup(layer_tree):
            layers = []
            children = layer_tree.children()
            children.reverse()  # GS and QGIS have opposite ordering
            for child in children:
                if isinstance(child, QgsLayerTreeLayer):
                    name = child.layer().name()
                    if name in to_publish:
                        layers.append(name)
                elif isinstance(child, QgsLayerTreeGroup):
                    subgroup = _addGroup(child)
                    if subgroup is not None:
                        layers.append(subgroup)
            if layers:
                return {"name": layer_tree.name(),
                        "title": layer_tree.customProperty("wmsTitle", layer_tree.name()),
                        "abstract": layer_tree.customProperty("wmsAbstract", layer_tree.name()),
                        "layers": layers}
            else:
                return None

        groups = []
        root = QgsProject().instance().layerTreeRoot()
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

    @staticmethod
    def publishableLayers():
        layers = [layer for layer in QgsProject().instance().mapLayers().values()
                  if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]]
        return layers

    def run(self):

        def publishLayer(lyr, lyr_name):
            fields = None
            if lyr.type() == lyr.VectorLayer:
                fields = [_name for _name, publish in self.fields[lyr].items() if publish]
            self.geodata_server.publishLayer(lyr, fields)
            if self.metadata_server is not None:
                metadata_uuid = uuidForLayer(lyr)
                md_url = self.metadata_server.metadataUrl(metadata_uuid)
                self.geodata_server.setLayerMetadataLink(lyr_name, md_url)

        try:
            validator = QgsNativeMetadataValidator()

            # DONOTALLOW = 0
            ALLOW = 1
            ALLOWONLYDATA = 2

            allow_without_md = ALLOW  # pluginSetting("allowWithoutMetadata")

            if self.geodata_server is not None:
                self.geodata_server.prepareForPublishing(self.only_symbology)

            qgs_layers = {}
            self.results = {}
            for i, name in enumerate(self.layers):
                if self.isCanceled():
                    return False
                warnings, errors = [], []
                self.setProgress(i * 100 / len(self.layers))
                layer = self.layerFromName(name)
                qgs_layers[name] = layer
                warnings.extend(self.validateLayer(layer))
                validates, _ = validator.validate(layer.metadata())
                validates = True
                if self.geodata_server is not None:
                    self.geodata_server.resetLog()

                    # Publish style
                    self.stepStarted.emit(name, SYMBOLOGY)
                    try:
                        self.geodata_server.publishStyle(layer)
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(name, SYMBOLOGY)

                    if self.only_symbology:
                        self.stepSkipped.emit(name, DATA)
                        return True

                    # Publish data
                    self.stepStarted.emit(name, DATA)
                    try:
                        if validates or allow_without_md in (ALLOW, ALLOWONLYDATA):
                            publishLayer(layer, name)
                        else:
                            self.stepStarted.emit(name, DATA)
                            if validates or allow_without_md in (ALLOW, ALLOWONLYDATA):
                                publishLayer(layer, name)
                            else:
                                self.geodata_server.logError(f"Layer '{layer.name()}' has invalid metadata. "
                                                             f"Layer was not published")
                            self.stepFinished.emit(name, DATA)
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(name, DATA)
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                    self.stepSkipped.emit(name, DATA)

                if self.metadata_server is not None:
                    try:
                        self.metadata_server.resetLog()
                        if validates or allow_without_md == ALLOW:
                            if self.geodata_server is not None:
                                full_name = self.geodata_server.fullLayerName(layer.name())
                                wms = self.geodata_server.layerWmsUrl()
                                if layer.type() == layer.VectorLayer:
                                    wfs = self.geodata_server.layerWfsUrl()
                                else:
                                    wfs = None
                            else:
                                wms = None
                                wfs = None
                                full_name = None
                            self.autofillMetadata(layer)
                            self.stepStarted.emit(name, METADATA)
                            self.metadata_server.publishLayerMetadata(layer, wms, wfs, full_name)
                            self.stepFinished.emit(name, METADATA)
                        else:
                            self.metadata_server.logError(f"Layer '{layer.name()}' has invalid metadata. "
                                                          f"Metadata was not published")
                    except:
                        errors.append(traceback.format_exc())
                else:
                    self.stepSkipped.emit(name, METADATA)

                if self.geodata_server is not None:
                    w, e = self.geodata_server.getLogIssues()
                    warnings.extend(w)
                    errors.extend(e)
                if self.metadata_server is not None:
                    w, e = self.metadata_server.getLogIssues()
                    warnings.extend(w)
                    errors.extend(e)
                self.results[name] = (set(warnings), set(errors))

            if self.geodata_server is not None:
                self.stepStarted.emit(None, GROUPS)
                groups = self._layerGroups(self.layers)
                try:
                    self.geodata_server.createGroups(groups, qgs_layers)
                except Exception:
                    # TODO: figure out where to put a warning or error message for this
                    pass
                finally:
                    self.stepFinished.emit(None, GROUPS)
            else:
                self.stepSkipped.emit(None, GROUPS)

            return True
        except Exception:
            self.exc_type, _, _ = sys.exc_info()
            self.exception = traceback.format_exc()
            return False

    @staticmethod
    def validateLayer(layer):
        warnings = []
        name = layer.name()
        correct = {c for c in string.ascii_letters + string.digits + "-_."}
        if not {c for c in name}.issubset(correct):
            warnings.append("Layer name contain non-ascii characters that might cause issues")
        return warnings

    @staticmethod
    def autofillMetadata(layer):
        metadata = layer.metadata()
        if not (bool(metadata.title())):
            metadata.setTitle(layer.name())
        extents = metadata.extent().spatialExtents()
        if not metadata.crs().isValid() or len(extents) == 0 or extents[0].bounds.width() == 0:
            epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
            metadata.setCrs(epsg4326)
            trans = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject().instance())
            layer_extent = trans.transform(layer.extent())
            box = QgsBox3d(layer_extent.xMinimum(), layer_extent.yMinimum(), 0,
                           layer_extent.xMaximum(), layer_extent.yMaximum(), 0)
            extent = QgsLayerMetadata.SpatialExtent()
            extent.bounds = box
            extent.extentCrs = epsg4326
            metadata.extent().setSpatialExtents([extent])
        layer.setMetadata(metadata)

    def finished(self, result):
        if result:
            dialog = PublishReportDialog(self.results, self.only_symbology,
                                         self.geodata_server, self.metadata_server,
                                         self.parent)
            dialog.exec_()


class ExportTask(FeedbackMixin, QgsTask):
    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

    def __init__(self, folder, layers, fields, export_data, export_metadata, export_symbology):
        super().__init__("Export from GeoCat Bridge", QgsTask.CanCancel)
        self.exception = None
        self.folder = folder
        self.layers = layers
        self.exportData = export_data
        self.exportMetadata = export_metadata
        self.exportSymbology = export_symbology
        self.fields = fields

    def layerFromName(self, name):
        layers = self.publishableLayers()
        for layer in layers:
            if layer.name() == name:
                return layer

    @staticmethod
    def publishableLayers():
        layers = [layer for layer in QgsProject().instance().mapLayers().values()
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
                    style_filename = os.path.join(self.folder, layer.name() + "_style.zip")
                    self.stepStarted.emit(name, SYMBOLOGY)
                    saveLayerStyleAsZippedSld(layer, style_filename)
                    self.stepFinished.emit(name, SYMBOLOGY)
                else:
                    self.stepSkipped.emit(name, SYMBOLOGY)
                if self.exportData:
                    ext = ".gpkg" if layer.type() == layer.VectorLayer else ".tif"
                    layer_filename = os.path.join(self.folder, layer.name() + ext)
                    self.stepStarted.emit(name, DATA)
                    exportLayer(layer, self.fields, path=layer_filename, force=True, logger=self)
                    self.stepFinished.emit(name, DATA)
                else:
                    self.stepSkipped.emit(name, DATA)
                if self.exportMetadata:
                    metadata_filename = os.path.join(self.folder, layer.name() + "_metadata.zip")
                    self.stepStarted.emit(name, METADATA)
                    saveMetadata(layer, metadata_filename)
                    self.stepFinished.emit(name, METADATA)
                else:
                    self.stepSkipped.emit(name, METADATA)

            return True
        except Exception:
            self.exception = traceback.format_exc()
            return False
