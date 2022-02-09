import psycopg2
from qgis.core import QgsVectorLayerExporter, QgsFeatureSink, QgsFields

from geocatbridge.servers.bases import DbServerBase
from geocatbridge.servers.views.postgis import PostgisWidget
from geocatbridge.utils.meta import getAppName


class PostgisServer(DbServerBase):
    host: str = "localhost"
    port: int = PostgisWidget.DEFAULT_PORT
    schema: str = "public"
    database: str = "db"

    def __init__(self, name, authid="", **options):  # noqa
        super().__init__(name, authid, **options)

    @classmethod
    def getWidgetClass(cls) -> type:
        return PostgisWidget

    @classmethod
    def getLabel(cls) -> str:
        return 'PostGIS'

    def importLayer(self, layer, fields):
        username, password = self.getCredentials()
        uri = "dbname='%s' key='id' host=%s port=%s user='%s' password='%s' table=\"%s\".\"%s\" (geom) sql=" % (
            self.database, self.host, self.port, username, password, self.schema, layer.name())

        qgsfields = QgsFields()
        for f in layer.fields():
            if fields is None or f.name() in fields:
                qgsfields.append(f)
        exporter = QgsVectorLayerExporter(uri, "postgres", qgsfields,
                                          layer.wkbType(), layer.sourceCrs(), True, {})

        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception(self.translate(getAppName(), f'Error importing to PostGIS: {exporter.errorMessage()}'))

        features = layer.getFeatures()
        for f in features:
            if not exporter.addFeature(f, QgsFeatureSink.FastInsert):
                raise Exception(self.translate(getAppName(), f'Error importing to PostGIS: {exporter.errorMessage()}'))
        exporter.flushBuffer()
        if exporter.errorCode() != QgsVectorLayerExporter.NoError:
            raise Exception(self.translate(getAppName(), f'Error importing to PostGIS: {exporter.errorMessage()}'))

    def testConnection(self, errors: set):
        username, password = self.getCredentials()
        con = None
        try:
            con = psycopg2.connect(dbname=self.database, user=username, password=password, host=self.host,
                                   port=self.port)
            cur = con.cursor()
            cur.execute('SELECT version()')
            cur.fetchone()[0]  # noqa
            return True
        except psycopg2.Error as e:
            errors.add(f'Could not connect to {self.serverName}: {e}')
        except IndexError:
            errors.add(f'Failed to retrieve version info for {self.serverName}')
        except Exception as e:
            errors.add(f'Unknown error while connecting to {self.serverName}: {e}')
        finally:
            if con:
                con.close()
        return False
