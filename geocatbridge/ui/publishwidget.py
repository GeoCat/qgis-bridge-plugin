import json
import webbrowser
from collections import Counter
from functools import partial
from typing import FrozenSet, Optional

import requests
from qgis.PyQt.QtCore import (
    Qt,
    QCoreApplication,
    QSettings,
    QPoint
)
from qgis.PyQt.QtGui import (
    QPixmap,
    QShowEvent
)
from qgis.PyQt.QtWidgets import (
    QLabel,
    QMenu,
    QWidget,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTableWidgetItem,
    QFileDialog
)
from qgis.core import (
    QgsCoordinateTransform,
    QgsNativeMetadataValidator,
    QgsProject,
    QgsApplication,
    QgsRectangle
)
from qgis.utils import iface

from geocatbridge.publish.metadata import uuidForLayer, loadMetadataFromXml, MetadataDependencyError
from geocatbridge.publish.tasks import PublishTask, ExportTask
from geocatbridge.servers import manager
from geocatbridge.ui.metadatadialog import MetadataDialog
from geocatbridge.ui.progressdialog import ProgressDialog
from geocatbridge.utils import files, gui, meta, l10n
from geocatbridge.utils.feedback import FeedbackMixin
from geocatbridge.utils.layers import (
    BridgeLayer, listBridgeLayers, layerById, listLayerNames, listGroupNames
)

# QGIS setting that stores the online/offline publish settings
PUBLISH_SETTING = f"{meta.PLUGIN_NAMESPACE}/BridgePublish"

# Icons
SELECT_ICON = gui.getSvgIcon("select")
DESELECT_ICON = gui.getSvgIcon("deselect")
PUBLISHED_ICON = gui.getSvgIcon("published")
VALIDATE_ICON = gui.getSvgIcon("validate")
PREVIEW_ICON = gui.getSvgIcon("preview")
IMPORT_ICON = gui.getSvgIcon("import")

IDENTIFICATION, CATEGORIES, KEYWORDS, ACCESS, EXTENT, CONTACT = range(6)

WIDGET, BASE = gui.loadUiType(__file__)


