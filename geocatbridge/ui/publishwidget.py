import os
import traceback

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtWidgets import (
    QProgressBar,
    QLabel,
    QMenu,
    QWidget,
    QComboBox,
    QHBoxLayout,
    QSizePolicy,
    QCheckBox,
    QListWidgetItem,
    QTableWidgetItem
) 
from qgis.PyQt.QtGui import (
    QIcon,
    QPixmap
)

from qgis.core import (
    QgsCoordinateTransform,
    QgsMessageOutput,
    QgsMapLayer,
    QgsMessageLog,
    QgsNativeMetadataValidator, 
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsProject,
    Qgis
)
from qgis.gui import QgsMessageBar, QgsMetadataWidget
from qgis.utils import iface

from geocatbridge.utils.gui import execute
from geocatbridge.publish.geonetwork import GeonetworkServer
from geocatbridge.publish.servers import geodataServers, metadataServers
from geocatbridge.publish.metadata import uuidForLayer
from geocatbridge.ui.metadatadialog import MetadataDialog
from geocatbridge.ui.publishreportdialog import PublishReportDialog

def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)

PUBLISHED_ICON = QIcon(iconPath("published.png"))
ERROR_ICON = '<img src="%s">' % iconPath("error-red.png")
REMOVE_ICON = QIcon(iconPath("remove.png"))
VALIDATE_ICON = QIcon(iconPath("validation.png"))
PREVIEW_ICON = QIcon(iconPath("preview.png"))
SAVE_ICON = QIcon(iconPath("save.png"))

IDENTIFICATION, CATEGORIES, KEYWORDS, ACCESS, EXTENT, CONTACT = range(6)

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'publishwidget.ui'))


