import os
import re

from qgis.PyQt.QtCore import QVariant, QSettings

try:
    from qgis.core import QGis
except ImportError:
    from qgis.core import Qgis as QGis, QgsWkbTypes

from qgis.core import (
                       QgsField,
                       QgsFields,
                       QgsCoordinateReferenceSystem,
                       QgsVectorLayer,
                       QgsRasterLayer,
                       QgsVectorFileWriter
                      )


try:
    from qgis.core import QgsMapLayerRegistry
    _layerreg = QgsMapLayerRegistry.instance()
except ImportError:
    from qgis.core import QgsProject
    _layerreg = QgsProject.instance()

def mapLayers(name=None, types=None):
    """
    Return all the loaded layers.  Filters by name (optional) first and then type (optional)
    :param name: (optional) name of layer to return..
    :param type: (optional) The QgsMapLayer type of layer to return. Accepts a single value or a list of them
    :return: List of loaded layers. If name given will return all layers with matching name.
    """
    if types is not None and not isinstance(types, list):
        types = [types]
    layers = _layerreg.mapLayers().values()
    _layers = []
    if name or types:
        if name:
            _layers = [layer for layer in layers if re.match(name, layer.name())]
        if types:
            _layers += [layer for layer in layers if layer.type() in types]
        return _layers
    else:
        return layers

def vectorLayers():
    return mapLayers(types = QgsVectorLayer.VectorLayer)

def addLayer(layer, loadInLegend=True):
    """
    Add one or several layers to the QGIS session and layer registry.
    :param layer: The layer object or list with layers  to add the QGIS layer registry and session.
    :param loadInLegend: True if this layer should be added to the legend.
    :return: The added layer
    """
    if not hasattr(layer, "__iter__"):
        layer = [layer]
    _layerreg.addMapLayers(layer, loadInLegend)
    return layer

def addLayerNoCrsDialog(layer, loadInLegend=True):
    '''
    Tries to add a layer from layer object
    Same as the addLayer method, but it does not ask for CRS, regardless of current
    configuration in QGIS settings
    '''
    settings = QSettings()
    prjSetting = settings.value('/Projections/defaultBehaviour')
    settings.setValue('/Projections/defaultBehaviour', '')
    # QGIS3
    prjSetting3 = settings.value('/Projections/defaultBehavior')
    settings.setValue('/Projections/defaultBehavior', '')
    layer = addLayer(layer, loadInLegend)
    settings.setValue('/Projections/defaultBehaviour', prjSetting)
    settings.setValue('/Projections/defaultBehavior', prjSetting3)
    return layer

TYPE_MAP = {
    str: QVariant.String,
    float: QVariant.Double,
    int: QVariant.Int,
    bool: QVariant.Bool
}

try:
    GEOM_TYPE_MAP = {
        QGis.WKBPoint: 'Point',
        QGis.WKBLineString: 'LineString',
        QGis.WKBPolygon: 'Polygon',
        QGis.WKBMultiPoint: 'MultiPoint',
        QGis.WKBMultiLineString: 'MultiLineString',
        QGis.WKBMultiPolygon: 'MultiPolygon',
    }
except:
    GEOM_TYPE_MAP = {
        QgsWkbTypes.Point: 'Point',
        QgsWkbTypes.LineString: 'LineString',
        QgsWkbTypes.Polygon: 'Polygon',
        QgsWkbTypes.MultiPoint: 'MultiPoint',
        QgsWkbTypes.MultiLineString: 'MultiLineString',
        QgsWkbTypes.MultiPolygon: 'MultiPolygon',
    }
    QGis.WKBPoint = QgsWkbTypes.Point
    QGis.WKBMultiPoint = QgsWkbTypes.MultiPoint
    QGis.WKBLine = QgsWkbTypes.LineString
    QGis.WKBMultiLine = QgsWkbTypes.MultiLineString
    QGis.WKBPolygon = QgsWkbTypes.Polygon
    QGis.WKBMultiPolygon = QgsWkbTypes.MultiPolygon

def _toQgsField(f):
    if isinstance(f, QgsField):
        return f
    return QgsField(f[0], TYPE_MAP.get(f[1], QVariant.String))

def _fieldName(f):
    if isinstance(f, basestring):
        return f
    return f.name()

def newPointsLayer(filename, fields, crs, encoding="utf-8"):
    return newVectorLayer(filename, fields, QGis.WKBPoint, crs, encoding)

def newLinesLayer(filename, fields, crs, encoding="utf-8"):
    return newVectorLayer(filename, fields, QGis.WKBLine, crs, encoding)

