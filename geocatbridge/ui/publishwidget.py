import json
from pathlib import Path
import webbrowser
from collections import Counter
from functools import partial

import requests
from qgis.PyQt.QtCore import (
    Qt,
    QCoreApplication, QSettings
)
from qgis.PyQt.QtGui import (
    QIcon,
    QPixmap
)
from qgis.PyQt.QtWidgets import (
    QLabel,
    QMenu,
    QWidget,
    QHBoxLayout,
    QCheckBox,
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
from qgis.gui import QgsMetadataWidget
from qgis.utils import iface

from geocatbridge.publish.metadata import uuidForLayer, loadMetadataFromXml
from geocatbridge.publish.tasks import PublishTask, ExportTask
from geocatbridge.servers import manager
from geocatbridge.ui.metadatadialog import MetadataDialog
from geocatbridge.ui.progressdialog import ProgressDialog
from geocatbridge.utils import files, gui, meta
from geocatbridge.utils.feedback import FeedbackMixin
from geocatbridge.utils.layers import getPublishableLayers, getLayerById, getLayerTitleAndName

# QGIS setting that stores the online/offline publish settings
PUBLISH_SETTING = f"{meta.PLUGIN_NAMESPACE}/BridgePublish"

PUBLISHED_ICON = QIcon(files.getIconPath("published"))
ERROR_ICON = f'<img src="{files.getIconPath("error-red")}">'
REMOVE_ICON = QIcon(files.getIconPath("remove"))
VALIDATE_ICON = QIcon(files.getIconPath("validation"))
PREVIEW_ICON = QIcon(files.getIconPath("preview"))
IMPORT_ICON = QIcon(files.getIconPath("save"))

IDENTIFICATION, CATEGORIES, KEYWORDS, ACCESS, EXTENT, CONTACT = range(6)

WIDGET, BASE = gui.loadUiType(__file__)


class PublishWidget(FeedbackMixin, BASE, WIDGET):

    def __init__(self, parent):
        super().__init__(parent)
        self.currentRow = None
        self.currentLayer = None
        self.parent = parent

        # Retrieve publishable layers once:
        # this is safe because the Bridge dialog is modal
        self.publishableLayers = getPublishableLayers()

        # Keep track of fields and metadata for each layer
        self.fieldsToPublish = {}
        self.metadata = {}

        # Keep track if metadata or geodata for a layer has been published
        self.isMetadataPublished = {}
        self.isDataPublished = {}

        # Default "not set" values for publish comboboxes
        self.COMBO_NOTSET_DATA = self.tr("Do not publish data")
        self.COMBO_NOTSET_META = self.tr("Do not publish metadata")

        # Initialize the UI and populate with data on the GUI thread
        gui.execute(self._setupUi)

    def _setupUi(self):
        self.setupUi(self)
        self.txtNoLayers.setVisible(False)
        self.populateComboBoxes()
        self.populateLayers()
        self.listLayers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listLayers.customContextMenuRequested.connect(self.showContextMenu)
        self.listLayers.currentRowChanged.connect(self.currentRowChanged)
        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)
        self.txtExportFolder.textChanged.connect(self.exportFolderChanged)
        self.btnPublish.clicked.connect(self.publish)
        self.btnOpenQgisMetadataEditor.clicked.connect(self.openMetadataEditor)
        self.labelSelect.linkActivated.connect(self.selectLabelClicked)
        self.btnRemoveAll.clicked.connect(self.unpublishAll)
        self.btnValidate.setIcon(VALIDATE_ICON)
        self.btnPreview.clicked.connect(self.previewMetadata)
        self.btnPreview.setIcon(PREVIEW_ICON)
        self.btnImport.setIcon(IMPORT_ICON)
        self.btnImport.clicked.connect(self.importMetadata)
        self.btnValidate.clicked.connect(self.validateMetadata)
        self.btnUseConstraints.clicked.connect(partial(self.openMetadataEditor, ACCESS))
        self.btnAccessConstraints.clicked.connect(partial(self.openMetadataEditor, ACCESS))
        self.btnIsoTopic.clicked.connect(partial(self.openMetadataEditor, CATEGORIES))
        self.btnKeywords.clicked.connect(partial(self.openMetadataEditor, KEYWORDS))
        self.btnDataContact.clicked.connect(partial(self.openMetadataEditor, CONTACT))
        self.btnMetadataContact.clicked.connect(partial(self.openMetadataEditor, CONTACT))
        self.btnExportFolder.clicked.connect(self.selectExportFolder)
        self.btnClose.clicked.connect(self.parent.close)
        self.tabOnOffline.currentChanged.connect(partial(self.tabOnOfflineChanged))

        if self.listLayers.count():
            item = self.listLayers.item(0)
            self.listLayers.setCurrentItem(item)
            self.currentRowChanged(0)
        else:
            self.txtNoLayers.setVisible(True)
            self.listLayers.setVisible(False)
            self.labelSelect.setVisible(False)
            self.btnRemoveAll.setVisible(False)

        self.metadataServerChanged()
        self.selectLabelClicked("all")

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
        except json.JSONDecodeError as e:
            self.logError(f"Failed to parse publish settings: {e}")
            return

        # Set online settings
        update_meta = False
        update_data = False
        online_settings = settings.get('online', {})
        geodata_server = online_settings.get('geodataServer')
        if geodata_server and geodata_server in manager.getGeodataServerNames():
            self.comboGeodataServer.setCurrentText(geodata_server)
            update_data = True
        metadata_server = online_settings.get('metadataServer')
        if metadata_server and metadata_server in manager.getMetadataServerNames():
            self.comboMetadataServer.setCurrentText(metadata_server)
            update_meta = True
        style_only = online_settings.get('symbologyOnly', False)
        self.chkOnlySymbology.setCheckState(Qt.Checked if style_only else Qt.Unchecked)

        # Set offline settings
        offline_settings = settings.get('offline', {})
        self.chkExportGeodata.setCheckState(Qt.Checked if offline_settings.get('exportGeodata') else Qt.Unchecked)
        self.chkExportMetadata.setCheckState(Qt.Checked if offline_settings.get('exportMetadata') else Qt.Unchecked)
        self.chkExportSymbology.setCheckState(Qt.Checked if offline_settings.get('exportSymbology') else Qt.Unchecked)
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
        self.updateOnlineLayersPublicationStatus()

    def selectExportFolder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Export to folder"))
        if folder:
            self.txtExportFolder.setText(folder)

    def geodataServerChanged(self):
        self.updateOnlineLayersPublicationStatus(True, False)

    def metadataServerChanged(self):
        self.updateOnlineLayersPublicationStatus(False, True)
        md_combo = self.comboMetadataServer.currentText()
        profile = 0
        if md_combo != self.COMBO_NOTSET_META:
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
            self.tabWidgetMetadata.addTab(self.tabTemporal, self.tr("Temporal"))

    def selectLabelClicked(self, url):
        """ Selects all layers if 'all' is clicked and deselects all layers if 'none' is clicked. """
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            self.listLayers.itemWidget(item).setCheckbox(url != 'none')

    def currentRowChanged(self, current_row):
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
        metadata = self.metadata[self.currentLayer.id()]
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
        self.comboLanguage.setCurrentText(metadata.language())
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
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                check = Qt.Checked if self.fieldsToPublish[self.currentLayer.id()][field] else Qt.Unchecked
                item.setCheckState(check)
                self.tableFields.setItem(i, 0, item)
                item = QTableWidgetItem(field)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.tableFields.setItem(i, 1, item)
        else:
            self.tabLayerInfo.setTabEnabled(1, False)

    def storeMetadata(self):
        if not self.currentLayer:
            return
        metadata = self.metadata[self.currentLayer.id()]
        metadata.setTitle(self.txtMetadataTitle.text())
        metadata.setAbstract(self.txtAbstract.toPlainText())
        metadata.setLanguage(self.comboLanguage.currentText())
        self.currentLayer.setMetadata(metadata)

    def storeFieldsToPublish(self):
        if not self.currentLayer or self.currentLayer.type() != self.currentLayer.VectorLayer:
            return
        pub_fields = {}
        fields = self.currentLayer.fields()
        for i in range(fields.count()):
            check = self.tableFields.item(i, 0)
            name = self.tableFields.item(i, 1)
            pub_fields[name.text()] = check.checkState() == Qt.Checked
        self.fieldsToPublish[self.currentLayer.id()] = pub_fields

    def showContextMenu(self, pos):
        """ Provides a context menu for published layers. """
        item = self.listLayers.itemAt(pos)
        if item is None:
            return
        layer_id = self.listLayers.itemWidget(item).id
        menu = QMenu()
        if self.isDataPublished.get(layer_id):
            menu.addAction(self.tr("View WMS layer"), partial(self.viewWms, layer_id))
            # menu.addAction(self.tr("Unpublish data"), lambda: self.unpublishData(layer_id))  TODO
        if self.isMetadataPublished.get(layer_id):
            menu.addAction(self.tr("View metadata"), partial(self.viewMetadata, layer_id))
            # menu.addAction(self.tr("Unpublish metadata"), lambda: self.unpublishMetadata(layer_id))  TODO
        if any(self.isDataPublished.values()):
            menu.addAction(self.tr("View all WMS layers"), self.viewAllWms)
        menu.exec_(self.listLayers.mapToGlobal(pos))

    def populateLayers(self):
        for i, layer in enumerate(self.publishableLayers):
            fields = [f.name() for f in layer.fields()] if \
                (hasattr(layer, 'fields') and layer.type() == layer.VectorLayer) else []
            self.fieldsToPublish[layer.id()] = {f: True for f in fields}
            self.metadata[layer.id()] = layer.metadata().clone()
            self.addLayerListItem(layer)
        self.updateOnlineLayersPublicationStatus()

    def addLayerListItem(self, layer):
        widget = LayerItemWidget(layer)
        item = QListWidgetItem(self.listLayers)
        item.setSizeHint(widget.sizeHint())
        self.listLayers.addItem(item)
        self.listLayers.setItemWidget(item, widget)
        return item

    def populateComboBoxes(self):
        self.populateComboMetadataServer()
        self.populateComboGeodataServer()
        self.comboLanguage.clear()
        for lang in QgsMetadataWidget().parseLanguages():
            self.comboLanguage.addItem(lang)

    def populateComboGeodataServer(self):
        servers = manager.getGeodataServerNames()
        current = self.comboGeodataServer.currentText()
        self.comboGeodataServer.clear()
        self.comboGeodataServer.addItem(self.COMBO_NOTSET_DATA)
        self.comboGeodataServer.addItems(servers)
        if current in servers:
            self.comboGeodataServer.setCurrentText(current)

    def populateComboMetadataServer(self):
        servers = manager.getMetadataServerNames()
        current = self.comboMetadataServer.currentText()
        self.comboMetadataServer.clear()
        self.comboMetadataServer.addItem(self.COMBO_NOTSET_META)
        self.comboMetadataServer.addItems(servers)
        if current in servers:
            self.comboMetadataServer.setCurrentText(current)

    def updateServers(self):
        # TODO: do not call updateOnlineLayersPublicationStatus if not really needed
        self.comboGeodataServer.currentIndexChanged.disconnect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.disconnect(self.metadataServerChanged)
        self.populateComboGeodataServer()
        self.populateComboMetadataServer()
        self.updateOnlineLayersPublicationStatus()
        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)

    def isMetadataOnServer(self, layer):
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not server:
            return False
        uuid = uuidForLayer(layer)
        return server.metadataExists(uuid)

    def isDataOnServer(self, layer):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return False
        _, name = getLayerTitleAndName(layer)
        return server.layerExists(name)

    def importMetadata(self):
        if self.currentLayer is None:
            return
        layer_source = Path(self.currentLayer.source())
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
                metadata_file, _ = QFileDialog.getOpenFileName(self, self.tr("Metadata file"),
                                                               files.getDirectory(self.currentLayer.source()), '*.xml')

        if metadata_file:
            try:
                loadMetadataFromXml(self.currentLayer, metadata_file)
            except Exception as err:
                self.logError(err)
                self.showWarningBar(
                    "Error importing metadata",
                    "Cannot convert metadata file. Does it have an ISO19139 or ESRI-ISO format?"
                )
                return

            self.metadata[self.currentLayer.id()] = self.currentLayer.metadata().clone()
            self.populateLayerMetadata()
            self.showSuccessBar("", "Successfully imported metadata")

    def validateMetadata(self):
        if self.currentLayer is None:
            return
        self.storeMetadata()
        validator = QgsNativeMetadataValidator()
        result, errors = validator.validate(self.metadata[self.currentLayer.id()])
        if result:
            html = f"<p>{self.tr('No validation errors')}</p>"
        else:
            issues = "".join(f"<li><b>{e.section}</b>: {e.note}</li>" for e in errors)
            html = f"<p>{self.tr('The following issues were found')}:<ul>{issues}</ul></p>"
        self.showHtmlMessage("Metadata validation", html)

    def openMetadataEditor(self, tab):
        if self.currentLayer is None:
            return
        self.storeMetadata()
        metadata = self.metadata[self.currentLayer.id()].clone()
        w = MetadataDialog(metadata, tab, self)
        w.exec_()
        if w.metadata is not None:
            self.metadata[self.currentLayer.id()] = w.metadata
            self.populateLayerMetadata()

    def unpublishData(self, layer_id):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        layer = getLayerById(layer_id)
        _, name = getLayerTitleAndName(layer)
        if server.deleteLayer(name):
            # Deletion was successful: silently try to remove style (should have been removed already)
            server.deleteStyle(name)
            # Mark layer as deleted
            self.updateLayerIsDataPublished(layer_id, None)

    def unpublishMetadata(self, layer_id):
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not server:
            return False
        uuid = uuidForLayer(getLayerById(layer_id))
        server.deleteMetadata(uuid)
        self.updateLayerIsMetadataPublished(layer_id, None)
        return True

    def updateLayerIsMetadataPublished(self, layer_id, server):
        self.isMetadataPublished[layer_id] = server is not None
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.id != layer_id:
                continue
            widget.setMetadataPublished(server)

    def updateLayerIsDataPublished(self, layer_id, server):
        self.isDataPublished[layer_id] = server is not None
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.id != layer_id:
                continue
            widget.setDataPublished(server)

    def exportFolderChanged(self):
        """ Resets visual appearance of export folder text box. """
        self.txtExportFolder.setStyleSheet("QLineEdit { }")

    def checkOnlinePublicationStatus(self) -> bool:
        """ Checks if all required online publish fields have been set. """
        if self.tabOnOffline.currentWidget() != self.tabOnline:
            # Current tab is not the online publishing tab
            return True

        # Test if servers (or symbology) have been selected
        data_server = self.comboGeodataServer.currentText()
        meta_server = self.comboMetadataServer.currentText()
        if data_server == self.COMBO_NOTSET_DATA and meta_server == self.COMBO_NOTSET_META \
                and not self.chkOnlySymbology.isChecked():
            self.showWarningBar("Nothing to publish",
                                "Please select a geodata and/or metadata server to use.")
            return False

        # Test connections of selected servers
        errors = set()
        success = []
        data_server = manager.getGeodataServer(data_server)
        meta_server = manager.getMetadataServer(meta_server)
        if data_server:
            success.append(data_server.testConnection(errors))
        if meta_server:
            success.append(meta_server.testConnection(errors))
        for e in errors:
            self.showErrorBar("Error", e)

        return all(success)

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

    def updateOnlineLayersPublicationStatus(self, data: bool = True, metadata: bool = True) -> bool:
        """ Validates online tab servers and updates layer status. """

        if self.tabOnOffline.currentWidget() != self.tabOnline:
            # Current tab is not the online publish tab
            return True

        can_publish = True
        data_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        metadata_server = manager.getMetadataServer(self.comboMetadataServer.currentText())

        errors = set()
        if data:
            self.comboGeodataServer.setStyleSheet("QComboBox { }")
            if data_server and not data_server.testConnection(errors):
                self.comboGeodataServer.setStyleSheet("QComboBox { border: 2px solid red; }")
                can_publish = False

        if metadata:
            self.comboMetadataServer.setStyleSheet("QComboBox { }")
            if metadata_server and not metadata_server.testConnection(errors):
                self.comboMetadataServer.setStyleSheet("QComboBox { border: 2px solid red; }")
                can_publish = False

        # Show errors (if there are any)
        for e in errors:
            self.showErrorBar("Error", e)

        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            layer = getLayerById(widget.id)
            if data:
                server = None
                if data_server:
                    self.isDataPublished[layer.id()] = self.isDataOnServer(layer)
                    server = data_server if self.isDataPublished.get(layer.id()) else None
                widget.setDataPublished(server)
            if metadata:
                server = None
                if metadata_server:
                    self.isMetadataPublished[layer.id()] = self.isMetadataOnServer(layer)
                    server = metadata_server if self.isMetadataPublished[layer.id()] else None
                widget.setMetadataPublished(server)

        can_publish = can_publish and self.listLayers.count()
        return can_publish

    def unpublishAll(self):
        """ Removes all geodata from the current server workspace and clears all metadata (published layers only). """
        if self.tabOnOffline.currentWidget() != self.tabOnline:
            return

        res = self.showQuestionBox(meta.getAppName(),
                                   "Are you sure you want to remove all geodata (clear workspace) "
                                   "and/or published metadata from the specified server(s)?",
                                   buttons=self.BUTTONS.YES | self.BUTTONS.NO)
        if res != self.BUTTONS.YES:
            return

        # Clear all geodata for the current workspace
        data_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not data_server:
            return
        result = data_server.clearWorkspace(False)
        if result:
            for layer_id in self.isDataPublished.keys():
                self.isDataPublished[layer_id] = False

        # Clear metadata (only what has been published)
        meta_server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        for layer_id, status in self.isMetadataPublished.items():
            if status:
                self.isMetadataPublished[layer_id] = not self.unpublishMetadata(layer_id)

        if result:
            if meta_server:
                self.showSuccessBar("Success", "Removed geodata and/or metadata from the selected server(s)")
            else:
                self.showSuccessBar("Success", "Removed geodata from the selected server")

        # Update layer item widgets
        self.updateOnlineLayersPublicationStatus(data_server is not None, meta_server is not None)

    def viewWms(self, layer_id):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        layer = getLayerById(layer_id)
        _, name = getLayerTitleAndName(layer)
        bbox = layer.extent()
        if bbox.isEmpty():
            bbox.grow(1)
        self.previewWebService(server, [name], bbox, layer.crs().authid())

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
            _, name = getLayerTitleAndName(layer)
            names.append(name)
            xform = QgsCoordinateTransform(layer.crs(), crs, QgsProject().instance())
            extent = xform.transform(layer.extent())
            bbox.combineExtentWith(extent)
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

    def viewMetadata(self, layer_id):
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not server:
            return
        layer = getLayerById(layer_id)
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
                                  "Connection error: server unavailable.\nPlease check QGIS log for details.",
                                  propagate=task.exception)
            else:
                self.showErrorBar(f"Error while {action}ing",
                                  "Please check QGIS log for details.", propagate=task.exception)
        elif isinstance(task, ExportTask):
            self.showSuccessBar(f"{action.capitalize()} completed", "No issues encountered.")

        if isinstance(task, PublishTask):
            # Show report dialog for publish tasks and update publication status
            task.finished(ret)
            self.updateOnlineLayersPublicationStatus(task.geodata_server is not None, task.metadata_server is not None)

    def publishOnBackground(self, to_publish):
        self.parent.close()
        task = self.getPublishTask(iface.mainWindow(), to_publish)
        action = 'publish' if hasattr(task, 'exc_type') else 'export'

        def _aborted():
            self.showErrorBar(f"{meta.getAppName()} background {action} failed",
                              "Please check QGIS log for details.", main=True, propagate=task.exception)

        def _finished():
            self.showSuccessBar(f"{meta.getAppName()} background {action} completed",
                                "No issues encountered.", main=True)

        task.taskTerminated.connect(_aborted)
        task.taskCompleted.connect(_finished)
        QgsApplication.taskManager().addTask(task)
        QCoreApplication.processEvents()

    def validateBeforePublication(self, to_publish, style_only):
        errors = set()
        for name, n in ((k, v) for (k, v) in Counter(to_publish).items() if v > 1):
            errors.add(f"Layer name '{name}' is not unique: found {n} duplicates")
        for name in to_publish:
            for c in "?&=#":
                if c in name:
                    errors.add(f"Unsupported character in layer '{name}': '{c}'")

        geodata_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if geodata_server:
            geodata_server.validateBeforePublication(errors, to_publish, style_only)

        if errors:
            html = f"<p><b>Cannot publish data.</b></p>"
            issues = "".join(f"<li>{e}</li>" for e in errors)
            if issues:
                html += f"<p>The following issues were found:<ul>{issues}</ul></p>"
            self.showHtmlMessage("Publish", html)
            return False
        else:
            return True

    def getCheckedLayers(self):
        """ Returns a list of the layer IDs that were selected by the user for publication. """
        to_publish = []
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.checked:
                to_publish.append(widget.id)
        return to_publish

    def getPublishTask(self, parent, to_publish):
        """ Get ExportTask or PublishTask for the given layers. """

        # Since currentRowChanged has not been called yet,
        # make sure that we store the active tab widget data
        self.storeMetadata()
        self.storeFieldsToPublish()

        if self.tabOnOffline.currentWidget() == self.tabOnline:
            geodata_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
            metadata_server = manager.getMetadataServer(self.comboMetadataServer.currentText())
            style_only = self.chkOnlySymbology.isChecked()
            return PublishTask(to_publish, self.fieldsToPublish, style_only, geodata_server, metadata_server, parent)

        return ExportTask(self.txtExportFolder.text(), to_publish, self.fieldsToPublish,
                          self.chkExportGeodata.isChecked(),
                          self.chkExportMetadata.isChecked(), self.chkExportSymbology.isChecked())