class PublishWidget(BASE, WIDGET):

    def __init__(self):
        super(PublishWidget, self).__init__()
        self.isMetadataPublished = {}
        self.isDataPublished = {}
        self.currentRow = None
        self.currentLayer = None

        self.fieldsToPublish = {}
        self.metadata = {}
        execute(self._setupUi)

        for s in geodataServers().values():
            s.setupForProject()

    def _setupUi(self):
        self.setupUi(self)    
        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.bar)

        self.populateComboBoxes()
        self.populateLayers()
        self.listLayers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listLayers.customContextMenuRequested.connect(self.showContextMenu)
        self.listLayers.currentRowChanged.connect(self.currentRowChanged)
        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)
        self.btnPublish.clicked.connect(self.publish)
        self.btnOpenQgisMetadataEditor.clicked.connect(self.openMetadataEditor)
        self.labelSelect.linkActivated.connect(self.selectLabelClicked)
        self.btnRemoveAll.clicked.connect(self.unpublishAll)
        self.btnRemoveAll.setIcon(REMOVE_ICON)
        self.btnValidate.setIcon(VALIDATE_ICON)
        self.btnPreview.clicked.connect(self.previewMetadata)
        self.btnPreview.setIcon(PREVIEW_ICON)
        self.btnSave.setIcon(SAVE_ICON)
        self.btnValidate.clicked.connect(self.validateMetadata)
        self.btnUseConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnAccessConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnIsoTopic.clicked.connect(lambda: self.openMetadataEditor(CATEGORIES))
        self.btnKeywords.clicked.connect(lambda: self.openMetadataEditor(KEYWORDS))
        self.btnDataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))
        self.btnMetadataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))        

        if self.listLayers.count():
            item = self.listLayers.item(0)
            self.listLayers.setCurrentItem(item)
            self.currentRowChanged(0)

        self.metadataServerChanged()
        self.selectLabelClicked("all")


    def geodataServerChanged(self):
        self.updateLayersPublicationStatus(True, False)

    def metadataServerChanged(self):
        self.updateLayersPublicationStatus(False, True)
        try:
            profile = metadataServers()[self.comboMetadataServer.currentText()].profile
        except KeyError:
            profile = GeonetworkServer.PROFILE_DEFAULT
        if profile == GeonetworkServer.PROFILE_DEFAULT:
            if self.tabWidgetMetadata.count() == 3:
                self.tabWidgetMetadata.removeTab(1)
                self.tabWidgetMetadata.removeTab(1)
        else:
            if self.tabWidgetMetadata.count() == 1:
                title = "Dutch geography" if profile == GeonetworkServer.PROFILE_DUTCH else "INSPIRE"
                self.tabWidgetMetadata.addTab(self.tabInspire, title)
                self.tabWidgetMetadata.addTab(self.tabTemporal, self.tr("Temporal"))
            self.comboStatus.setVisible(profile == GeonetworkServer.PROFILE_DUTCH)
        
    def selectLabelClicked(self, url):
        state = Qt.Unchecked if url == "none" else Qt.Checked
        for i in range (self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item).setCheckState(state)

    def currentRowChanged(self, currentRow):
        if self.currentRow == currentRow:
            return
        self.currentRow = currentRow
        self.storeFieldsToPublish()
        self.storeMetadata()
        layers = self.publishableLayers()
        layer = layers[currentRow]
        self.currentLayer = layer
        self.populateLayerMetadata()
        self.populateLayerFields()
        if layer.type() != layer.VectorLayer:
            self.tabLayerInfo.setCurrentWidget(self.tabMetadata)

    def populateLayerMetadata(self):
        metadata = self.metadata[self.currentLayer]
        self.txtMetadataTitle.setText(metadata.title())
        self.txtAbstract.setPlainText(metadata.abstract())
        isoTopics = ",".join(metadata.keywords().get("gmd:topicCategory", []))
        self.txtIsoTopic.setText(isoTopics)        
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
        #TODO: Use default values if no values in QGIS metadata object

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
                fieldsToPublish = {}
                fields = self.currentLayer.fields()
                for i in range(fields.count()):
                    chkItem = self.tableFields.item(i, 0)
                    nameItem = self.tableFields.item(i, 1)
                    fieldsToPublish[nameItem.text()] = chkItem.checkState() == Qt.Checked
                self.fieldsToPublish[self.currentLayer] = fieldsToPublish

    def showContextMenu(self, pos):
        item = self.listLayers.itemAt(pos)
        if item is None:
            return
        row = self.listLayers.row(item)
        name = self.listLayers.itemWidget(item).name()
        menu = QMenu()        
        if self.isDataPublished[name]:
            menu.addAction(self.tr("View WMS layer"), lambda: self.viewWms(name))
            menu.addAction(self.tr("Unpublish data"), lambda: self.unpublishData(name))
        if self.isMetadataPublished[name]:
            menu.addAction(self.tr("View metadata"), lambda: self.viewMetadata(name))  
            menu.addAction(self.tr("Unpublish metadata"), lambda: self.unpublishMetadata(name))
        if any(self.isDataPublished.values()):
            menu.addAction(self.tr("View all WMS layers"), self.viewAllWms)
        menu.exec_(self.listLayers.mapToGlobal(pos))

    def publishableLayers(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() 
                if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]]
        return layers

    def populateLayers(self):
        layers = self.publishableLayers()
        for i, layer in enumerate(layers):
            fields = [f.name() for f in layer.fields()] if layer.type() == layer.VectorLayer else []
            self.fieldsToPublish[layer] = {f:True for f in fields}
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
        self.populatecomboMetadataServer()
        self.populatecomboGeodataServer()
        self.comboLanguage.clear()
        for lang in QgsMetadataWidget.parseLanguages():
            self.comboLanguage.addItem(lang)

    def populatecomboGeodataServer(self):
        self.comboGeodataServer.clear()
        self.comboGeodataServer.addItem(self.tr("Do not publish data"))
        self.comboGeodataServer.addItems(geodataServers().keys())

    def populatecomboMetadataServer(self):
        self.comboMetadataServer.clear()
        self.comboMetadataServer.addItem(self.tr("Do not publish metadata"))
        self.comboMetadataServer.addItems(metadataServers().keys())

    def updateServers(self):
        #TODO: do not call updateLayersPublicationStatus if not really needed
        self.comboGeodataServer.currentIndexChanged.disconnect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.disconnect(self.metadataServerChanged)
        self.populatecomboMetadataServer()
        current = self.comboGeodataServer.currentText()
        self.populatecomboGeodataServer()
        if current in geodataServers().keys():
            self.comboGeodataServer.setCurrentText(current)
        current = self.comboMetadataServer.currentText()
        self.populatecomboMetadataServer()
        if current in metadataServers().keys():
            self.comboMetadataServer.setCurrentText(current)
        self.updateLayersPublicationStatus()
        self.comboGeodataServer.currentIndexChanged.connect(self.geodataServerChanged)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)

    def isMetadataOnServer(self, layer):
        try:
            server = metadataServers()[self.comboMetadataServer.currentText()]
            self.comboMetadataServer.setStyleSheet("QComboBox {}")
            uuid = uuidForLayer(self.layerFromName(layer))
            return server.metadataExists(uuid)
        except KeyError:
            self.comboMetadataServer.setStyleSheet("QComboBox {}")
            return False
        except:
            self.comboMetadataServer.setStyleSheet("QComboBox { border: 2px solid red; }")

    def isDataOnServer(self, layer):
        try:
            server = geodataServers()[self.comboGeodataServer.currentText()]
            self.comboGeodataServer.setStyleSheet("QComboBox {}")
            return server.layerExists(layer)
        except KeyError:
            self.comboGeodataServer.setStyleSheet("QComboBox {}")
            return False
        except Exception as e:
            self.comboGeodataServer.setStyleSheet("QComboBox { border: 2px solid red; }")

    def validateMetadata(self):
        self.storeMetadata()
        validator = QgsNativeMetadataValidator()
        result, errors = validator.validate(self.metadata[self.currentLayer])
        if result:
            txt = self.tr("No validation errors")
        else:
            txt = self.tr("The following issues were found:") + "<br>" + "<br>".join(["<b>%s</b>:%s" % (err.section, err.note) for err in errors])
        dlg = QgsMessageOutput.createMessageOutput()
        dlg.setTitle(self.tr("Metadata validation"))
        dlg.setMessage(txt, QgsMessageOutput.MessageHtml)
        dlg.showMessage()

    def openMetadataEditor(self, tab):
        self.storeMetadata()
        metadata = self.metadata[self.currentLayer].clone()
        w = MetadataDialog(metadata, tab, self)
        w.exec_()
        if w.metadata is not None:
            self.metadata[self.currentLayer] = w.metadata
            self.populateLayerMetadata()          

    def openConnectionsDialog(self):
        dlg = ServerConnectionsDialog(iface.mainWindow())
        dlg.exec_()

    def unpublishData(self, name):
        server = geodataServers()[self.comboGeodataServer.currentText()]
        server.deleteLayer(name)
        server.deleteStyle(name)
        self.updateLayerIsDataPublished(name, False)

    def unpublishMetadata(self, name):
        server = metadataServers()[self.comboMetadataServer.currentText()]
        uuid = uuidForLayer(self.layerFromName(name))
        server.deleteMetadata(uuid)
        self.updateLayerIsMetadataPublished(name, False)

    def updateLayerIsMetadataPublished(self, name, value):
        self.isMetadataPublished[name] = value
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.name() == name:
                server = metadataServers()[self.comboMetadataServer.currentText()] if value else None
                widget.setMetadataPublished(server)

    def updateLayerIsDataPublished(self, name, value):
        self.isDataPublished[name] = value
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.name() == name:
                server = geodataServers()[self.comboGeodataServer.currentText()] if value else None
                widget.setDataPublished(server)

    def updateLayersPublicationStatus(self, data=True, metadata=True):
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            name = widget.name()
            if data:
                self.isDataPublished[name] = self.isDataOnServer(name)
                server = geodataServers()[self.comboGeodataServer.currentText()] if self.isDataPublished[name] else None
                widget.setDataPublished(server)
            if metadata:
                self.isMetadataPublished[name] = self.isMetadataOnServer(name)
                server = metadataServers()[self.comboMetadataServer.currentText()] if self.isMetadataPublished[name] else None
                widget.setMetadataPublished(server)

    def unpublishAll(self):
        for name in self.isDataPublished:
            if self.isDataPublished[name]:
                self.unpublishData(name)
            if self.isMetadataPublished[name]:
                self.unpublishMetadata(name)            

    def viewWms(self, name):        
        layer = self.layerFromName(name)
        names = [layer.name()]        
        bbox = layer.extent()
        if bbox.isEmpty():
            bbox.grow(1)
        sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])        
        server = geodataServers()[self.comboGeodataServer.currentText()]
        server.openWms(names, sbbox, layer.crs().authid())

    def viewAllWms(self):
        server = geodataServers()[self.comboGeodataServer.currentText()]
        layers = self.publishableLayers()
        bbox = QgsRectangle()
        canvasCrs = iface.mapCanvas().mapSettings().destinationCrs()
        names = []
        for layer in layers:
            if self.isDataPublished[layer.name()]:
                names.append(layer.name())                
                xform = QgsCoordinateTransform(layer.crs(), canvasCrs, QgsProject.instance())
                extent = xform.transform(layer.extent())
                bbox.combineExtentWith(extent)
        sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])
        server.openWms(names, sbbox, canvasCrs.authid())

    def previewMetadata(self):
        html = self.currentLayer.htmlMetadata()
        dlg = QgsMessageOutput.createMessageOutput()
        dlg.setTitle("Layer metadata")
        dlg.setMessage(html, QgsMessageOutput.MessageHtml)
        dlg.showMessage()

    def viewMetadata(self, name):
        server = geodataServers()[self.comboMetadataServer.currentText()]
        layer = self.layerFromName(name)
        uuid = uuidForLayer(layer)
        server.openMetadata(uuid)

    def publish(self):
        try:
            ret = execute(self._publish)
            if ret is not None:
                self.bar.clearWidgets()
                dialog = PublishReportDialog(self, ret)
                dialog.exec_()
        except:
            self.bar.clearWidgets()
            self.bar.pushMessage(self.tr("Error while publishing"), self.tr("See QGIS log for details"), level=Qgis.Warning, duration=5)
            QgsMessageLog.logMessage(traceback.format_exc(), 'GeoCat Bridge', level=Qgis.Critical)

    def _publish(self):
        if self.comboGeodataServer.currentIndex() != 0:
            geodataServer = geodataServers()[self.comboGeodataServer.currentText()]
        else:
            geodataServer = None

        if self.comboMetadataServer.currentIndex() != 0:
            metadataServer = metadataServers()[self.comboMetadataServer.currentText()]
        else:
            metadataServer = None 

        toPublish = []
        for i in range(self.listLayers.count()):            
            item = self.listLayers.item(i)
            widget = self.listLayers.itemWidget(item)
            if widget.checked():
                name = widget.name()   
                toPublish.append(name)

        progressMessageBar = self.bar.createMessage(self.tr("Publishing layers"))
        progress = QProgressBar()
        progress.setMaximum(self.listLayers.count())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        self.bar.pushWidget(progressMessageBar, Qgis.Info)

        self.storeMetadata()
        self.storeFieldsToPublish()

        validator = QgsNativeMetadataValidator()        
            
        DONOTALLOW = 0
        ALLOW = 1
        ALLOWONLYDATA = 2
        
        allowWithoutMetadata = ALLOW #pluginSetting("allowWithoutMetadata")

        if geodataServer is not None:
            geodataServer.prepareForPublishing(self.chkOnlySymbology.checkState() == Qt.Checked)

        results = {}
        warnings, errors = [], []
        for i, name in enumerate(toPublish):
            progressMessageBar.setText("Publishing layer " + name)
            progress.setValue(i)                    
            try:                       
                layer = self.layerFromName(name)
                validates, _ = validator.validate(layer.metadata())
                validates = True
                if geodataServer is not None:
                    geodataServer.resetLog()
                    if self.chkOnlySymbology.checkState() == Qt.Checked:
                        geodataServer.publishStyle(layer)
                    else:
                        if validates or allowWithoutMetadata in [ALLOW, ALLOWONLYDATA]:
                            fields = None
                            if layer.type() == layer.VectorLayer:
                                fields = [name for name, publish in self.fieldsToPublish[layer].items() if publish]                            
                            geodataServer.publishLayer(layer, fields)
                            if metadataServer is not None:
                                metadataUuid = uuidForLayer(layer)
                                url = metadataServer.metadataUrl(metadataUuid)
                                geodataServer.setLayerMetadataLink(name, url)
                        else:
                            geodataServer.logError(self.tr("Layer '%s' has invalid metadata. Layer was not published") % layer.name())
                if metadataServer is not None:
                    metadataServer.resetLog()
                    if validates or allowWithoutMetadata == ALLOW:
                        if geodataServer is not None:
                            names = [layer.name()]        
                            bbox = layer.extent()
                            sbbox = ",".join([str(v) for v in [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]])                            
                            wms = layerWms(names, bbox, layer.crs().authid())
                        else:
                            wms = None
                        metadataServer.publishLayerMetadata(layer, wms)
                    else:
                        metadataServer.logError(self.tr("Layer '%s' has invalid metadata. Metadata was not published") % layer.name())
            except:
                errors.append(traceback.format_exc())
            if geodataServer is not None:
                w, e = geodataServer.loggedInfo()
                warnings.extend(w)
                errors.extend(e)
            if metadataServer is not None:
                w, e = metadataServer.loggedInfo()
                warnings.extend(w)
                errors.extend(e)
            results[name] = (set(warnings), errors)

        if geodataServer is not None:            
            groups = self._layerGroups(toPublish)                            
            geodataServer.createGroups(groups)

            geodataServer.closePublishing()

        self.updateLayersPublicationStatus(geodataServer is not None, metadataServer is not None)

        return results


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


class LayerItemWidget(QWidget):
    def __init__ (self, layer, parent = None):
        super(LayerItemWidget, self).__init__(parent)
        self.layer = layer
        self.layout = QHBoxLayout()
        self.check = QCheckBox()
        self.check.setText(layer.name())
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

    def iconPath(self, server):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", 
                        "%s.png" % server.__class__.__name__.lower()[:-6])

    def setMetadataPublished(self, server):
        self.labelMetadata.setPixmap(QPixmap(self.iconPath(server)))

    def setDataPublished(self, server):
        self.labelData.setPixmap(QPixmap(self.iconPath(server)))

    def checked(self):
        return self.check.isChecked()

    def setCheckState(self, state):
        self.check.setCheckState(state)
