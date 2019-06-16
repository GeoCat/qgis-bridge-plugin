import os
import traceback
from qgis.PyQt import uic
from geocatbridge.publish.servers import geodataServers, metadataServers, GeonetworkServer
from geocatbridge.ui.serverconnectionsdialog import ServerConnectionsDialog
from geocatbridge.ui.metadatadialog import MetadataDialog
from geocatbridge.ui.publishreportdialog import PublishReportDialog
from geocatbridgecommons import log
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.utils import iface
from qgiscommons2.gui import execute

def iconPath(icon):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", icon)

PUBLISHED_ICON = QIcon(iconPath("published.png"))
ERROR_ICON = '<img src="%s">' % iconPath("error-red.png")
REMOVE_ICON = QIcon(iconPath("remove.png"))
VALIDATE_ICON = QIcon(iconPath("validation.png"))
PREVIEW_ICON = QIcon(iconPath("preview.png"))
SAVE_ICON = QIcon(iconPath("save.png"))

IDENTIFICATION, CATEGORIES, KEYWORDS, ACCESS, EXTENT, CONTACT = range(6)

WIDGET, BASE = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'geocatbridgedialog.ui'))

class GeocatBridgeDialog(BASE, WIDGET):

    def __init__(self, parent=None):
        super(GeocatBridgeDialog, self).__init__(parent)
        self.isMetadataPublished = {}
        self.isDataPublished = {}
        self.currentRow = None
        self.currentLayer = None

        self.fieldsToPublish = {}
        self.metadata = {}
        self.setupUi(self)

        self.bar = QgsMessageBar()
        self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.bar)

        class QgisLogger():
            def logInfo(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Info)
            def logWarning(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Warning)
            def logError(self, text):
                QgsMessageLog.logMessage(text, 'GeoCat Bridge', level=Qgis.Critical)

        logger = QgisLogger()
        log.setLogger(logger)

        self.populateComboBoxes()
        self.populateLayers()
        self.tableLayers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableLayers.customContextMenuRequested.connect(self.showContextMenu)
        self.tableLayers.currentCellChanged.connect(self.currentCellChanged)
        self.comboGeodataServer.currentIndexChanged.connect(self.populateLayers)
        self.comboMetadataServer.currentIndexChanged.connect(self.metadataServerChanged)
        self.btnDefineConnectionsData.clicked.connect(self.defineConnectionsData)
        self.btnDefineConnectionsMetadata.clicked.connect(self.defineConnectionsMetadata)
        self.btnPublish.clicked.connect(self.publish)
        self.btnClose.clicked.connect(self.close)
        self.btnOpenQgisMetadataEditor.clicked.connect(self.openMetadataEditor)
        self.labelSelect.linkActivated.connect(self.selectLabelClicked)
        self.btnRemoveAll.clicked.connect(self.unpublishAll)
        self.btnRemoveAll.setIcon(REMOVE_ICON)
        self.btnValidate.setIcon(VALIDATE_ICON)
        self.btnPreview.setIcon(PREVIEW_ICON)
        self.btnSave.setIcon(SAVE_ICON)
        self.btnUseConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnAccessConstraints.clicked.connect(lambda: self.openMetadataEditor(ACCESS))
        self.btnIsoTopic.clicked.connect(lambda: self.openMetadataEditor(CATEGORIES))
        self.btnKeywords.clicked.connect(lambda: self.openMetadataEditor(KEYWORDS))
        self.btnDataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))
        self.btnMetadataContact.clicked.connect(lambda: self.openMetadataEditor(CONTACT))

        if self.tableLayers.rowCount():
            self.currentCellChanged(0, 0, None, None)

        self.metadataServerChanged()

    def metadataServerChanged(self):
        self.populateLayers()
        try:
            profile = metadataServers()[self.comboMetadataServer.currentText()]
        except KeyError:
            profile = GeonetworkServer.PROFILE_DEFAULT
        if profile == GeonetworkServer.PROFILE_DEFAULT:
            if self.tabWidgetMetadata.count() == 3:
                self.tabWidgetMetadata.removeTab(1)
                self.tabWidgetMetadata.removeTab(1)
        else:
            if self.tabWidgetMetadata.count() == 1:
                self.tabWidgetMetadata.addTab(self.tabInspire)
                self.tabWidgetMetadata.addTab(self.tabTemporal)
            self.comboStatus.setVisible(profile == GeonetworkServer.PROFILE_DUTCH)
        
    def selectLabelClicked(self, url):
        state = Qt.Unchecked if url == "none" else Qt.Checked
        for i in range (self.tableLayers.rowCount()):
            item = self.tableLayers.item(i, 0)
            item.setCheckState(state)

    def currentCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
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
            self.comboDataContact.setCurrentText(metadata.contacts()[0].name)
            self.comboMetadataContact.setCurrentText(metadata.contacts()[0].name)
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
        item = self.tableLayers.itemAt(pos)
        print(item)
        if item is None:
            return
        row = self.tableLayers.row(item)
        name = self.tableLayers.item(row, 1).text()
        menu = QMenu()
        menu.addAction("View metadata", lambda: self.viewMetadata(name))
        if self.isDataPublished[name]:
            menu.addAction("View WMS layer", lambda: self.viewWms(name))
            menu.addAction("Unpublish data", lambda: self.unpublishData(name))
        if self.isMetadataPublished[name]:    
            menu.addAction("Unpublish metadata", lambda: self.unpublishMetadata(name))
        print(menu)
        print(self.tableLayers.mapToGlobal(pos))
        menu.exec_(self.tableLayers.mapToGlobal(pos))

    def publishableLayers(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() 
                if layer.type() in [QgsMapLayer.VectorLayer, QgsMapLayer.RasterLayer]]
        return layers

    def populateLayers(self):
        self.tableLayers.setRowCount(0)
        layers = self.publishableLayers()
        self.tableLayers.setRowCount(len(layers))
        for i, layer in enumerate(layers):
            fields = [f.name() for f in layer.fields()]
            self.fieldsToPublish[layer] = {f:True for f in fields}
            self.metadata[layer] = layer.metadata().clone()            
            item = QTableWidgetItem()
            item.setCheckState(Qt.Unchecked)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 0, item)
            item = QTableWidgetItem(layer.name())
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 1, item)
            self.isMetadataPublished[layer.name()] = self.isMetadataOnServer(layer)
            item = QTableWidgetItem()
            item.setIcon(PUBLISHED_ICON if self.isMetadataPublished[layer.name()] else QIcon())
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 2, item)
            self.isDataPublished[layer.name()] = self.isDataOnServer(layer)
            item = QTableWidgetItem()          
            item.setIcon(PUBLISHED_ICON if self.isDataPublished[layer.name()] else QIcon())
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.tableLayers.setItem(i, 3, item)

    def populateComboBoxes(self):
        self.populatecomboMetadataServer()
        self.populatecomboGeodataServer()
        self.comboLanguage.clear()
        w = QgsMetadataWidget()
        for lang in w.parseLanguages():
            self.comboLanguage.addItem(lang)

    def populatecomboGeodataServer(self):
        self.comboGeodataServer.clear()
        self.comboGeodataServer.addItems(geodataServers().keys())

    def populatecomboMetadataServer(self):
        self.comboMetadataServer.clear()
        self.comboMetadataServer.addItems(metadataServers().keys())

    def isMetadataOnServer(self, layer):
        try:
            catalog = metadataServers()[self.comboMetadataServer.currentText()].catalog()
            self.labelErrorMetadataServer.setText("")
            return catalog.metadata_exists(layer.name())
        except KeyError:
            self.labelErrorMetadataServer.setText("")
            return False
        except:
            self.labelErrorMetadataServer.setText(ERROR_ICON)

    def isDataOnServer(self, layer):
        try:
            catalog = geodataServers()[self.comboGeodataServer.currentText()].catalog()
            self.labelErrorGeodataServer.setText("")
            return catalog.layer_exists(layer.name())
        except KeyError:
            self.labelErrorGeodataServer.setText("")
            return False
        except:
            self.labelErrorGeodataServer.setText(ERROR_ICON)

    def openMetadataEditor(self, tab):
        metadata = self.metadata[self.currentLayer].clone()
        w = MetadataDialog(metadata, tab, self)
        w.exec_()
        if w.metadata is not None:
            self.metadata[self.currentLayer] = w.metadata
            self.populateLayerMetadata()

    def defineConnectionsData(self):
        current = self.comboGeodataServer.currentText()
        self.openConnectionsDialog()
        self.populatecomboGeodataServer()
        if current in geodataServers().keys():
            self.comboGeodataServer.setCurrentText(current)

    def defineConnectionsMetadata(self):
        current = self.comboGeodataServer.currentText()
        self.openConnectionsDialog()
        self.populatecomboMetadataServer()
        if current in metadataServers().keys():
            self.comboMetadataServer.setCurrentText(current)            

    def openConnectionsDialog(self):
        dlg = ServerConnectionsDialog(iface.mainWindow())
        dlg.exec_()

    def unpublishData(self, name):
        catalog = geodataServers()[self.comboGeodataServer.currentText()].catalog()
        catalog.delete_layer(name)
        catalog.delete_style(name)
        self.updateLayerIsDataPublished(name, False)

    def unpublishMetadata(self, name):
        catalog = metadataServers()[self.comboMetadataServer.currentText()].catalog()
        catalog.delete_metadata(name)
        self.updateLayerIsMetadataPublished(name, False)

    def updateLayerIsMetadataPublished(self, name, value):
        self.isMetadataPublished[name] = value
        for i in range(self.tableLayers.rowCount()):
            item = self.tableLayers.item(i, 1)
            if item.text() == name:
                item.setIcon(PUBLISHED_ICON if value else QIcon())

    def updateLayerIsDataPublished(self, name, value):
        self.isDataPublished[name] = value
        for i in range(self.tableLayers.rowCount()):
            item = self.tableLayers.item(i, 1)
            if item.text() == name:
                item.setIcon(PUBLISHED_ICON if value else QIcon())

    def unpublishAll(self):
        for name in self.isDataPublished:
            if self.isDataPublished[name]:
                self.unpublishData(name)
            if self.isMetadataPublished[name]:
                self.unpublishMetadata(name)            

    def viewWms(self, name):
        pass

    def viewMetadata(self, name):
        pass        

    def publish(self):
        try:
            execute(self._publish)
            self.bar.clearWidgets()
            dialog = PublishReportDialog(self)
            dialog.exec_()
        except:
            self.bar.pushMessage("Error while publishing", "See QGIS log for details", level=Qgis.Warning, duration=5)
            QgsMessageLog.logMessage(traceback.format_exc(), 'GeoCat Bridge', level=Qgis.Critical)

    def _publish(self):
        if self.chkPublishToGeodataServer.checkState() == Qt.Checked:
            try:
                geodataServer = geodataServers()[self.comboGeodataServer.currentText()]
            except KeyError:                
                self.bar.pushMessage("Error", "No map server has been defined", level=Qgis.Warning, duration=5)
                return
        else:
            geodataServer = None

        if self.chkPublishToMetadataServer.checkState() == Qt.Checked:
            try:
                metadataServer = metadataServers()[self.comboMetadataServer.currentText()]
            except KeyError:  
                self.bar.pushMessage("Error", "No metadata catalogue has been defined", level=Qgis.Warning, duration=5)              
                return
        else:
            metadataServer = None 

        progressMessageBar = self.bar.createMessage("Publishing layers")
        progress = QProgressBar()
        progress.setMaximum(self.tableLayers.rowCount())
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        self.bar.pushWidget(progressMessageBar, Qgis.Info)

        for i in range(self.tableLayers.rowCount()):
            progress.setValue(i)
            item = self.tableLayers.item(i, 0)
            if item.checkState() == Qt.Checked:                
                name = self.tableLayers.item(i, 1).text()                
                layer = self.layerFromName(name)
                if geodataServer is not None:
                    if self.chkOnlySymbology.checkState() == Qt.Checked:
                        geodataServer.publishStyle(layer)
                    else:
                        fields = None
                        if layer.type() == layer.VectorLayer:
                            fields = [name for name, publish in self.fieldsToPublish[layer].items() if publish]                            
                        geodataServer.publishLayer(layer, fields)
                        self.updateLayerIsDataPublished(name, True)
                if metadataServer is not None:
                    metadataServer.publishLayerMetadata(layer)
                    self.updateLayerIsMetadataPublished(name, True)        

    def layerFromName(self, name):
        layers = self.publishableLayers()
        for layer in layers:
            if layer.name() == name:
                return layer