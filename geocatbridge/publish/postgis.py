import psycopg2
from qgis.core import QgsVectorLayerExporter, QgsFeatureSink, QgsFields
from qgis.PyQt.QtCore import QCoreApplication
from .serverbase import ServerBase


class PostgisServer(ServerBase):
    def __init__(
        self,
        name,
        authid="",
        host="localhost",
        port="5432",
        schema="public",
        database="db",
    ):
        super().__init__()
        self.name = name
        self.host = host
        self.port = port
        self.schema = schema
        self.database = database
        self.authid = authid
        self._isMetadataCatalog = False
        self._isDataCatalog = False

    def importLayer(self, layer, fields):
        username, password = self.getCredentials()
        uri = (
            "dbname='%s' key='id' host=%s port=%s user='%s' password='%s' table=\"%s\".\"%s\" (geom) sql="
            % (
                self.database,
                self.host,
                self.port,
                username,
                password,
                self.schema,
                layer.name(),
            )
        )

        qgsfields = QgsFields()
        for f in layer.fields():
            if fields is None or f.name() in fields:
                qgsfields.append(f)
        exporter = QgsVectorLayerExporter(
            uri, "postgres", qgsfields, layer.wkbType(), layer.sourceCrs(), True
        )

        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception(
                QCoreApplication.translate(
                    "GeocatBridge", "Error importing to PostGIS: {0}"
                ).format(exporter.errorMessage())
            )

        features = layer.getFeatures()
        for f in features:
            if not exporter.addFeature(f, QgsFeatureSink.FastInsert):
                raise Exception(
                    QCoreApplication.translate(
                        "GeocatBridge", "Error importing to PostGIS: {0}"
                    ).format(exporter.errorMessage())
                )
        exporter.flushBuffer()
        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception(
                QCoreApplication.translate(
                    "GeocatBridge", "Error importing to PostGIS: {0}"
                ).format(exporter.errorMessage())
            )

    def testConnection(self):
        username, password = self.getCredentials()
        con = None
        try:
            con = psycopg2.connect(
                dbname=self.database,
                user=username,
                password=password,
                host=self.host,
                port=self.port,
            )
            cur = con.cursor()
            cur.execute("SELECT version()")
            cur.fetchone()[0]
            return True
        except:
            return False
        finally:
            if con:
                con.close()
