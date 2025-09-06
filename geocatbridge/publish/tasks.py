import os
import sys
import traceback
from typing import Union, List

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import (
    QgsTask,
    QgsNativeMetadataValidator,
    QgsProject,
    QgsLayerMetadata,
    QgsBox3d,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem
)

from geocatbridge.publish import export
from geocatbridge.publish.export import GeoPackager
from geocatbridge.publish.metadata import uuidForLayer, saveMetadata
from geocatbridge.publish.style import saveLayerStyleAsZippedSld
from geocatbridge.servers.bases import DataCatalogServerBase, MetaCatalogServerBase
from geocatbridge.ui.progressdialog import DATA, METADATA, SYMBOLOGY, GROUPS
from geocatbridge.ui.publishreportdialog import PublishReportDialog
from geocatbridge.utils import feedback
from geocatbridge.utils import strings
from geocatbridge.utils.fields import fieldsForLayer, ShpFieldLookup, fieldNameEditor
from geocatbridge.utils.layers import BridgeLayer, layerById
from geocatbridge.utils.meta import getAppName


class TaskBase(QgsTask):
    stepFinished = pyqtSignal(str, int)
    stepStarted = pyqtSignal(str, int)
    stepSkipped = pyqtSignal(str, int)

    def __init__(self, layer_ids: List[str], field_map: dict):
        super().__init__(f'{getAppName()} publish/export task', QgsTask.Flag.CanCancel)
        self.layer_ids = layer_ids
        self.field_map = field_map

    def run(self):
        raise NotImplementedError


class PublishTask(TaskBase):

    def __init__(self, layer_ids: List[str], field_map: dict, only_symbology: bool,
                 geodata_server: DataCatalogServerBase, metadata_server: MetaCatalogServerBase, parent: QWidget):
        super().__init__(layer_ids, field_map)
        self._geopackager = GeoPackager(layer_ids, field_map)
        self.geodata_server = geodata_server
        self.metadata_server = metadata_server
        self.only_symbology = only_symbology
        self.results = {}
        self.exception = None
        self.exc_type = None
        self.parent = parent

    def run(self):
        """ Start the publish task. """

        def _publish(lyr: BridgeLayer, pub_fields: Union[list, ShpFieldLookup, None] = None):
            pub_fields = pub_fields.values() if isinstance(pub_fields, ShpFieldLookup) else pub_fields
            self.geodata_server.publishLayer(lyr, pub_fields)
            if not self.metadata_server:
                return
            metadata_uuid = uuidForLayer(lyr)
            md_url = self.metadata_server.metadataUrl(metadata_uuid)
            self.geodata_server.setLayerMetadataLink(layer.web_slug, md_url)

        try:
            validator = QgsNativeMetadataValidator()

            # TODO: remove or make configurable
            # DONOTALLOW = 0
            ALLOW = 1
            ALLOWONLYDATA = 2

            allow_without_md = ALLOW  # pluginSetting("allowWithoutMetadata")

            if self.geodata_server is not None:
                self.geodata_server.prepareForPublishing(self.only_symbology)

            self.results = {}
            published_ids = set()
            for i, layer_id in enumerate(self.layer_ids):
                if self.isCanceled():
                    return False
                warnings, errors = [], []
                self.setProgress(i * 100 / len(self.layer_ids))
                layer = layerById(layer_id)
                if not layer:
                    errors.append(f"Layer with ID {layer_id} is missing or no longer publishable")
                    continue
                name = layer.name()
                if not strings.validate(name, first_alpha=True):
                    try:
                        msg = f"Layer name '{name}' may cause issues"
                    except UnicodeError:
                        msg = "Layer name may cause issues"
                    msg += f" and has been published as '{layer.web_slug}': " \
                           f"preferably use ASCII characters only, start with a letter, " \
                           f"and follow with letters, numbers, or .-_"
                    warnings.append(msg)
                md_valid, _ = validator.validate(layer.metadata())
                if self.geodata_server is not None:
                    self.geodata_server.resetLogIssues()

                    publish_fields = fieldsForLayer(layer, self.field_map, self.geodata_server.vectorLayersAsShp())
                    with fieldNameEditor(layer, publish_fields):

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
                                if md_valid or (allow_without_md in (ALLOW, ALLOWONLYDATA)):
                                    _publish(layer, publish_fields)
                                    published_ids.add(layer_id)
                                else:
                                    errors.append(f"Could not publish layer '{name}' because of invalid metadata")
                            except:
                                errors.append(traceback.format_exc())
                            self.stepFinished.emit(layer_id, DATA)

                else:
                    # No geodata server selected: skip layer data and symbology
                    self.stepSkipped.emit(layer_id, SYMBOLOGY)
                    self.stepSkipped.emit(layer_id, DATA)

                if self.metadata_server is not None:
                    # User selected metadata server: publish metadata
                    self.stepStarted.emit(layer_id, METADATA)
                    try:
                        self.metadata_server.resetLogIssues()
                        if md_valid or (allow_without_md == ALLOW):
                            wms = None
                            wfs = None
                            full_name = None
                            if self.geodata_server is not None:
                                full_name = self.geodata_server.fullLayerName(layer.web_slug)
                                wms = self.geodata_server.getWmsUrl()
                                if layer.type() == layer.VectorLayer:
                                    wfs = self.geodata_server.getWfsUrl()
                            self.autofillMetadata(layer)
                            self.metadata_server.publishLayerMetadata(layer, wms, wfs, full_name)
                        else:
                            errors.append(f"Could not publish metadata of layer '{name}' because it is invalid")
                    except:
                        errors.append(traceback.format_exc())
                    self.stepFinished.emit(layer_id, METADATA)
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
            if published_ids and self.geodata_server is not None:
                self.stepStarted.emit(None, GROUPS)
                try:
                    self.geodata_server.createGroups(published_ids)
                except Exception as err:
                    # TODO: figure out where to properly put a warning or error message for this
                    feedback.logError(f"Could not create layer groups: {err}")
                finally:
                    try:
                        # Call closePublishing(): for GeoServer, this will set up vector tiles, if enabled
                        self.geodata_server.closePublishing(published_ids)
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
            dialog.exec()


