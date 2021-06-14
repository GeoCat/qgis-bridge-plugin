import os
import string
import sys
import traceback
from typing import Iterable

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import (
    QgsTask,
    QgsLayerTreeLayer,
    QgsLayerTreeGroup,
    QgsNativeMetadataValidator,
    QgsProject,
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
from geocatbridge.utils import feedback
from geocatbridge.utils import layers as lyr_utils
from geocatbridge.utils.meta import getAppName


class TaskBase(QgsTask):
    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

    def __init__(self, layer_ids: Iterable, field_map: dict):
        super().__init__(f'{getAppName()} publish/export task', QgsTask.CanCancel)
        self.layer_ids = frozenset(layer_ids)
        self.field_map = field_map


class PublishTask(TaskBase):

    def __init__(self, layer_ids, field_map, only_symbology, geodata_server, metadata_server, parent):
        super().__init__(layer_ids, field_map)
        self.geodata_server = geodata_server
        self.metadata_server = metadata_server
        self.only_symbology = only_symbology
        self.results = {}
        self.exception = None
        self.exc_type = None
        self.parent = parent

    def _layerGroups(self):

        def _addGroup(layer_tree):
            layers = []
            children = layer_tree.children()
            children.reverse()  # GS and QGIS have opposite ordering
            for child in children:
                if isinstance(child, QgsLayerTreeLayer):
                    child_layer = child.layer()
                    _, out_name = lyr_utils.getLayerTitleAndName(child_layer)
                    if child_layer.id() in self.layer_ids:
                        layers.append(out_name)
                elif isinstance(child, QgsLayerTreeGroup):
                    subgroup = _addGroup(child)
                    if subgroup is not None:
                        layers.append(subgroup)
            if layers:
                title, name = lyr_utils.getLayerTitleAndName(layer_tree)
                return {"name": name,
                        "title": layer_tree.customProperty("wmsTitle", title),
                        "abstract": layer_tree.customProperty("wmsAbstract", title),
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

    def run(self):

        def publishLayer(lyr, lyr_name):
            fields = None
            if lyr.type() == lyr.VectorLayer:
                fields = [_name for _name, publish in self.field_map[lyr.id()].items() if publish]
            self.geodata_server.publishLayer(lyr, fields)
            if self.metadata_server is not None:
                metadata_uuid = uuidForLayer(lyr)
                md_url = self.metadata_server.metadataUrl(metadata_uuid)
                self.geodata_server.setLayerMetadataLink(lyr_name, md_url)

        try:
            validator = QgsNativeMetadataValidator()

            # FIXME: remove or improve this
            # DONOTALLOW = 0
            ALLOW = 1
            ALLOWONLYDATA = 2

            allow_without_md = ALLOW  # pluginSetting("allowWithoutMetadata")

            if self.geodata_server is not None:
                self.geodata_server.prepareForPublishing(self.only_symbology)

            self.results = {}
            for i, layer_id in enumerate(self.layer_ids):
                if self.isCanceled():
                    return False
                warnings, errors = [], []
                self.setProgress(i * 100 / len(self.layer_ids))
                layer = lyr_utils.getLayerById(layer_id)
                name, safe_name = lyr_utils.getLayerTitleAndName(layer)
                if not lyr_utils.hasValidLayerName(layer):
                    try:
                        warnings.append(f"Layer name '{name}' contains characters that may cause issues")
                    except UnicodeError:
                        warnings.append("Layer name contains characters that may cause issues")
                md_valid, _ = validator.validate(layer.metadata())
                if self.geodata_server is not None:
                    self.geodata_server.resetLogIssues()

                    # Publish style
                    self.stepStarted.emit(layer_id, SYMBOLOGY)
                    try:
                        self.geodata_server.publishStyle(layer)
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(layer_id, SYMBOLOGY)

                    if self.only_symbology:
                        # Skip data publish if "only symbology" was checked
                        self.stepSkipped.emit(layer_id, DATA)
                    else:
                        # Publish data
                        self.stepStarted.emit(layer_id, DATA)
                        try:
                            if md_valid or allow_without_md in (ALLOW, ALLOWONLYDATA):
                                publishLayer(layer, safe_name)
                            else:
                                self.stepStarted.emit(layer_id, DATA)
                                if md_valid or allow_without_md in (ALLOW, ALLOWONLYDATA):
                                    publishLayer(layer, safe_name)
                                else:
                                    self.geodata_server.logError(f"Layer '{name}' has invalid metadata. "
                                                                 f"Layer was not published")
                                self.stepFinished.emit(layer_id, DATA)
                        except:
                            errors.append(traceback.format_exc())
                        self.stepFinished.emit(layer_id, DATA)

                else:
                    # No geodata server selected: skip layer data and symbology
                    self.stepSkipped.emit(layer_id, SYMBOLOGY)
                    self.stepSkipped.emit(layer_id, DATA)

                if self.metadata_server is not None:
                    # User selected metadata server: publish metadata
                    try:
                        self.metadata_server.resetLogIssues()
                        if md_valid or allow_without_md == ALLOW:
                            wms = None
                            wfs = None
                            full_name = None
                            if self.geodata_server is not None:
                                full_name = self.geodata_server.fullLayerName(safe_name)
                                wms = self.geodata_server.getWmsUrl()
                                if layer.type() == layer.VectorLayer:
                                    wfs = self.geodata_server.getWfsUrl()
                            self.autofillMetadata(layer)
                            self.stepStarted.emit(layer_id, METADATA)
                            self.metadata_server.publishLayerMetadata(layer, wms, wfs, full_name)
                            self.stepFinished.emit(layer_id, METADATA)
                        else:
                            self.metadata_server.logError(f"Layer '{name}' has invalid metadata. "
                                                          f"Metadata was not published")
                    except:
                        errors.append(traceback.format_exc())
                else:
                    self.stepSkipped.emit(layer_id, METADATA)

                # Collect all layer-specific errors and warnings (if any)
                if self.geodata_server is not None:
                    w, e = self.geodata_server.getLogIssues()
                    warnings.extend(w)
                    errors.extend(e)
                if self.metadata_server is not None:
                    w, e = self.metadata_server.getLogIssues()
                    warnings.extend(w)
                    errors.extend(e)
                self.results[name] = (set(warnings), set(errors))

            # Create layer groups (if any)
            if self.geodata_server is not None:
                self.stepStarted.emit(None, GROUPS)
                try:
                    # FIXME (did this ever work?)
                    self.geodata_server.createGroups(self._layerGroups(), self.layer_ids)
                except Exception as err:
                    # TODO: figure out where to properly put a warning or error message for this
                    feedback.logError(f"Could not create layer groups: {err}")
                finally:
                    try:
                        # Call closePublishing(): for GeoServer, this will set up vector tiles, if enabled
                        self.geodata_server.closePublishing()
                    except Exception as err:
                        feedback.logError(f"Failed to finalize publish task: {err}")
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

    def finished(self, success: bool):
        if success:
            dialog = PublishReportDialog(self.results, self.only_symbology,
                                         self.geodata_server, self.metadata_server,
                                         self.parent)
            dialog.exec_()


class ExportTask(TaskBase, feedback.FeedbackMixin):

    def __init__(self, folder, layer_ids, field_map, export_data, export_metadata, export_symbology):
        TaskBase.__init__(self, layer_ids, field_map)
        self.exception = None
        self.folder = folder
        self.export_data = export_data
        self.export_metadata = export_metadata
        self.export_symbology = export_symbology

    def run(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
            for i, id_ in enumerate(self.layer_ids):
                if self.isCanceled():
                    return False
                self.setProgress(i * 100 / len(self.layer_ids))
                layer = self.getLayerById(id_)
                name, safe_name = lyr_utils.getLayerTitleAndName(layer)
                if self.export_symbology:
                    style_filename = os.path.join(self.folder, safe_name + "_style.zip")
                    self.stepStarted.emit(id_, SYMBOLOGY)
                    saveLayerStyleAsZippedSld(layer, style_filename)
                    self.stepFinished.emit(id_, SYMBOLOGY)
                else:
                    self.stepSkipped.emit(id_, SYMBOLOGY)
                if self.export_data:
                    ext = ".gpkg" if layer.type() == layer.VectorLayer else ".tif"
                    layer_filename = os.path.join(self.folder, safe_name + ext)
                    self.stepStarted.emit(id_, DATA)
                    exportLayer(layer, self.field_map[id_], path=layer_filename, force=True, logger=self)
                    self.stepFinished.emit(id_, DATA)
                else:
                    self.stepSkipped.emit(id_, DATA)
                if self.export_metadata:
                    metadata_filename = os.path.join(self.folder, safe_name + "_metadata.zip")
                    self.stepStarted.emit(id_, METADATA)
                    saveMetadata(layer, metadata_filename)
                    self.stepFinished.emit(id_, METADATA)
                else:
                    self.stepSkipped.emit(id_, METADATA)

            return True
        except Exception:
            self.exception = traceback.format_exc()
            return False
