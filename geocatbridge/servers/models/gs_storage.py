from geocatbridge.utils.enum_ import LabeledIntEnum


class GeoserverStorage(LabeledIntEnum):
    FILE_BASED = 'File-based storage (e.g. GeoPackage)'
    POSTGIS_BRIDGE = 'Import into PostGIS database (direct connect)'
    POSTGIS_GEOSERVER = 'Import into PostGIS database (managed by GeoServer)'
