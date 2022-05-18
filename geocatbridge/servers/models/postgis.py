from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from qgis.core import QgsVectorLayerExporter

from geocatbridge.utils.layers import BridgeLayer
from geocatbridge.servers.bases import DbServerBase
from geocatbridge.servers.views.postgis import PostgisWidget


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

    def qgisUri(self, layer: BridgeLayer) -> str:
        """ Returns a database table connection URI that can be used by QGIS. """
        username, password = self.getCredentials()
        uri = f"""dbname='{self.database}' host='{self.host}' port={self.port} user='{username}' password='{password}' key='id' table="{self.schema}"."{layer.web_slug}" (geom)"""  # noqa
        return uri

    @contextmanager
    def cursor(self, autocommit: bool = False):
        """ Gets a direct access PostGIS query cursor for the configured connection details. """
        con, cur = None, None
        username, password = self.getCredentials()
        try:
            con = psycopg2.connect(dbname=self.database, user=username, password=password,
                                   host=self.host, port=self.port)
            if autocommit:
                con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = con.cursor()
            yield cur
        finally:
            if hasattr(cur, "close"):
                cur.close()
            if hasattr(con, "close"):
                con.close()

    def layerTableName(self, layer: BridgeLayer, qualified: bool = False):
        """ Tries to determine the (qualified) underlying (target) table name for the given layer.
        Note that the table may not exist (yet) and no checks are performed.
        """
        table = f'{layer.dataset_name if layer.is_postgis_based else layer.web_slug}'
        if qualified:
            return f'"{self.schema}"."{table}"'
        return table

    def geometryField(self, layer: BridgeLayer) -> str:
        """ Returns the first geometry field name for the given underlying layer table, if any exists. """
        table_name = self.layerTableName(layer)
        try:
            with self.cursor(True) as cur:
                # noinspection SqlNoDataSourceInspection
                cur.execute(f"""SELECT column_name FROM information_schema.columns 
                                WHERE table_name = '{table_name}' AND table_schema = '{self.schema}' 
                                AND table_catalog='{self.database}' and udt_name = 'geometry'""")
                result = cur.fetchone()[0]
        except Exception as err:
            self.logWarning(f"Failed to retrieve geometry field name for table {table_name}: {err}")
            result = None
        return result

    def dropLayerTable(self, layer: BridgeLayer):
        """ Tries to drop an existing underlying table for a given QGIS layer.
        If the table does not exist, no error is thrown. """
        table_name = self.layerTableName(layer, True)
        with self.cursor(True) as cur:
            # noinspection SqlNoDataSourceInspection
            cur.execute(f"""DROP TABLE IF EXISTS {table_name}""")

    def importLayer(self, layer: BridgeLayer):
        """ Imports a QGIS layer into PostGIS. Only supports vector layers for now. """

        def checkErrors(export_result):
            """ Checks if the exporter returned an error. If it did, an exception is raised. """
            error_msg = 'unknown error'
            error_code = -1
            if isinstance(export_result, tuple):
                error_code, error_msg = export_result[:2]
            elif isinstance(export_result, int):
                error_code = export_result
            if not error_code:
                # Error code is 0: no issues found
                return
            error_msg = error_msg.strip()
            if not error_msg:
                # There is an error code, but no error message: create message ourselves
                messages = [
                    'no error',
                    'failed to create data source',                 # ErrCreateDataSource
                    'failed to create table',                       # ErrCreateLayer
                    'unsupported attribute type encountered',       # ErrAttributeTypeUnsupported
                    'failed to create attribute(s)',                # ErrAttributeCreationFailed
                    'projection error',                             # ErrProjection
                    'failed to write feature',                      # ErrFeatureWriteFailed
                    'invalid layer',                                # ErrInvalidLayer
                    'invalid provider',                             # ErrInvalidProvider
                    'unsupported feature for current provider',     # ErrProviderUnsupportedFeature
                    'connection failure',                           # ErrConnectionFailed
                    'operation canceled by user'                    # ErrUserCanceled
                ]
                if isinstance(error_code, int) and error_code < len(messages):
                    # Lookup error message for current code if code is in range
                    error_msg = messages[error_code]

            # Raise the exception if we ended up here
            raise Exception(f'Error importing into PostGIS: {error_msg}')

        # Get PostGIS connection string for the current layer
        uri = self.qgisUri(layer)

        # Delete table if it exists
        self.dropLayerTable(layer)

        # Export to PostGIS (include all fields)
        result = QgsVectorLayerExporter.exportLayer(layer, uri, "postgres", layer.sourceCrs())
        checkErrors(result)

    def testConnection(self, errors: set):
        try:
            with self.cursor() as cur:
                cur.execute('SELECT version()')
                cur.fetchone()[0]  # noqa
                return True
        except psycopg2.Error as e:
            errors.add(f'Could not connect to {self.serverName}: {e}')
        except IndexError:
            errors.add(f'Failed to retrieve version info for {self.serverName}')
        except Exception as e:
            errors.add(f'Unknown error while connecting to {self.serverName}: {e}')
        return False
