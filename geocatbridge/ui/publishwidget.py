import json
import os
from collections import Counter

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
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsProject,
    QgsApplication,
    QgsRectangle
)
from qgis.gui import QgsMetadataWidget
from qgis.utils import iface

from geocatbridge.servers import manager
from geocatbridge.publish.metadata import uuidForLayer, loadMetadataFromXml
from geocatbridge.publish.publishtask import PublishTask, ExportTask
from geocatbridge.ui.metadatadialog import MetadataDialog
from geocatbridge.ui.progressdialog import ProgressDialog
from geocatbridge.utils import files, gui, meta
from geocatbridge.utils.feedback import FeedbackMixin

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
        self.isMetadataPublished = {}
        self.isDataPublished = {}
        self.currentRow = None
        self.currentLayer = None
        self.parent = parent

        self.fieldsToPublish = {}
        self.metadata = {}

        # Default "not set" values for publish comboboxes
        self.COMBO_NOTSET_DATA = self.tr("Do not publish data")
        self.COMBO_NOTSET_META = self.tr("Do not publish metadata")

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
        self.btnRemoveAll.setIcon(REMOVE_ICON)
        self.btnValidate.setIcon(VALIDATE_ICON)
        self.btnPreview.clicked.connect(self.previewMetadata)
        self.btnPreview.setIcon(PREVIEW_ICON)
        self.btnImport.setIcon(IMPORT_ICON)
        self.btnImport.clicked.connect(self.importMetadata)
        self.btnValidate.clicked.connect(self.validateMetadata)
        self.btnUseConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnAccessConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnIsoTopic.clicked.connect(lambda: self.openMetadataEditor(CATEGORIES))
        self.btnKeywords.clicked.connect(lambda: self.openMetadataEditor(KEYWORDS))
        self.btnDataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))
        self.btnMetadataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))
        self.btnExportFolder.clicked.connect(self.selectExportFolder)
        self.btnClose.clicked.connect(self.parent.close)

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

    def setFromConfig(self):
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
            self.logError(f"Failed to parse publish settings:\n{e}")
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
        self.chkOnlySymbology.setCheckState(Qt.Checked if style_only else Qt.Unchecked)

        # Set offline settings
        offline_settings = settings.get('offline', {})
        self.chkExportGeodata.setCheckState(Qt.Checked if offline_settings.get('exportGeodata') else Qt.Unchecked)
        self.chkExportMetadata.setCheckState(Qt.Checked if offline_settings.get('exportMetadata') else Qt.Unchecked)
        self.chkExportSymbology.setCheckState(Qt.Checked if offline_settings.get('exportSymbology') else Qt.Unchecked)
        folder = offline_settings.get('exportFolder') or ''
        self.txtExportFolder.setText(folder)

        # Set active tab (making sure there's no IndexError)
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
        state = Qt.Unchecked if url == "none" else Qt.Checked
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            self.listLayers.itemWidget(item).setCheckState(state)

    def currentRowChanged(self, current_row):
        if self.currentRow == current_row:
            return
        self.currentRow = current_row
        self.storeFieldsToPublish()
        self.storeMetadata()
        layers = self.publishableLayers()
        layer = layers[current_row]
        self.currentLayer = layer
        self.populateLayerMetadata()
        self.populateLayerFields()
        if layer.type() != layer.VectorLayer:
            self.tabLayerInfo.setCurrentWidget(self.tabMetadata)

    def populateLayerMetadata(self):
        metadata = self.metadata[self.currentLayer]
        self.txtMetadataTitle.setText(metadata.title())
        self.txtAbstract.setPlainText(metadata.abstract())
        iso_topics = ",".join(metadata.keywords().get("gmd:topicCategory", []))
        self.txtIsoTopic.setText(iso_topics)
        keywords = []
        for group in metadata.keywords().values():
            keywords.extend(group)
        self.txtKeywords.setText(",".join(keywords))
        if metadata.contacts():
            self.txtDataContact.setText(metadata.contacts()[0].name)
            self.txtMetadataContact.setText(metadata.contacts()[0].name)
        self.txtUseConstraints.setText(metadata.fees())
        licenses = metadata.licenses()
        if licenses:
            self.txtAccessConstraints.setText(licenses[0])
        else:
            self.txtAccessConstraints.setText("")
        self.comboLanguage.setCurrentText(metadata.language())
        # TODO: Use default values if no values in QGIS metadata object

    def populateLayerFields(self):
        if self.currentLayer.type() == self.currentLayer.VectorLayer:
            fields = [f.name() for f in self.currentLayer.fields()]
            self.tabLayerInfo.setTabEnabled(1, True)
            self.tableFields.setRowCount(len(fields))
            for i, field in enumerate(fields):
                item = QTableWidgetItem()
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                check = Qt.Checked if self.fieldsToPublish[self.currentLayer][field] else Qt.Unchecked
                item.setCheckState(check)
                self.tableFields.setItem(i, 0, item)
                item = QTableWidgetItem(field)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.tableFields.setItem(i, 1, item)
        else:
            self.tabLayerInfo.setTabEnabled(1, False)

    def storeMetadata(self):
        if self.currentLayer is not None:
            metadata = self.metadata[self.currentLayer]
            metadata.setTitle(self.txtMetadataTitle.text())
            metadata.setAbstract(self.txtAbstract.toPlainText())
            metadata.setLanguage(self.comboLanguage.currentText())
            self.currentLayer.setMetadata(metadata)

    def storeFieldsToPublish(self):
        if self.currentLayer is not None:
            if self.currentLayer.type() == self.currentLayer.VectorLayer:
                pub_fields = {}
                fields = self.currentLayer.fields()
                for i in range(fields.count()):
                    check = self.tableFields.item(i, 0)
                    name = self.tableFields.item(i, 1)
                    pub_fields[name.text()] = check.checkState() == Qt.Checked
                self.fieldsToPublish[self.currentLayer] = pub_fields

    def showContextMenu(self, pos):
        item = self.listLayers.itemAt(pos)
        if item is None:
            return
        name = self.listLayers.itemWidget(item).name()
        menu = QMenu()
        if self.isDataPublished.get(name):
            menu.addAction(self.tr("View WMS layer"), lambda: self.viewWms(name))
            menu.addAction(self.tr("Unpublish data"), lambda: self.unpublishData(name))
        if self.isMetadataPublished.get(name):
            menu.addAction(self.tr("View metadata"), lambda: self.viewMetadata(name))
            menu.addAction(self.tr("Unpublish metadata"), lambda: self.unpublishMetadata(name))
        if any(self.isDataPublished.values()):
            menu.addAction(self.tr("View all WMS layers"), self.viewAllWms)
        menu.exec_(self.listLayers.mapToGlobal(pos))

    @staticmethod
    def publishableLayers():
        def _layersFromTree(layer_tree):
            _layers = []
            for child in layer_tree.children():
                if isinstance(child, QgsLayerTreeLayer):
                    _layers.append(child.layer())
                elif isinstance(child, QgsLayerTreeGroup):
                    _layers.extend(_layersFromTree(child))
            return _layers

        root = QgsProject().instance().layerTreeRoot()
        layers = [layer for layer in _layersFromTree(root)
                  if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]
                  and layer.dataProvider().name() != "wms"]
        return layers

    def populateLayers(self):
        layers = self.publishableLayers()
        for i, layer in enumerate(layers):
            fields = [f.name() for f in layer.fields()] if layer.type() == layer.VectorLayer else []
            self.fieldsToPublish[layer] = {f: True for f in fields}
            self.metadata[layer] = layer.metadata().clone()
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
        uuid = uuidForLayer(self.layerFromName(layer))
        return server.metadataExists(uuid)

    def isDataOnServer(self, layer):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if server:
            return server.layerExists(layer)
        return False

    def importMetadata(self):
        if self.currentLayer is None:
            return
        metadata_file = os.path.splitext(self.currentLayer.source())[0] + ".xml"
        if not os.path.exists(metadata_file):
            metadata_file = self.currentLayer.source() + ".xml"
            if not os.path.exists(metadata_file):
                metadata_file = None

        if metadata_file is None:
            res = self.showQuestionBox("Metadata file",
                                       "Could not find a suitable metadata file.\nDo you want to select it manually?")
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

            self.metadata[self.currentLayer] = self.currentLayer.metadata().clone()
            self.populateLayerMetadata()
            self.showSuccessBar("", "Successfully imported metadata")

    def validateMetadata(self):
        if self.currentLayer is None:
            return
        self.storeMetadata()
        validator = QgsNativeMetadataValidator()
        result, errors = validator.validate(self.metadata[self.currentLayer])
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
        metadata = self.metadata[self.currentLayer].clone()
        w = MetadataDialog(metadata, tab, self)
        w.exec_()
        if w.metadata is not None:
            self.metadata[self.currentLayer] = w.metadata
            self.populateLayerMetadata()

    def unpublishData(self, name):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        server.deleteLayer(name)
        server.deleteStyle(name)
        self.updateLayerIsDataPublished(name, False)

    def unpublishMetadata(self, name):
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not server:
            return
        uuid = uuidForLayer(self.layerFromName(name))
        server.deleteMetadata(uuid)
        self.updateLayerIsMetadataPublished(name, False)

    def updateLayerIsMetadataPublished(self, name, value):
        self.isMetadataPublished[name] = value
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.name() != name:
                continue
            server = manager.getMetadataServer(self.comboMetadataServer.currentText())
            widget.setMetadataPublished(True if server and value else False)

    def updateLayerIsDataPublished(self, name, value):
        self.isDataPublished[name] = value
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.name() != name:
                continue
            server = manager.getGeodataServer(self.comboGeodataServer.currentText())
            widget.setMetadataPublished(True if server and value else False)

    def exportFolderChanged(self):
        """ Resets visual appearance of export folder text box. """
        self.txtExportFolder.setStyleSheet("QLineEdit { }")

    def checkOnlinePublicationStatus(self) -> bool:
        """ Checks if all required online publish fields have been set. """
        if self.tabOnOffline.currentWidget() != self.tabOnline:
            # Current tab is not the online publishing tab
            return True

        if self.comboGeodataServer.currentText() == self.COMBO_NOTSET_DATA and self.comboMetadataServer.currentText() and not self.chkOnlySymbology.isChecked():
            self.showWarningBar("Nothing to publish",
                                "Please select a geodata and/or metadata server to use.")
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

    def updateOnlineLayersPublicationStatus(self, data: bool = True, metadata: bool = True) -> bool:
        """ Validates online tab servers and updates layer status. """

        if self.tabOnOffline.currentWidget() != self.tabOnline:
            # Current tab is not the online publish tab
            return True

        can_publish = True
        data_server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        metadata_server = manager.getMetadataServer(self.comboMetadataServer.currentText())

        if data:
            self.comboGeodataServer.setStyleSheet("QComboBox { }")
            if data_server and not data_server.testConnection():
                self.comboGeodataServer.setStyleSheet("QComboBox { border: 2px solid red; }")
                can_publish = False

        if metadata:
            self.comboMetadataServer.setStyleSheet("QComboBox { }")
            if metadata_server and not metadata_server.testConnection():
                self.comboMetadataServer.setStyleSheet("QComboBox { border: 2px solid red; }")
                can_publish = False

        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            name = widget.name()
            if data:
                server = None
                if data_server:
                    self.isDataPublished[name] = self.isDataOnServer(name)
                    server = data_server if self.isDataPublished[name] else None
                widget.setDataPublished(server)
            if metadata:
                server = None
                if metadata_server:
                    self.isMetadataPublished[name] = self.isMetadataOnServer(name)
                    server = metadata_server if self.isMetadataPublished[name] else None
                widget.setMetadataPublished(server)

        can_publish = can_publish and self.listLayers.count()
        return can_publish

    def unpublishAll(self):
        for name in self.isDataPublished:
            if self.isDataPublished.get(name, False):
                self.unpublishData(name)
            if self.isMetadataPublished.get(name, False):
                self.unpublishMetadata(name)

    def viewWms(self, name):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        layer = self.layerFromName(name)
        names = [layer.name()]
        bbox = layer.extent()
        if bbox.isEmpty():
            bbox.grow(1)
        sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])
        server.openPreview(names, sbbox, layer.crs().auth_id())

    def viewAllWms(self):
        server = manager.getGeodataServer(self.comboGeodataServer.currentText())
        if not server:
            return
        layers = self.publishableLayers()
        bbox = QgsRectangle()
        crs = iface.mapCanvas().mapSettings().destinationCrs()
        names = []
        for layer in layers:
            if not self.isDataPublished[layer.name()]:
                continue
            names.append(layer.name())
            xform = QgsCoordinateTransform(layer.crs(), crs, QgsProject().instance())
            extent = xform.transform(layer.extent())
            bbox.combineExtentWith(extent)
        sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])
        server.openPreview(names, sbbox, crs.auth_id())

    def previewMetadata(self):
        if self.currentLayer is None:
            return
        self.showHtmlMessage("Layer metadata", self.currentLayer.htmlMetadata())

    def viewMetadata(self, name):
        server = manager.getMetadataServer(self.comboMetadataServer.currentText())
        if not server:
            return
        layer = self.layerFromName(name)
        uuid = uuidForLayer(layer)
        server.openMetadata(uuid)

    def publish(self):
        """ Publish/export the selected layers. """

        online = self.tabOnOffline.currentWidget() == self.tabOnline
        action = 'publish' if online else 'export'
        to_publish = self._toPublish()
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

        geodata_server = manager.getServer(self.comboGeodataServer.currentText())
        if geodata_server:
            geodata_server.validateBeforePublication(errors, to_publish, style_only)

        # if self.comboMetadataServer.currentIndex() != 0:
        #     metadata_server = metadataServers()[self.comboMetadataServer.currentText()]
        #     metadata_server.validateMetadataBeforePublication(errors)

        if errors:
            html = f"<p><b>Cannot publish data.</b></p>"
            issues = "".join(f"<li>{e}</li>" for e in errors)
            if issues:
                html += f"<p>The following issues were found:<ul>{issues}</ul></p>"
            self.showHtmlMessage("Publish", html)
            return False
        else:
            return True

    def _toPublish(self):
        to_publish = []
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.checked():
                name = widget.name()
                to_publish.append(name)
        return to_publish

    def getPublishTask(self, parent, to_publish):
        self.storeMetadata()
        self.storeFieldsToPublish()

        if self.tabOnOffline.currentWidget() == self.tabOnline:
            geodata_server = manager.getServer(self.comboGeodataServer.currentText())
            metadata_server = manager.getServer(self.comboMetadataServer.currentText())
            style_only = self.chkOnlySymbology.isChecked()
            return PublishTask(to_publish, self.fieldsToPublish, style_only, geodata_server, metadata_server, parent)

        return ExportTask(self.txtExportFolder.text(), to_publish, self.fieldsToPublish,
                          self.chkExportGeodata.isChecked(),
                          self.chkExportMetadata.isChecked(), self.chkExportSymbology.isChecked())

    def layerFromName(self, name):
        layers = self.publishableLayers()
        for layer in layers:
            if layer.name() == name:
                return layer