def newPolygonsLayer(filename, fields, crs, encoding="utf-8"):
    return newVectorLayer(filename, fields, QGis.WKBPolygon, crs, encoding)

def newVectorLayer(filename, fields, geometryType, crs, encoding="utf-8"):
    '''
    Creates a new vector layer

    :param filename: The filename to store the file. The extensions determines the type of file.
    If extension is not among the supported ones, a shapefile will be created and the file will
    get an added '.shp' to its path.
    If the filename is None, a memory layer will be created

    :param fields: the fields to add to the layer. Accepts a QgsFields object or a list of tuples (field_name, field_type)
    Accepted field types are basic Python types str, float, int and bool

    :param geometryType: The type of geometry of the layer to create.

    :param crs: The crs of the layer to create. Accepts a QgsCoordinateSystem object or a string with the CRS authId.

    :param encoding: The layer encoding
    '''
    if isinstance(crs, basestring):
        crs = QgsCoordinateReferenceSystem(crs)
    if filename is None:
        uri = GEOM_TYPE_MAP[geometryType]
        if crs.isValid():
            uri += '?crs=' + crs.authid() + '&'
        fieldsdesc = ['field=' + f for f in fields]

        fieldsstring = '&'.join(fieldsdesc)
        uri += fieldsstring
        layer = QgsVectorLayer(uri, "mem_layer", 'memory')
    else:
        formats = QgsVectorFileWriter.supportedFiltersAndFormats()
        OGRCodes = {}
        for (key, value) in formats.items():
            extension = unicode(key)
            extension = extension[extension.find('*.') + 2:]
            extension = extension[:extension.find(' ')]
            OGRCodes[extension] = value

        extension = os.path.splitext(filename)[1][1:]
        if extension not in OGRCodes:
            extension = 'shp'
            filename = filename + '.shp'

        if isinstance(fields, QgsFields):
            qgsfields = fields
        else:
            qgsfields = QgsFields()
            for field in fields:
                qgsfields.append(_toQgsField(field))

        QgsVectorFileWriter(filename, encoding, qgsfields,
                            geometryType, crs, OGRCodes[extension])

        layer = QgsVectorLayer(filename, os.path.basename(filename), 'ogr')

    return layer


def createWmsLayer(url, layer, style, crs):
    pass


def createWfsLayer(url, layer, crs):
    pass

class WrongLayerNameException(BaseException) :
    pass

class WrongLayerSourceException(BaseException) :
    pass

def layerFromName(name):
    '''
    Returns the layer from the current project with the passed name
    Raises WrongLayerNameException if no layer with that name is found
    If several layers with that name exist, only the first one is returned
    '''
    layers =_layerreg.mapLayers().values()
    for layer in layers:
        if layer.name() == name:
            return layer
    raise WrongLayerNameException()

def layerFromSource(source):
    '''
    Returns the layer from the current project with the passed source
    Raises WrongLayerSourceException if no layer with that source is found
    '''
    layers =_layerreg.mapLayers().values()
    for layer in layers:
        if layer.source() == source:
            return layer
    raise WrongLayerSourceException()


def loadLayer(filename, name = None, provider=None):
    '''
    Tries to load a layer from the given file

    :param filename: the path to the file to load.

    :param name: the name to use for adding the layer to the current project.
    If not passed or None, it will use the filename basename
    '''
    name = name or os.path.splitext(os.path.basename(filename))[0]
    if provider != 'gdal': # QGIS3 crashes if opening a raster as vector ... this needs further investigations
        qgslayer = QgsVectorLayer(filename, name, provider or "ogr")
    if provider == 'gdal' or not qgslayer.isValid():
        qgslayer = QgsRasterLayer(filename, name, provider or "gdal")
        if not qgslayer.isValid():
            raise RuntimeError('Could not load layer: ' + unicode(filename))

    return qgslayer


def loadLayerNoCrsDialog(filename, name=None, provider=None):
    '''
    Tries to load a layer from the given file
    Same as the loadLayer method, but it does not ask for CRS, regardless of current
    configuration in QGIS settings
    '''
    settings = QSettings()
    prjSetting = settings.value('/Projections/defaultBehaviour')
    settings.setValue('/Projections/defaultBehaviour', '')
    # QGIS3:
    prjSetting3 = settings.value('/Projections/defaultBehavior')
    settings.setValue('/Projections/defaultBehavior', '')
    layer = loadLayer(filename, name, provider)
    settings.setValue('/Projections/defaultBehaviour', prjSetting)
    settings.setValue('/Projections/defaultBehavior', prjSetting3)
    return layer

