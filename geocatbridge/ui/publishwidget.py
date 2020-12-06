import os

import requests
from qgis.PyQt.QtCore import (
    Qt,
    QCoreApplication
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
from geocatbridge.utils import files, gui
from geocatbridge.utils.feedback import FeedbackMixin

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
        super().__init__()
        self.isMetadataPublished = {}
        self.isDataPublished = {}
        self.currentRow = None
        self.currentLayer = None
        self.parent = parent

        self.fieldsToPublish = {}
        self.metadata = {}
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
        self.btnPublish.clicked.connect(self.publish)
        self.btnPublishOnBackground.clicked.connect(self.publishOnBackground)
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

    def selectExportFolder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Export to folder"))
        if folder:
            self.txtExportFolder.setText(folder)

    def geodataServerChanged(self):
        self.updateLayersPublicationStatus(True, False)

    def metadataServerChanged(self):
        self.updateLayersPublicationStatus(False, True)
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
        self.updateLayersPublicationStatus()

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
        servers = manager.getGeodataServers()
        current = self.comboGeodataServer.currentText()
        self.comboGeodataServer.clear()
        self.comboGeodataServer.addItem(self.tr("Do not publish data"))
        self.comboGeodataServer.addItems(servers)
        if current in servers:
            self.comboGeodataServer.setCurrentText(current)

    def populateComboMetadataServer(self):
        servers = manager.getMetadataServers()
        current = self.comboMetadataServer.currentText()
        self.comboMetadataServer.clear()
        self.comboMetadataServer.addItem(self.tr("Do not publish metadata"))
        self.comboMetadataServer.addItems(servers)
        if current in servers:
            self.comboMetadataServer.setCurrentText(current)

    def updateServers(self):
        # TODO: do not call updateLayersPublicationStatus if not really needed
        self.comboGeodataServer.currentIndexChanged.disconnect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.disconnect(self.metadataServerChanged)
        self.populateComboGeodataServer()
        self.populateComboMetadataServer()
        self.updateLayersPublicationStatus()
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
                    "Cannot convert metadata file. Is it really an ISO19139 or ESRI-ISO format?"
                )
                return

            self.metadata[self.currentLayer] = self.currentLayer.metadata().clone()
            self.populateLayerMetadata()
            self.showSuccessBar("", "Metadata correctly imported")

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

    def updateLayersPublicationStatus(self, data=True, metadata=True):
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
        self.btnPublish.setEnabled(can_publish)
        self.btnPublishOnBackground.setEnabled(can_publish)

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
        to_publish = self._toPublish()
        style_only = self.chkOnlySymbology.isChecked()
        if not self.validateBeforePublication(to_publish, style_only):
            return

        progress_dialog = ProgressDialog(to_publish, self.parent)
        task = self.getPublishTask(self.parent)
        task.stepStarted.connect(progress_dialog.setInProgress)
        task.stepSkipped.connect(progress_dialog.setSkipped)
        task.stepFinished.connect(progress_dialog.setFinished)
        progress_dialog.show()
        ret = gui.execute(task.run)
        progress_dialog.close()
        task.finished(ret)
        if task.exception is not None:
            if task.exc_type == requests.exceptions.ConnectionError:
                self.showErrorBox("Error while publishing",
                                  "Connection error. Server unavailable.\nSee QGIS log for details",
                                  propagate=task.exception)
            else:
                self.showErrorBar("Error while publishing", "See QGIS log for details", propagate=task.exception)
        if isinstance(task, PublishTask):
            self.updateLayersPublicationStatus(task.geodata_server is not None, task.metadata_server is not None)

    def publishOnBackground(self):
        to_publish = self._toPublish()
        style_only = self.chkOnlySymbology.isChecked()
        if not self.validateBeforePublication(to_publish, style_only):
            return

        self.parent.close()
        task = self.getPublishTask(iface.mainWindow())

        def _finished():
            if task.exception is not None:
                self.showErrorBar("Error while publishing", "See QGIS log for details",
                                  main=True, propagate=task.exception)

        task.taskTerminated.connect(_finished)
        QgsApplication().taskManager().addTask(task)
        QCoreApplication.processEvents()

    def validateBeforePublication(self, to_publish, style_only):
        names = []
        errors = set()
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.checked():
                name = widget.name()
                for c in "?&=#":
                    if c in name:
                        errors.add("Unsupported character in layer name: " + c)
                if name in names:
                    errors.add("Several layers with the same name")
                names.append(name)

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

    def getPublishTask(self, parent):
        self.storeMetadata()
        self.storeFieldsToPublish()
        to_publish = self._toPublish()

        if self.tabOnOffline.currentIndex() == 0:
            geodata_server = manager.getServer(self.comboGeodataServer.currentText())
            metadata_server = manager.getServer(self.comboMetadataServer.currentText())
            style_only = self.chkOnlySymbology.isChecked()
            return PublishTask(to_publish, self.fieldsToPublish, style_only, geodata_server, metadata_server, parent)

        return ExportTask(self.txtExportFolder.text(), to_publish, self.fieldsToPublish,
                          self.chkExportData.isChecked(),
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
            self.check.setIcon(QgsApplication().getThemeIcon('/mIconLineLayer.svg'))
        else:
            self.check.setIcon(QgsApplication().getThemeIcon('/mIconRaster.svg'))
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
