import unittest
import os
import sys

from geocatbridgecommons.geoserver import GeoServerCatalog
from geocatbridgecommons.geoserver import RequestsNetworkAccessManager

def _testFile(f):
    return os.path.join(os.path.dirname(__file__), 'data', f)

class TestWorkflow(unittest.TestCase):

    GSURL = "http://localhost:8080/geoserver/rest"
    GSWORKSPACE = "test_workspace"
    GSUSER = "admin"
    GSPASSWD = "geoserver"

    GNURL = "http://localhost:8080/geoserver/rest"        

    DBHOST = "localhost"
    DBPORT = 5432
    DBSCHEMA = "test"
    DBPASSWD = "test"
    DBUSERNAME = "test"
    LAYERNAME = "points"

    def __init__(self):
        nam = RequestsNetworkAccessManager(self.GSUSER, self.GSPASSWD)
        self.catalog = geoserver.GeoServerCatalog(self.GSURL, nam, self.WORKSPACE)
        gnnam = RequestsNetworkAccessManagerForGeoNetwork(self.GNUSER, self. GNPASSWD)

    @classmethod
    def setUpClass(cls):
        pass

    def testPublishMetadata(self):
        sld = _testFile("points.sld")
        if self.catalog.style_exists(self.LAYERNAME):
            self.catalog.style_exists(self.LAYERNAME)
        self.assertFalse(self.catalog.style_exists(self.LAYERNAME))
        self.catalog.publish_style(self.LAYERNAME, sld = sld)
        self.assertTrue(self.catalog.style_exists(self.LAYERNAME))

    def testPublishVectorFromPostGIS(self):
        sld = _testFile(self.LAYERNAME + ".sld")
        if self.catalog.style_exists(self.LAYERNAME):
            self.catalog.style_exists(self.LAYERNAME)
        self.assertFalse(self.catalog.style_exists(self.LAYERNAME))
        self.catalog.publish_layer_from_postgis(self.DBHOST, self.DBPORT, self.DBNAME, self.DBSCHEMA, self.LAYERNAME, 
                                        self.DBUSER, self.DBPASSWD, "EPSG:4326", self.LAYERNAME, sld, self.LAYERNAME)
        self.assertTrue(self.catalog.style_exists(self.LAYERNAME))
        self.assertTrue(self.catalog.layer_exists(self.LAYERNAME))

    def testPublishVectorFromFile(self):
        gpkg = _testFile(self.LAYERNAME + ".gpkg")
        sld = _testFile(self.LAYERNAME + ".sld")
        if self.catalog.style_exists(self.LAYERNAME):
            self.catalog.style_exists(self.LAYERNAME)
        self.assertFalse(self.catalog.style_exists(self.LAYERNAME))
        self.catalog.publish_layer_from_file(gpkg, self.LAYERNAME, sld, self.LAYERNAME)
        self.assertTrue(self.catalog.style_exists(self.LAYERNAME))
        self.assertTrue(self.catalog.layer_exists(self.LAYERNAME))        
        
    def testPublishStyleAsSld(self):
        sld = _testFile("points.sld")
        if self.catalog.style_exists(self.LAYERNAME):
            self.catalog.style_exists(self.LAYERNAME)
        self.assertFalse(self.catalog.style_exists(self.LAYERNAME))
        self.catalog.publish_style(self.LAYERNAME, sld = sld)
        self.assertTrue(self.catalog.style_exists(self.LAYERNAME))

    def testPublishStyleAsZip(self):
        zipfile = _testFile("points.zip")
        if self.catalog.style_exists(self.LAYERNAME):
            self.catalog.style_exists(self.LAYERNAME)
        self.assertFalse(self.catalog.style_exists(self.LAYERNAME))
        self.catalog.publish_style(self.LAYERNAME, zipfile = zipfile)
        self.assertTrue(self.catalog.style_exists(self.LAYERNAME))
        
def suite():
    suite = unittest.makeSuite(TestLayers, 'test')
    suite.addTests(unittest.makeSuite(TestLayersB, 'test'))
    return suite

def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())

if __name__ == '__main__':
    unittest.main()
