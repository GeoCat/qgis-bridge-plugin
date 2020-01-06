import os

import bridgestyle

from geocatbridge.publish.geoserver import GeoserverServer

from qgis.PyQt.QtGui import QImage, QColor, QPainter
from qgis.PyQt.QtCore import QSize, QCoreApplication, QUrl, QEventLoop

from qgis.core import (
    QgsMapSettings, 
    QgsMapRendererCustomPainterJob,
    QgsRasterLayer,
    QgsVectorLayer
)

from qgis.PyQt.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest
)

class TestGeoserverServer(GeoserverServer):

    def setupForProject(self):
        self._workspace = "visualtests"   
    
_layers = {}
def load_layer(file):    
    if file not in _layers:
        name = os.path.basename(file)
        layer = QgsRasterLayer(file, name, "gdal")
        if not layer.isValid():
            layer = QgsVectorLayer(file, "testlayer", "ogr")
        _layers[file] = layer
    return _layers[file]

def create_styles_visual_test_page(folder, url = "http://localhost:8080/geoserver", username="admin", password="geoserver"):
    server = TestGeoserverServer("testserver", url)
    server.setBasicAuthCredentials(username, password)
    server.setupForProject()
    server.prepareForPublishing(False)
    main_folder = os.path.join(os.path.dirname(bridgestyle.__file__), "test", "data", "qgis")
    s = ""
    for subfolder in os.listdir(main_folder):
        datafile = os.path.join(main_folder, subfolder, "testlayer.gpkg")
        layer = load_layer(datafile)
        if not os.path.exists(datafile):
            datafile = os.path.join(main_folder, subfolder, "testlayer.tiff")        
        subfolder_path = os.path.join(main_folder, subfolder)
        for style in os.listdir(subfolder_path):
            if style.lower().endswith("qml"):
                stylefile = os.path.join(subfolder_path, style)
                name = os.path.splitext(os.path.basename(stylefile))[0]
                layer.setName(name)              
                layer.loadNamedStyle(stylefile)
                server.publishLayer(layer)
                s = s + create_images(folder, url, layer)
    indexfilename = os.path.join(folder, "index.html")
    with open(indexfilename, "w") as f:
        f.write(s)
    server.deleteWorkspace()

WIDTH = 500.0

def create_images(folder, url, layer):
    extent = layer.extent()  
    filename = os.path.join(folder, "%s_qgis.png" % layer.name())
    save_layer_image(filename, layer, extent)
    filename_wms = os.path.join(folder, "%s_geoserver.png" % layer.name())
    save_wms_image(filename_wms, url, layer, extent)
    s = '<p><b>%s</b></p><ul><li><p>QGIS</p><p><img src="%s"></p></li>'
        '</li><p>GeoServer</p><p><img src="%s"></p></li></ul>' % (layer.name(), filename, filename_wms)
    return s

def save_wms_image(filename, url, layer, extent):
    bbox = "%f,%f,%f,%f" % (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
    h = int(extent.height() / extent.width() * WIDTH)
    url = ("%s/wms?request=GetMap&service=WMS&version=1.1.1&srs=EPSG:4326&layers=visualtests:%s&"
        "styles=visualtests:%s&format=image/png&width=%i&height=%i&bbox=%s" 
        % (url, layer.name(), layer.name(), WIDTH, h, bbox))        
    nam = QNetworkAccessManager()
    reply = nam.get(QNetworkRequest(QUrl(url)))
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    loop.exec()
    img = QImage()
    img.loadFromData(reply.readAll())
    img.save(filename)        
    
def save_layer_image(filename, layer, extent):
    h = int(extent.height() / extent.width() * WIDTH)
    img = QImage(QSize(WIDTH, h), QImage.Format_A2BGR30_Premultiplied)
    color = QColor(255,255,255,255)
    img.fill(color.rgba())
    p = QPainter()
    p.begin(img)
    p.setRenderHint(QPainter.Antialiasing)
    ms = QgsMapSettings()
    ms.setBackgroundColor(color)        
    ms.setLayers([layer])
    ms.setExtent(extent)
    ms.setOutputSize(img.size())
    render = QgsMapRendererCustomPainterJob(ms, p)
    render.start()
    render.waitForFinished()
    p.end()
    img.save(filename)    