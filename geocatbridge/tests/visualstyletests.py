"""
The create_styles_visual_test_page function in this file creates a webpage
with a set of test styles, as represented by QGIS and GeoServer, so visual
inspection is easy and can be used to check that conversion from QGIS style 
into SLD and later parsing by GeoServer is done correctly. 

Test styles are taken from the underlying bridge-style library, and follow
these rules:

- Styles are grouped in folders, each of them defining a group
- All styles in the same group use the same data source. 

To add new tests, just add data and style files to the bridge-style library,
following the above rules

In the webpage created by this script, there will be a tab for each of the 
groups. Within that tab, all test styles are displayed, with a pair of images
for each of them.

A link to the SLD file is also available for each test style, so the SLD code
can be inspected as well.

To run this script, use the following code from the QGIS Python console:

>>> from geocatbridge.tests.visualstyletest import create_styles_visual_test_page
>>> create_styles_visual_test_page("path/to/outut/folder")

The script assumes a standard GeoServer instance reachable at 

http://localhost:8080/geoserver

with default admin credentials (admin/geoserver). If you want to test against
a different configuration, pass the url and the corresponing credentials when
calling the main function:

>>> create_styles_visual_test_page("path/to/outut/folder", 
        url="my/url/to/geoserver", username="user", password="pass")


"""

import os

import bridgestyle
from bridgestyle.qgis import layerStyleAsSld

from geocatbridge.publish.geoserver import GeoserverServer

from qgis.PyQt.QtGui import QImage, QColor, QPainter
from qgis.PyQt.QtCore import QSize, QCoreApplication, QUrl, QEventLoop

from qgis.core import (
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    QgsRasterLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest


class TestGeoserverServer(GeoserverServer):
    @property
    def _workspace(self):
        return "visualtests"


_layers = {}


def load_layer(file):
    if file not in _layers:
        name = os.path.basename(file)
        layer = QgsRasterLayer(file, name, "gdal")
        if not layer.isValid():
            layer = QgsVectorLayer(file, "testlayer", "ogr")
        _layers[file] = layer
    return _layers[file]


def create_styles_visual_test_page(
    folder,
    url="http://localhost:8080/geoserver",
    username="admin",
    password="geoserver",
):
    server = TestGeoserverServer("testserver", url)
    server.setBasicAuthCredentials(username, password)
    server.prepareForPublishing(False)
    main_folder = os.path.join(
        os.path.dirname(bridgestyle.__file__), "test", "data", "qgis"
    )
    tabshtml = '<div class="tab">'

    contenthtml = ""
    for subfolder in os.listdir(main_folder):
        tabshtml += (
            '<button class="tablinks" onclick="openTab(event, \'%s\')">%s</button>'
            % (subfolder, subfolder)
        )
        contenthtml += '<div id="%s" class="tabcontent">' % subfolder
        datafile = os.path.join(main_folder, subfolder, "testlayer.gpkg")
        if not os.path.exists(datafile):
            datafile = os.path.join(main_folder, subfolder, "testlayer.tiff")
        layer = load_layer(datafile)
        subfolder_path = os.path.join(main_folder, subfolder)
        for style in os.listdir(subfolder_path):
            if style.lower().endswith("qml"):
                stylefile = os.path.join(subfolder_path, style)
                name = os.path.splitext(os.path.basename(stylefile))[0]
                layer.setName(name)
                layer.loadNamedStyle(stylefile)
                server.publishLayer(layer)
                contenthtml += create_images(folder, url, layer, subfolder)
        contenthtml += "</div>"

    tabshtml += "</div>"
    s = template.replace("[tabs]", tabshtml)
    s = s.replace("[content]", contenthtml)
    s = s.replace("[default]", os.listdir(main_folder)[0])
    indexfilename = os.path.join(folder, "index.html")
    with open(indexfilename, "w") as f:
        f.write(s)
    # server.deleteWorkspace()


WIDTH = 500.0


def create_images(folder, url, layer, group):
    extent = layer.extent()
    filename = os.path.join(folder, "%s_%s_qgis.png" % (group, layer.name()))
    save_layer_image(filename, layer, extent)
    filename_wms = os.path.join(folder, "%s_%s_geoserver.png" % (group, layer.name()))
    save_wms_image(filename_wms, url, layer, extent)
    filename_sld = os.path.join(folder, "%s_%s.sld" % (group, layer.name()))
    sld, _, _ = layerStyleAsSld(layer)
    with open(filename_sld, "w") as f:
        f.write(sld)
    s = (
        '<p><b>%s</b></p><ul><li><p>QGIS</p><p><img src="%s"></p></li>'
        '<li><p>GeoServer <a href="%s">[SLD]</a></p>'
        '<p><img src="%s"></p></li></ul>'
        % (layer.name(), filename, filename_sld, filename_wms)
    )
    return s


def save_wms_image(filename, url, layer, extent):
    bbox = "%f,%f,%f,%f" % (
        extent.xMinimum(),
        extent.yMinimum(),
        extent.xMaximum(),
        extent.yMaximum(),
    )
    h = int(extent.height() / extent.width() * WIDTH)
    url = (
        "%s/wms?request=GetMap&service=WMS&version=1.1.1&srs=EPSG:4326&layers=visualtests:%s&"
        "styles=visualtests:%s&format=image/png&width=%i&height=%i&bbox=%s"
        % (url, layer.name(), layer.name(), WIDTH, h, bbox)
    )
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
    color = QColor(255, 255, 255, 255)
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


template = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* {box-sizing: border-box}
body {font-family: "Lato", sans-serif;}

/* Style the tab */
.tab {
  float: left;
  border: 1px solid #ccc;
  background-color: #f1f1f1;
  width: 30%;
  height: 100%;
}

/* Style the buttons inside the tab */
.tab button {
  display: block;
  background-color: inherit;
  color: black;
  padding: 22px 16px;
  width: 100%;
  border: none;
  outline: none;
  text-align: left;
  cursor: pointer;
  transition: 0.3s;
  font-size: 17px;
}

/* Change background color of buttons on hover */
.tab button:hover {
  background-color: #ddd;
}

/* Create an active/current "tab button" class */
.tab button.active {
  background-color: #ccc;
}

/* Style the tab content */
.tabcontent {
  float: left;
  padding: 0px 12px;
  border: 1px solid #ccc;
  width: 70%;
  border-left: none;
  height: 100%;
}
</style>
</head>
<body>

[tabs]
[content]

<script>
function openTab(evt, tabName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " active";
}

document.getElementById("[default]").click();
</script>
   
</body>"""
