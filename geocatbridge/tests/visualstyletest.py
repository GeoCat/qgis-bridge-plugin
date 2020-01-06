import os
import unittest
import json

import bridgestyle

from geocatbridge.publish.geoserver import GeoserverServer
from qgis.core import QgsRasterLayer, QgsVectorLayer

class QgisToStylerTest(unittest.TestCase):
   pass
    
_layers = {}
def load_layer(file):    
    if file not in _layers:
        name = os.path.basename(file)
        layer = QgsRasterLayer(file, "testlayer", "gdal")
        if not layer.isValid():
            layer = QgsVectorLayer(file, "testlayer", "ogr")
        _layers[file] = layer
    return _layers[file]

def create_styles_visual_test_page(url = "http://localhost:808/geoserver", username="admin", password="geoserver"):
    server = GeoServer
    main_folder = bridgestyle(bridgestyle.__file__, "test", "data", "qgis")
    for subfolder in os.listdir(main_folder):
        datafile = os.path.join(main_folder, subfolder, "testlayer.gpkg")
        layer = load_layer(datafile)
        if not os.path.exists(datafile):
            datafile = os.path.join(main_folder, subfolder, "testlayer.tiff")        
        subfolder_path = os.path.join(main_folder, subfolder)
        for style in os.listdir(subfolder_path):
            if style.lower().endswith("qml"):
                stylefile = os.path.join(subfolder_path, style)
                name = os.path.splitext(stylefile)[0]                
                layer.loadNamedStyle(stylefile)             
                           
    
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QgisToStylerTest)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    run_tests()
    