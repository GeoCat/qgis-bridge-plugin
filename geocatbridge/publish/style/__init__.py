# Maps required bridgestyle functionality to a more convenient geocatbridge.publish.style namespace.
# This also makes sure that we are importing the bridgestyle lib matching this version of GeoCat Bridge.

from geocatbridge.libs.bridgestyle.bridgestyle.qgis import *  # noqa
from geocatbridge.libs.bridgestyle.bridgestyle.mapboxgl.fromgeostyler import convertGroup as convertMapboxGroup  # noqa

convertDictToMapfile = mapserver.fromgeostyler.convertDictToMapfile
convertStyle = togeostyler.convert