class LayerItemWidget(QWidget):
    def __init__(self, layer, parent=None):
        super(LayerItemWidget, self).__init__(parent)
        self._name = layer.name()
        self._id = layer.id()
        self._checkbox = QCheckBox()
        self._checkbox.setText(self._name)
        if layer.type() == layer.VectorLayer:
            self._checkbox.setIcon(QgsApplication.getThemeIcon('/mIconLineLayer.svg'))
        else:
            self._checkbox.setIcon(QgsApplication.getThemeIcon('/mIconRaster.svg'))
        self._metalabel = QLabel()
        self._metalabel.setFixedWidth(20)
        self._datalabel = QLabel()
        self._datalabel.setFixedWidth(20)
        layout = QHBoxLayout()
        layout.addWidget(self._checkbox)
        layout.addWidget(self._datalabel)
        layout.addWidget(self._metalabel)
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
        pixmap = server_widget.getPngIcon() if server_widget else QPixmap()
        if not pixmap.isNull():
            pixmap = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        return not pixmap.isNull()

    def setMetadataPublished(self, server):
        if self._setIcon(self._metalabel, server):
            self._metalabel.setToolTip(f"Metadata published to '{server.serverName}'")
        else:
            self._metalabel.setToolTip('')

    def setDataPublished(self, server):
        if self._setIcon(self._datalabel, server):
            self._datalabel.setToolTip(f"Geodata published to '{server.serverName}'")
        else:
            self._datalabel.setToolTip('')

    @property
    def checked(self) -> bool:
        """ Returns True if the list widget item checkbox is in a checked state. """
        return self._checkbox.isChecked()

    def setCheckbox(self, state: bool):
        self._checkbox.setCheckState(Qt.Checked if state else Qt.Unchecked)