class PublishWidget(FeedbackMixin, BASE, WIDGET):
    listLayers: QListWidget
    publishableLayers: list[BridgeLayer]
    statusWorker: Optional[gui.BackgroundWorker]
    statusThread: Optional[gui.QtCore.QThread]

    def __init__(self, parent):
        super().__init__(parent)
        self.currentRow = None
        self.currentLayer = None
        self.parent = parent

        self.statusWorker = None
        self.statusThread = None

        # Keep track of publishable fields for each layer
        self.fieldsToPublish = {}

        # Keep track if metadata or geodata for a layer has been published
        self.isMetadataPublished = {}
        self.isDataPublished = {}

        # Initialize the list of publishable layers
        self.publishableLayers = []

        # Default "not set" values for comboboxes
        self.COMBO_NOTSET_LANG = self.translate("Not specified")
        self.COMBO_NOTSET_DATA = self.translate("Do not publish data")
        self.COMBO_NOTSET_META = self.translate("Do not publish metadata")

        # Initialize the UI and populate with data
        self._setupUi()

    def _setupUi(self):
        self.setupUi(self)
        self.populateComboBoxes(True)

        # Set up signals and slots
        self.btnAccessConstraints.clicked.connect(partial(self.openMetadataEditor, ACCESS))
        self.btnClose.clicked.connect(self.parent.close)
        self.btnDataContact.clicked.connect(partial(self.openMetadataEditor, CONTACT))
        self.btnExportFolder.clicked.connect(self.selectExportFolder)
        self.btnImport.clicked.connect(self.importMetadata)
        self.btnImport.setIcon(IMPORT_ICON)
        self.btnIsoTopic.clicked.connect(partial(self.openMetadataEditor, CATEGORIES))
        self.btnKeywords.clicked.connect(partial(self.openMetadataEditor, KEYWORDS))
        self.btnMetadataContact.clicked.connect(partial(self.openMetadataEditor, CONTACT))
        self.btnOpenQgisMetadataEditor.clicked.connect(self.openMetadataEditor)
        self.btnOpenQgisMetadataEditor.setIcon(QgsApplication.getThemeIcon("../../icons/qgis_icon.svg"))  # noqa
        self.btnPreview.clicked.connect(self.previewMetadata)
        self.btnPreview.setIcon(PREVIEW_ICON)
        self.btnPublish.clicked.connect(self.publish)
        self.btnRemoveAll.clicked.connect(self.unpublishAll)
        self.btnSelectAll.clicked.connect(partial(self.toggleLayers, True))
        self.btnSelectAll.setIcon(SELECT_ICON)
        self.btnSelectAll.setToolTip(self.tr("Select all layers"))
        self.btnSelectNone.clicked.connect(partial(self.toggleLayers, False))
        self.btnSelectNone.setIcon(DESELECT_ICON)
        self.btnSelectNone.setToolTip(self.tr("Deselect all layers"))
        self.btnUseConstraints.clicked.connect(partial(self.openMetadataEditor, ACCESS))
        self.btnValidate.clicked.connect(self.validateMetadata)
        self.btnValidate.setIcon(VALIDATE_ICON)
        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)
        self.listLayers.currentRowChanged.connect(self.currentRowChanged)
        self.listLayers.customContextMenuRequested.connect(self.showContextMenu)
        self.listLayers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabOnOffline.currentChanged.connect(partial(self.tabOnOfflineChanged))
        self.txtExportFolder.textChanged.connect(self.exportFolderChanged)

        self.toggleLayerElements()
        self.toggleUpdateProgress(False)

    def toggleLayerElements(self):
        """ Toggles the visibility of UI elements based on the layer widget content. """

        if self.listLayers.count():
            if self.listLayers.currentRow() < 0:
                # Select the first layer item by default (if nothing is selected yet)
                self.listLayers.setCurrentRow(0)
            self.txtNoLayers.setVisible(False)
            self.listLayers.setVisible(True)
            self.btnRemoveAll.setVisible(True)
            self.btnSelectAll.setEnabled(True)
            self.btnSelectNone.setEnabled(True)
        else:
            self.txtNoLayers.setVisible(True)
            self.listLayers.setVisible(False)
            self.btnRemoveAll.setVisible(False)
            self.btnSelectAll.setEnabled(False)
            self.btnSelectNone.setEnabled(False)

    def toggleUpdateProgress(self, show: bool, max_value: int = 0):
        """ Toggles the visibility of the layer status update progress bar (and resets it). """
        self.progressBar.value = 0
        if max_value:
            self.progressBar.setMaximum(max_value)
        self.progressBar.setVisible(show)

    def restoreConfig(self):
        """ Sets online and offline publish settings from QGIS Bridge configuration. """

        # Read QGIS setting
        config_str = QSettings().value(PUBLISH_SETTING)
        if not config_str:
            self.logInfo(f"Could not find existing {meta.getAppName()} setting '{PUBLISH_SETTING}'")
            return

        # Parse JSON object from settings string
        try:
            settings = json.loads(config_str)
            if not isinstance(settings, dict):
                # Settings have become corrupt (usually because user edited QGIS advanced settings):
                # reset to empty dict in this case
                self.logError(f"Publish settings corrupt: must be a dict, not {type(settings)}")
                QSettings().setValue(PUBLISH_SETTING, '{}')
                return
        except json.JSONDecodeError as e:
            self.logError(f"Failed to parse publish settings: {e}")
            return

        # Set online settings
        online_settings = settings.get('online', {})
        geodata_server = online_settings.get('geodataServer')
        if geodata_server and geodata_server in manager.getGeodataServerNames():
            self.comboGeodataServer.setCurrentText(geodata_server)
        metadata_server = online_settings.get('metadataServer')
        if metadata_server and metadata_server in manager.getMetadataServerNames():
            self.comboMetadataServer.setCurrentText(metadata_server)
        style_only = online_settings.get('symbologyOnly', False)
        self.chkOnlySymbology.setCheckState(Qt.CheckState.Checked if style_only else Qt.CheckState.Unchecked)

        # Set offline settings
        offline_settings = settings.get('offline', {})
        self.chkExportGeodata.setCheckState(Qt.CheckState.Checked if offline_settings.get('exportGeodata') else Qt.CheckState.Unchecked)
        self.chkExportMetadata.setCheckState(Qt.CheckState.Checked if offline_settings.get('exportMetadata') else Qt.CheckState.Unchecked)
        self.chkExportSymbology.setCheckState(Qt.CheckState.Checked if offline_settings.get('exportSymbology') else Qt.CheckState.Unchecked)
        folder = offline_settings.get('exportFolder') or ''
        self.txtExportFolder.setText(folder)

        # Set active tab (making sure the tab index is not out of bounds)
        tab_index = min(max(0, settings.get('currentTab', 0)), self.tabOnOffline.count() - 1)
        self.tabOnOffline.setCurrentIndex(tab_index)

    def saveConfig(self):
        """ Collects current publish settings and persists them as QGIS Bridge configuration. """

        # Create JSON object
        geodata_server = self.comboGeodataServer.currentText()
        metadata_server = self.comboMetadataServer.currentText()
        settings = {
            'online': {
                'geodataServer': geodata_server if geodata_server != self.COMBO_NOTSET_DATA else None,
                'metadataServer': metadata_server if metadata_server != self.COMBO_NOTSET_META else None,
                'symbologyOnly': self.chkOnlySymbology.isChecked()
            },
            'offline': {
                'exportFolder': self.txtExportFolder.text().strip(),
                'exportGeodata': self.chkExportGeodata.isChecked(),
                'exportMetadata': self.chkExportMetadata.isChecked(),
                'exportSymbology': self.chkExportSymbology.isChecked()
            },
            'currentTab': min(max(0, self.tabOnOffline.currentIndex()), self.tabOnOffline.count() - 1)
        }

        # Serialize as JSON and save string
        try:
            config_str = json.dumps(settings)
        except TypeError as e:
            self.logError(f"Failed to serialize publish settings as JSON: {e}")
            return
        QSettings().setValue(PUBLISH_SETTING, config_str)

    def tabOnOfflineChanged(self, tab_index: int):
        """ Refreshes the layer publication status. """
        if tab_index < 0:
            return
        self.updateOnlineLayerStatus()

    def selectExportFolder(self):
        folder = QFileDialog.getExistingDirectory(self, self.translate("Export to folder"))  # noqa
        if folder:
            self.txtExportFolder.setText(folder)

    def geodataServerChanged(self):
        self.updateOnlineLayerStatus(True, False)

    def metadataServerChanged(self, update_status: bool = True):
        if update_status:
            self.updateOnlineLayerStatus(False, True)
        md_combo = self.comboMetadataServer.currentText()
        profile = 0
        if md_combo and md_combo != self.COMBO_NOTSET_META:
            profile = manager.getMetadataProfile(self.comboMetadataServer.currentText())
        num_tabs = self.tabWidgetMetadata.count()
        if profile == 0:  # Default profile should be equal to 0
            if num_tabs > 1:
                for i in range(num_tabs - 1, 0, -1):
                    self.tabWidgetMetadata.removeTab(i)
            return
        # TODO: implement other profile tabs
        if num_tabs == 1:
            self.tabWidgetMetadata.addTab(self.tabInspire, profile)
            self.tabWidgetMetadata.addTab(self.tabTemporal, self.translate("Temporal"))

    def toggleLayers(self, state: bool):
        """ Toggles the checkbox state of all layer items. """
        for i in range(self.listLayers.count()):
            widget = self.getPublishWidget(i)
            widget.setCheckbox(state)

    def currentRowChanged(self, current_row: int):
        """ Called whenever the user selects another layer item. """
        if self.currentRow == current_row:
            return
        self.currentRow = current_row
        self.storeFieldsToPublish()
        self.storeMetadata()
        layer = self.publishableLayers[current_row]
        self.currentLayer = layer
        self.populateLayerMetadata()
        self.populateLayerFields()
        if layer.type() != layer.VectorLayer:
            self.tabLayerInfo.setCurrentWidget(self.tabMetadata)

    def populateLayerMetadata(self):
        if not self.currentLayer:
            return
        metadata = self.currentLayer.metadata()
        self.txtMetadataTitle.setText(metadata.title())
        self.txtAbstract.setPlainText(metadata.abstract())
        iso_topics = ",".join(t for t in metadata.keywords().get("gmd:topicCategory", []) if t)
        self.txtIsoTopic.setText(iso_topics)
        keywords = []
        for group in metadata.keywords().values():
            keywords.extend(group)
        self.txtKeywords.setText(",".join(k for k in keywords if k))
        contacts = metadata.contacts()
        if contacts:
            self.txtDataContact.setText(contacts[0].name)
            self.txtMetadataContact.setText(contacts[0].name)
        self.txtUseConstraints.setText(metadata.fees())
        licenses = metadata.licenses()
        if licenses:
            self.txtAccessConstraints.setText(licenses[0])
        else:
            self.txtAccessConstraints.setText("")
        lang = l10n.code2label.get(metadata.language(), self.COMBO_NOTSET_LANG)
        self.comboLanguage.setCurrentText(lang)
        # TODO: Use default values if no values in QGIS metadata object

    def populateLayerFields(self):
        if not self.currentLayer:
            return
        if self.currentLayer.type() == self.currentLayer.VectorLayer:
            fields = [f.name() for f in self.currentLayer.fields()]
            self.tabLayerInfo.setTabEnabled(1, True)
            self.tableFields.setRowCount(len(fields))
            for i, field in enumerate(fields):
                item = QTableWidgetItem()
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # noqa
                check = Qt.CheckState.Checked if self.fieldsToPublish[self.currentLayer.id()][field] else Qt.CheckState.Unchecked
                item.setCheckState(check)
                self.tableFields.setItem(i, 0, item)
                item = QTableWidgetItem(field)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # noqa
                self.tableFields.setItem(i, 1, item)
        else:
            self.tabLayerInfo.setTabEnabled(1, False)

    def storeMetadata(self):
        if not self.currentLayer:
            return
        metadata = self.currentLayer.metadata().clone()
        metadata.setTitle(self.txtMetadataTitle.text())
        metadata.setAbstract(self.txtAbstract.toPlainText())
        lang = l10n.label2code.get(self.comboLanguage.currentText())
        if lang:
            metadata.setLanguage(lang)
        self.currentLayer.setMetadata(metadata)

    def storeFieldsToPublish(self):
        if not self.currentLayer or self.currentLayer.type() != self.currentLayer.VectorLayer:
            return
        pub_fields = {}
        fields = self.currentLayer.fields()
        for i in range(fields.count()):
            check = self.tableFields.item(i, 0)
            name = self.tableFields.item(i, 1)
            pub_fields[name.text()] = check.checkState() == Qt.CheckState.Checked
        self.fieldsToPublish[self.currentLayer.id()] = pub_fields

    def showContextMenu(self, pos: QPoint):
        """ Provides a context menu for published layers. """
        item = self.listLayers.itemAt(pos)
        if item is None:
            return
        widget = self.listLayers.itemWidget(item)
        if not isinstance(widget, LayerItemWidget):
            return
        layer_id = widget.id
        menu = QMenu()
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if any(self.isDataPublished.values()):
            menu.addAction(self.translate("View all WMS layers"), self.viewAllWms)
        if self.isDataPublished.get(layer_id):
            menu.addAction(self.translate("View this WMS layer"), partial(self.viewWms, layer_id))
            menu.addAction(self.translate("Unpublish geodata"), partial(self.unpublishData, layer_id))
        if self.isMetadataPublished.get(layer_id):
            menu.addAction(self.translate("View metadata record"), partial(self.viewMetadata, layer_id))
            menu.addAction(self.translate("Unpublish metadata"), partial(self.unpublishMetadata, layer_id))
        menu.exec(self.listLayers.mapToGlobal(pos))

    def populateLayerWidget(self):
        for i, layer in enumerate(self.publishableLayers):
            fields = [f.name() for f in layer.fields()] if (hasattr(layer, 'fields') and layer.is_vector) else []
            self.fieldsToPublish[layer.id()] = {f: True for f in fields}
            self._addLayerListItem(layer)

    def _addLayerListItem(self, layer):
        widget = LayerItemWidget(layer, self)
        item = QListWidgetItem(self.listLayers)
        item.setSizeHint(widget.sizeHint())
        self.listLayers.addItem(item)
        self.listLayers.setItemWidget(item, widget)
        return item

    def populateComboBoxes(self, languages=False):
        """ Populates the server combo boxes with available servers.
        If `languages` is True, the language combo box is also populated.
        """
        if languages:
            self.comboLanguage.clear()
            self.comboLanguage.addItem(self.COMBO_NOTSET_LANG)
            self.comboLanguage.addItems(l10n.label2code.keys())
        self._populateComboMetadataServer()
        self._populateComboGeodataServer()

    def _populateComboGeodataServer(self):
        servers_ = manager.getGeodataServerNames()
        current = self.comboGeodataServer.currentText()
        self.comboGeodataServer.clear()
        self.comboGeodataServer.addItem(self.COMBO_NOTSET_DATA)
        self.comboGeodataServer.addItems(servers_)
        if current in servers_:
            self.comboGeodataServer.setCurrentText(current)

    def _populateComboMetadataServer(self):
        servers_ = manager.getMetadataServerNames()
        current = self.comboMetadataServer.currentText()
        self.comboMetadataServer.clear()
        self.comboMetadataServer.addItem(self.COMBO_NOTSET_META)
        self.comboMetadataServer.addItems(servers_)
        if current in servers_:
            self.comboMetadataServer.setCurrentText(current)

    def updateAll(self):
        """ Updates the publishable layers list and server combo boxes. """

        update_status = False

        # Get BridgeLayer objects and populate list widget
        if not self.publishableLayers:
            # It's safe to only do this once, as the Bridge dialog is modal
            self.publishableLayers = listBridgeLayers()
            self.populateLayerWidget()
            update_status = True

        self.comboGeodataServer.currentIndexChanged.disconnect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.disconnect(self.metadataServerChanged)

        self.populateComboBoxes()
        self.toggleLayerElements()

        if update_status:
            # This is a potentially expensive operation (runs on background thread)
            self.updateOnlineLayerStatus()

        # Fire metadata server changed event once to update metadata tab(s)
        self.metadataServerChanged(False)

        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)

    def importMetadata(self):
        if self.currentLayer is None:
            return

        if not self.currentLayer.is_file_based:
            return self.showWarningBar(
                "Error importing metadata",
                "Can only import metadata for file-based layer sources"
            )

        layer_source = self.currentLayer.uri
        metadata_file = layer_source.with_suffix(".xml")
        if not metadata_file.exists():
            # First find XML using source path with extension replaced for .xml, then use path with .xml appended
            metadata_file = layer_source.with_suffix(f"{layer_source.suffix}.xml")
            if not metadata_file.exists():
                metadata_file = None

        if metadata_file is None:
            res = self.showQuestionBox("Metadata",
                                       "Could not find a suitable metadata XML file.\n"
                                       "Would you like to select it manually?")
            if res == self.BUTTONS.YES:
                metadata_file, _ = QFileDialog.getOpenFileName(self, self.translate("Metadata file"),
                                                               files.getDirectory(self.currentLayer.source()), '*.xml')  # noqa

        if metadata_file:
            try:
                loadMetadataFromXml(self.currentLayer, metadata_file)
            except MetadataDependencyError as err:
                self.logError(err)
                return self.showErrorBar(
                    "Error importing metadata",
                    f"Missing Bridge dependency: {err}"
                )
            except Exception as err:
                self.logError(err)
                return self.showWarningBar(
                    "Error importing metadata",
                    "Cannot convert metadata file. Does it have an ISO19139 or ESRI-ISO format?"
                )

            self.populateLayerMetadata()
            self.showSuccessBar("", "Successfully imported metadata")

    def validateMetadata(self):
        if self.currentLayer is None:
            return
        self.storeMetadata()
        validator = QgsNativeMetadataValidator()
        result, errors = validator.validate(self.currentLayer.metadata())
        if result:
            tr_text = self.translate('No validation errors')
            html = f"<p>{tr_text}</p>"
        else:
            issues = "".join(f"<li><b>{e.section}</b>: {e.note}</li>" for e in errors)
            tr_text = self.translate('The following issues were found')
            html = f"<p>{tr_text}:<ul>{issues}</ul></p>"
        self.showHtmlMessage("Metadata validation", html)

    def openMetadataEditor(self, tab):
        if self.currentLayer is None:
            return
        self.storeMetadata()
        w = MetadataDialog(self.currentLayer, tab, self)
        if w.exec():
            self.populateLayerMetadata()

    def unpublishData(self, layer_id: str) -> bool:
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return False
        layer = layerById(layer_id)
        if layer and server.deleteLayer(layer.web_slug):
            # Deletion was successful: silently try to remove style (should have been removed already)
            server.deleteStyle(layer.web_slug)
            # Mark layer as deleted
            self.updateLayerIsDataPublished(layer_id, None)
            return True
        return False

    def unpublishMetadata(self, layer_id: str) -> bool:
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        layer = layerById(layer_id)
        if not server or not layer:
            return False
        uuid = uuidForLayer(layer)
        try:
            server.deleteMetadata(uuid)
        except Exception as err:
            self.logError(f"Failed to delete metadata on '{server.serverName}': {err}")
            return False
        else:
            self.updateLayerIsMetadataPublished(layer_id, None)
            return True

    def getPublishWidget(self, index: int) -> 'LayerItemWidget':
        """ Returns the LayerItemWidget at the given index. Raises an IndexError if the item does not exist. """
        item = self.listLayers.item(index)
        widget = self.listLayers.itemWidget(item)
        if isinstance(widget, LayerItemWidget):
            return widget
        # This should not happen
        raise IndexError(f"Item at index {index} does not exist or is not a LayerItemWidget")

    def updateLayerIsMetadataPublished(self, layer_id: str, server):
        self.isMetadataPublished[layer_id] = server is not None
        for i in range(self.listLayers.count()):
            widget = self.getPublishWidget(i)
            if widget.id != layer_id:
                continue
            widget.setMetadataPublished(server)

    def updateLayerIsDataPublished(self, layer_id: str, server):
        self.isDataPublished[layer_id] = server is not None
        for i in range(self.listLayers.count()):
            widget = self.getPublishWidget(i)
            if widget.id != layer_id:
                continue
            widget.setDataPublished(server)

    def exportFolderChanged(self):
        """ Resets visual appearance of export folder text box. """
        self.txtExportFolder.setStyleSheet("QLineEdit { }")

    def checkOnlinePublicationStatus(self) -> bool:
        """ Checks if all required online publish fields have been set. """
        data_server = self.comboGeodataServer.currentText()
        meta_server = self.comboMetadataServer.currentText()
        if data_server == self.COMBO_NOTSET_DATA and meta_server == self.COMBO_NOTSET_META:
            self.showWarningBar("Nothing to publish", "Please select at least one target server.")
            return False
        return True

    def checkOfflinePublicationStatus(self) -> bool:
        """ Checks if all required offline publish fields have been set. """
        if self.tabOnOffline.currentWidget() != self.tabOffline:
            # Current tab is not the offline publishing tab
            return True

        checked_items = any((
            self.chkExportGeodata.isChecked(),
            self.chkExportMetadata.isChecked(),
            self.chkExportSymbology.isChecked()
        ))
        if not checked_items:
            self.showWarningBar("Nothing to export",
                                "Please select the things you wish to export (geodata, metadata or symbology).")
        dir_set = len((self.txtExportFolder.text() or '').strip()) > 0
        if not dir_set:
            self.txtExportFolder.setStyleSheet("QLineEdit { border: 2px solid red; }")
        return dir_set and checked_items and self.listLayers.count()

    def updateOnlineLayerStatus(self, data: bool = True, metadata: bool = True):
        """ Validates online tab servers and updates layer status. """

        # === HELPER FUNCTIONS ===
        def _isMetadataOnServer(srv: manager.bases.MetaCatalogServerBase, lyr: BridgeLayer) -> bool:
            """ Checks if metadata is already published on the server (e.g. GeoNetwork). """
            if not srv:
                return False
            uuid = uuidForLayer(lyr)
            return srv.metadataExists(uuid)

        def _isDataOnServer(srv: manager.bases.DataCatalogServerBase, lyr: BridgeLayer,
                            existing_items: frozenset) -> bool:
            """ Checks if a layer is already published on the server (e.g. GeoServer). """
            if not srv:
                return False
            if existing_items is None:
                # Workspace does not exist, so no layers will exist either
                return False
            return lyr.web_slug in existing_items

        def _testServer(srv: manager.bases.ServerBase, combo: QComboBox) -> bool:
            """ Tests a single server connection and displays and error message if it fails. """
            errors = set()
            if srv and not srv.testConnection(errors) and errors:
                combo.setStyleSheet("QComboBox { border: 2px solid red; }")
                for err in errors:
                    self.showErrorBar("Error", err)
                return False
            combo.setStyleSheet('')  # reset default style
            return True

        def _testServers() -> tuple[manager.bases.DataCatalogServerBase, manager.bases.MetaCatalogServerBase]:
            """ Gets the selected server connections (if any) and tests them. """
            data_srv = manager.getGeodataServer(self.comboGeodataServer.currentText()) if data else None
            meta_srv = manager.getMetadataServer(self.comboMetadataServer.currentText()) if metadata else None
            if not _testServer(data_srv, self.comboGeodataServer):
                data_srv = None
            if not _testServer(meta_srv, self.comboMetadataServer):
                meta_srv = None
            return data_srv, meta_srv

        def _iterateLayers():
            """ Returns a generator of all publishable layers and their corresponding widgets. """
            for i in range(self.listLayers.count()):
                widget = self.getPublishWidget(i)
                layer = layerById(widget.id)
                if not layer:
                    continue
                yield layer, widget

        def _refreshStatus(map_srv: Optional[manager.bases.DataCatalogServerBase],
                           cat_srv: Optional[manager.bases.MetaCatalogServerBase],
                           existing_map_layers: Optional[frozenset],
                           layer_item_pair: tuple[BridgeLayer, 'LayerItemWidget']):
            """ Refreshes the publication status of a single layer item for both servers. """

            layer, widget = layer_item_pair

            # Update layer publication status
            if isinstance(map_srv, manager.bases.DataCatalogServerBase):
                published = _isDataOnServer(map_srv, layer, existing_map_layers)
                self.isDataPublished[layer.id()] = published
                state = map_srv if published else None
                widget.setDataPublished(state)
            if isinstance(cat_srv, manager.bases.MetaCatalogServerBase):
                published = _isMetadataOnServer(cat_srv, layer)
                self.isMetadataPublished[layer.id()] = published
                state = cat_srv if published else None
                widget.setMetadataPublished(state)

        # === FUNCTION BODY ===
        if self.tabOnOffline.currentWidget() != self.tabOnline or not self.publishableLayers:
            # Current tab is not the online publish tab, or there aren't any layers to publish
            return

        # Test connection to servers (blocking)
        data_server, meta_server = gui.execute(_testServers)

        if data_server is None and meta_server is None:
            # No servers selected or both tests failed
            return

        # Get list of all layer names on server to prevent doing a lot of requests   TODO: metadata?
        existing_layers = None
        if data_server and hasattr(data_server, 'workspaceExists'):
            if data_server.workspaceExists():
                existing_layers = frozenset(data_server.layerNames().keys())

        try:
            # Refresh layer upload status on background thread (non-blocking)
            items = tuple(_iterateLayers())
            self.toggleUpdateProgress(True, len(items))
            status_func = partial(_refreshStatus, data_server, meta_server, existing_layers)
            self.statusWorker, self.statusThread = gui.BackgroundWorker.setup(status_func, items)
            self.statusWorker.progress.connect(self.progressBar.setValue)
            self.statusWorker.finished.connect(partial(self.toggleUpdateProgress, False))
            self.statusWorker.start()
        except Exception as e:
            self.logError(f"Failed to update layer status: {e}")
            self.toggleUpdateProgress(False)

    def unpublishAll(self):
        """ Removes all geodata from the current server workspace and clears all metadata (published layers only). """
        if self.tabOnOffline.currentWidget() != self.tabOnline:
            # This should not happen (clear all button is visible on online tab only)
            return

        data_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        meta_server = manager.getMetadataServer(self.comboMetadataServer.currentText())

        q_msg = ""
        if data_server:
            q_msg = "all geodata (i.e. clear workspace)"
            if meta_server:
                q_msg += " \nand published metadata"
        elif meta_server:
            q_msg = "all published metadata"
        suffix = " from the specified server"
        suffix += "s" if data_server and meta_server else ""

        res = self.showWarningBox(meta.getAppName(),
                                  f"Are you sure you want to remove {q_msg}{suffix}?",
                                  buttons=self.BUTTONS.YES | self.BUTTONS.NO,
                                  defaultButton=self.BUTTONS.NO)
        if res != self.BUTTONS.YES:
            return

        # Clear all geodata for the current workspace
        data_deleted = False
        if data_server:
            try:
                data_deleted = data_server.clearWorkspace(False)
                if data_deleted:
                    for layer_id in self.isDataPublished.keys():
                        self.isDataPublished[layer_id] = False
            except Exception as err:
                self.logError(f"Failed to clear geodata on '{data_server.serverName}': {err}")
                self.showErrorBar("Error", "Failed to remove geodata from the specified server")
                data_deleted = None

        # Clear metadata (only what has been published)
        if meta_server:
            for layer_id, status in self.isMetadataPublished.items():
                if status:
                    self.isMetadataPublished[layer_id] = not self.unpublishMetadata(layer_id)

        r_msg = "Removed "
        if data_deleted and meta_server:
            r_msg += "geodata and metadata"
        elif data_deleted:
            r_msg += "geodata"
        elif meta_server:
            r_msg += "metadata"
        self.showSuccessBar("Success", f"{r_msg}{suffix}")

        # Update layer item widgets
        self.updateOnlineLayerStatus(data_deleted, meta_server is not None)

    def viewWms(self, layer_id: str):
        layer = layerById(layer_id)
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not (server and layer):
            return
        bbox = layer.extent()
        if bbox.isEmpty():
            bbox.grow(1)
        self.previewWebService(server, [layer.web_slug], bbox, layer.crs().authid())

    def viewAllWms(self):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        bbox = QgsRectangle()
        crs = iface.mapCanvas().mapSettings().destinationCrs()
        names = []
        for layer in self.publishableLayers:
            if not self.isDataPublished.get(layer.id()):
                continue
            names.append(layer.web_slug)
            xform = QgsCoordinateTransform(layer.crs(), crs, QgsProject().instance())
            extent = xform.transform(layer.extent())
            bbox.combineExtentWith(extent)
        # Reverse WMS layer order to correctly stack them visually
        names.sort(reverse=False)
        self.previewWebService(server, names, bbox, crs.authid())

    def previewWebService(self, server, layer_names, bbox, crs_authid):
        sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])
        preview_url = server.getPreviewUrl(layer_names, sbbox, crs_authid)
        if preview_url:
            webbrowser.open_new_tab(preview_url)
        else:
            self.logWarning(f"Server '{server.serverName}' did not return a preview URL")

    def previewMetadata(self):
        if self.currentLayer is None:
            return
        self.showHtmlMessage("Layer metadata", self.currentLayer.htmlMetadata())

    def viewMetadata(self, layer_id: str):
        layer = layerById(layer_id)
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not (server and layer):
            return
        uuid = uuidForLayer(layer)
        server.openMetadata(uuid)

    def publish(self):
        """ Publish/export the selected layers. """

        online = self.tabOnOffline.currentWidget() == self.tabOnline
        action = 'publish' if online else 'export'
        to_publish = self.getCheckedLayers()
        if not to_publish:
            self.showWarningBar(f"Nothing to {action}", "Please select one or more layers.")
            return

        if not online and not self.checkOfflinePublicationStatus():
            # Offline tab active: check if required offline publish settings have been set
            return

        if online:
            # Online tab active
            if not self.checkOnlinePublicationStatus():
                # No server nor "only_symbology" has been selected
                return
            if not self.validateBeforePublication(to_publish, self.chkOnlySymbology.isChecked()):
                # No data is valid for online publishing
                return

        if self.chkBackground.isChecked():
            # User wants to publish in the background: close dialog
            return self.publishOnBackground(to_publish)

        progress_dialog = ProgressDialog(to_publish, self.parent)
        task = self.getPublishTask(self.parent, to_publish)
        task.stepStarted.connect(progress_dialog.setInProgress)
        task.stepSkipped.connect(progress_dialog.setSkipped)
        task.stepFinished.connect(progress_dialog.setFinished)
        progress_dialog.show()
        ret = gui.execute(task.run)
        progress_dialog.close()
        if task.exception is not None:
            if getattr(task, 'exc_type', None) == requests.exceptions.ConnectionError:
                self.showErrorBox(f"Error while {action}ing",
                                  f"Connection error: server unavailable.\n"
                                  f"Please check {meta.getAppName()} log for details.",
                                  propagate=task.exception)
            else:
                self.showErrorBar(f"Error while {action}ing",
                                  f"Please check {meta.getAppName()} log for details.",
                                  propagate=task.exception)
        elif isinstance(task, ExportTask):
            self.showSuccessBar(f"{action.capitalize()} completed", "No issues encountered.")

        if isinstance(task, PublishTask):
            # Show report dialog for publish tasks and update publication status
            task.finished(ret)
            self.updateOnlineLayerStatus(task.geodata_server is not None, task.metadata_server is not None)

    def publishOnBackground(self, to_publish: list[str]):
        self.parent.close()
        task = self.getPublishTask(iface.mainWindow(), to_publish)
        action = 'publish' if hasattr(task, 'exc_type') else 'export'

        def _aborted():
            self.showErrorBar(f"{meta.getAppName()} background {action} failed",
                              f"Please check {meta.getAppName()} log for details.",
                              main=True, propagate=task.exception)

        def _finished():
            self.showSuccessBar(f"{meta.getAppName()} background {action} completed",
                                "No issues encountered.", main=True)

        task.taskTerminated.connect(_aborted)
        task.taskCompleted.connect(_finished)
        QgsApplication.taskManager().addTask(task)
        QCoreApplication.processEvents()  # noqa

    def validateBeforePublication(self, to_publish: list[str], style_only: bool) -> bool:
        """ Checks if there are no duplicate names among the selected layers (also verifies participating group names),
        and performs server-specific checks for each selected layer.
        Shows (bad) results in a dialog and returns False if validation failed.

        :param to_publish:  QGIS layer IDs that must be published.
        :param style_only:  If True, only styles will be published. Value is passed on to server-specific validation.
        """
        errors = set()

        # Collect all participating (group) layer names
        layer_names = listLayerNames(to_publish, actual=True)
        group_names = listGroupNames(to_publish, actual=True)

        # Add errors for duplicate names
        for name, n in ((k, v) for (k, v) in Counter(layer_names).items() if v > 1):
            errors.add(f"Layer name '{name}' is not unique: found {n} duplicates")
        for name, n in ((k, v) for (k, v) in Counter(group_names).items() if v > 1):
            errors.add(f"Group name '{name}' is not unique: found {n} duplicates")

        # Quick check for unsupported chars in names (<server>.validateBeforePublication may be more specific)
        for name in layer_names + group_names:
            for c in "?&=#":
                if c in name:
                    errors.add(f"Unsupported character in group or layer '{name}': '{c}'")

        # Server-specific validation
        geodata_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if geodata_server:
            geodata_server.validateBeforePublication(errors, to_publish, style_only)

        # Display errors (if any) and return
        if errors:
            html = f"<p><b>Cannot publish data.</b></p>"
            issues = "".join(f"<li>{e}</li>" for e in errors)
            if issues:
                html += f"<p>The following issues were found:<ul>{issues}</ul></p>"
            self.showHtmlMessage("Publish", html)
            return False
        return True

    def getCheckedLayers(self) -> list[str]:
        """ Returns a list of the layer IDs that were selected by the user for publication. """
        to_publish = []
        for i in range(self.listLayers.count()):
            widget = self.getPublishWidget(i)
            if widget.checked:
                to_publish.append(widget.id)
        return to_publish

    def getPublishTask(self, parent: QWidget, to_publish: list[str]):
        """ Get ExportTask or PublishTask for the given layers. """

        # Since currentRowChanged has not been called yet,
        # make sure that we store the active tab widget data
        self.storeMetadata()
        self.storeFieldsToPublish()

        style_only = self.chkOnlySymbology.isChecked()
        if self.tabOnOffline.currentWidget() == self.tabOnline:
            geodata_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
            metadata_server = manager.getMetadataServer(self.comboMetadataServer.currentText())
            return PublishTask(to_publish, self.fieldsToPublish, style_only, geodata_server, metadata_server, parent)

        return ExportTask(self.txtExportFolder.text(), to_publish, self.fieldsToPublish,
                          self.chkExportGeodata.isChecked(), self.chkExportMetadata.isChecked(), style_only)

    def showEvent(self, _: QShowEvent):
        """ Triggered when the widget is shown."""
        self.updateAll()