class LayerItemWidget(QWidget):
    def __init__(self, layer, parent=None):
        super(LayerItemWidget, self).__init__(parent)
        self.layer = layer
        self.layout = QHBoxLayout()
        self.check = QCheckBox()
        self.check.setText(layer.name())
        if layer.type() == layer.VectorLayer:
            self.check.setIcon(QgsApplication.getThemeIcon('/mIconLineLayer.svg'))
        else:
            self.check.setIcon(QgsApplication.getThemeIcon('/mIconRaster.svg'))
        self.labelMetadata = QLabel()
        self.labelMetadata.setFixedWidth(50)
        self.labelData = QLabel()
        self.labelData.setFixedWidth(50)
        self.layout.addWidget(self.check)
        self.layout.addWidget(self.labelData)
        self.layout.addWidget(self.labelMetadata)
        self.setLayout(self.layout)

    def name(self):
        return self.layer.name()

    @staticmethod
    def setIcon(label, server):
        pixmap = QPixmap(files.getIconPath(server.__class__.__name__.lower()[:-6]))
        label.setPixmap(pixmap)

    def setMetadataPublished(self, server):
        self.setIcon(self.labelMetadata, server)

    def setDataPublished(self, server):
        self.setIcon(self.labelData, server)

    def checked(self):
        return self.check.isChecked()

    def setCheckState(self, state):
        self.check.setCheckState(state)
