import configparser
from pathlib import Path

#: GeoCat Bridge plugin namespace
PLUGIN_NAMESPACE = "geocatbridge"

_prop_cache = {}
_meta_parser = configparser.ConfigParser()


def _load():
    _meta_parser.read(str(Path(__file__).parent.parent / 'metadata.txt'))


def getProperty(name, section='general'):
    """ Reads the property with the given name from the **local** plugin metadata. """
    try:
        value = _prop_cache.get(name, _meta_parser.get(section, name))
    except (configparser.NoOptionError, configparser.NoSectionError):
        value = None
    _prop_cache[name] = value
    return value


def getAppName() -> str:
    """ Returns the full name of the QGIS Bridge plugin. """
    return getProperty("name")


def getTrackerUrl() -> str:
    """ Returns the issue tracker URL for GeoCat Bridge. """
    return getProperty("tracker")


def getVersion() -> str:
    """ Returns the GeoCat Bridge version string. """
    return getProperty("version").strip()


def getDocsUrl() -> str:
    """ Returns the GeoCat Bridge documentation URL. """
    return getProperty("docs", "bridge").rstrip('/')


_load()