class LayerItemWidget(QWidget):
    def __init__(self, layer: BridgeLayer, publish_widget: PublishWidget = None):
        super(LayerItemWidget, self).__init__()  # noqa
        self._publish_widget = publish_widget
        self._position = publish_widget.listLayers.count() if publish_widget else 0  # assumes widget is added
        self._name = layer.name()
        self._id = layer.id()
        self._checkbox = QCheckBox(self._name, self)
        self._checkbox.clicked.connect(self._checkbox_clicked)
        if layer.is_vector:
            self._checkbox.setIcon(QgsApplication.getThemeIcon('mIconVector.svg'))
        elif layer.is_raster:
            self._checkbox.setIcon(QgsApplication.getThemeIcon('mIconRaster.svg'))
        self._metalabel = QLabel()
        self._metalabel.setFixedWidth(20)
        self._datalabel = QLabel()
        self._datalabel.setFixedWidth(20)
        layout = QHBoxLayout()
        layout.addWidget(self._checkbox)  # noqa
        layout.addWidget(self._datalabel)  # noqa
        layout.addWidget(self._metalabel)  # noqa
        self.setLayout(layout)

    @property
    def name(self):
        """ Returns the corresponding layer name of the current list widget item. """
        return self._name

    @property
    def id(self):
        """ Returns the QGIS layer ID of the current list widget item. """
        return self._id

    @staticmethod
    def _setIcon(label, server) -> bool:
        """ Sets the server icon on the layer item widget if it has been published to that server.

        :returns:   True if the icon was set, False if it was not (or removed).
        """
        if not isinstance(server, manager.bases.AbstractServer):
            if label.pixmap():
                # Remove existing pixmap
                label.pixmap().swap(QPixmap())
            return False
        server_widget = server.__class__.getWidgetClass()
        pixmap = server_widget.getIcon() if server_widget else QPixmap()  # noqa
        if not pixmap.isNull():
            pixmap = pixmap.scaled(label.width(), label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(pixmap)
        return not pixmap.isNull()

    def setMetadataPublished(self, server):
        if self._setIcon(self._metalabel, server):
            self._metalabel.setToolTip(f"Metadata published to '{server.serverName}'")
        else:
            self._metalabel.setToolTip('')
        self.update()

    def setDataPublished(self, server):
        if self._setIcon(self._datalabel, server):
            self._datalabel.setToolTip(f"Geodata published to '{server.serverName}'")
        else:
            self._datalabel.setToolTip('')
        self.update()

    def _checkbox_clicked(self, _):
        """ Make sure that the list widget item is selected when the checkbox is clicked (toggled). """
        if not isinstance(self._publish_widget, PublishWidget):
            return
        self._publish_widget.listLayers.item(self._position).setSelected(True)
        self._publish_widget.currentRowChanged(self._position)

    @property
    def checked(self) -> bool:
        """ Returns True if the list widget item checkbox is in a checked state. """
        return self._checkbox.isChecked()

    def setCheckbox(self, state: bool):
        self._checkbox.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
