import configparser
from pathlib import Path

#: GeoCat Bridge plugin namespace
PLUGIN_NAMESPACE = "geocatbridge"

_prop_cache = {}
_meta_parser = configparser.ConfigParser()


def _load():
    _meta_parser.read(str(Path(__file__).parent.parent / 'metadata.txt'))


def getProperty(name):
    """ Reads the property with the given name from the **local** plugin metadata. """
    try:
        value = _prop_cache.get(name, _meta_parser.get("general", name))
    except configparser.NoOptionError:
        value = None
    _prop_cache[name] = value
    return value


def getAppName():
    """ Returns the full name of the QGIS Bridge plugin. """
    return getProperty("name")


def getTrackerUrl():
    """ Returns the issue tracker URL for GeoCat Bridge. """
    return getProperty("tracker")


_load()