class ExportTask(TaskBase, feedback.FeedbackMixin):

    def __init__(self, folder: str, layer_ids: List[str], field_map: dict,
                 export_data: bool, export_metadata: bool, export_symbology: bool):
        """
        Task to export layer data and styles to a given offline (local) folder.

        :param folder:              Folder path where the data should be written.
        :param layer_ids:           List of QGIS layer IDs to export.
        :param field_map:           Lookup dictionary with all field names to export for each layer.
        :param export_data:         Set to True if the layer source data should be exported (GeoPackage, GeoTIFF).
        :param export_metadata:     Set to True if the layer metadata should be exported (zipped MEF).
        :param export_symbology:    Set to True if the layer styles should be exported (zipped SLDs).
        """
        TaskBase.__init__(self, layer_ids, field_map)
        self.exception = None
        self.folder = folder
        self.export_data = export_data
        self.export_metadata = export_metadata
        self.export_symbology = export_symbology

    def run(self):
        """ Start the export task. """
        try:
            os.makedirs(self.folder, exist_ok=True)
            for i, id_ in enumerate(self.layer_ids):
                if self.isCanceled():
                    return False
                self.setProgress(i * 100 / len(self.layer_ids))
                layer = layerById(id_)
                if not layer:
                    continue
                if self.export_symbology:
                    style_filename = os.path.join(self.folder, layer.file_slug + "_style.zip")
                    self.stepStarted.emit(id_, SYMBOLOGY)
                    saveLayerStyleAsZippedSld(layer, style_filename)
                    self.stepFinished.emit(id_, SYMBOLOGY)
                else:
                    self.stepSkipped.emit(id_, SYMBOLOGY)
                if self.export_data:
                    self.stepStarted.emit(id_, DATA)
                    if layer.is_vector:
                        target_path = os.path.join(self.folder, 'vectordata' + export.EXT_GEOPACKAGE)
                        export.exportVector(layer, fieldsForLayer(layer, self.field_map), target_path=target_path)
                    elif layer.is_raster:
                        target_path = os.path.join(self.folder, layer.file_slug + export.EXT_GEOTIFF)
                        export.exportRaster(layer, target_path)
                    self.stepFinished.emit(id_, DATA)
                else:
                    self.stepSkipped.emit(id_, DATA)
                if self.export_metadata:
                    metadata_filename = os.path.join(self.folder, layer.file_slug + "_metadata.zip")
                    self.stepStarted.emit(id_, METADATA)
                    saveMetadata(layer, metadata_filename)
                    self.stepFinished.emit(id_, METADATA)
                else:
                    self.stepSkipped.emit(id_, METADATA)
        except Exception:
            self.exception = traceback.format_exc()
            return False
        return True
